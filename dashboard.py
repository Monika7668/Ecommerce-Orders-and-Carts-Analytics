import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px


# =========================================================
# DATABASE
# =========================================================

DB_PATH = Path("data/ecommerce.db")

st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon="🛒",
    layout="wide",
)

st.title("E-commerce Orders & Cart Analytics")
st.caption(
    "Sample data from DummyJSON. Cart value is not confirmed revenue."
)


# =========================================================
# DATABASE CHECK
# =========================================================

if not DB_PATH.exists():
    st.error("Database not found. Run: python fetch_data.py")
    st.stop()


# =========================================================
# LOAD DATA
# =========================================================

with sqlite3.connect(DB_PATH) as conn:

    carts = pd.read_sql_query(
        "SELECT * FROM carts",
        conn
    )

    products = pd.read_sql_query(
        "SELECT * FROM products",
        conn
    )

    items = pd.read_sql_query(
        """
        SELECT
            ci.*,
            p.title,
            p.category
        FROM cart_items ci
        JOIN products p
            ON ci.product_id = p.product_id
        """,
        conn
    )


if carts.empty:
    st.warning("No cart data available.")
    st.stop()


# =========================================================
# KPI SECTION
# =========================================================

st.subheader("Overall Cart Metrics")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Total Carts",
    f"{len(carts):,}"
)

c2.metric(
    "Unique Users",
    f"{carts['user_id'].nunique():,}"
)

c3.metric(
    "Items in Carts",
    f"{carts['total_quantity'].sum():,}"
)

c4.metric(
    "Average Cart Value",
    f"{carts['reported_total'].mean():,.2f}"
)


# =========================================================
# CATEGORY PERFORMANCE
# =========================================================

st.subheader("Category Performance")

category_query = """
SELECT
    p.category,
    COUNT(DISTINCT ci.cart_id) AS carts_with_category,
    SUM(ci.quantity) AS total_units,
    ROUND(SUM(ci.line_total), 2) AS category_value
FROM products p
JOIN cart_items ci
    ON p.product_id = ci.product_id
GROUP BY p.category
ORDER BY category_value DESC;
"""

with sqlite3.connect(DB_PATH) as conn:
    category_data = pd.read_sql_query(
        category_query,
        conn
    )


fig = px.bar(
    category_data,
    x="category",
    y="total_units",
    title="Units in Sample Carts by Category",
    labels={
        "category": "Category",
        "total_units": "Units"
    }
)

st.plotly_chart(
    fig,
    width="stretch"
)


# =========================================================
# TOP 10 PRODUCTS
# =========================================================

st.subheader("Top 10 Products")

top_products_query = """
SELECT
    p.product_id,
    p.title,
    p.category,
    SUM(ci.quantity) AS units_in_carts
FROM cart_items ci
JOIN products p
    ON ci.product_id = p.product_id
GROUP BY
    p.product_id,
    p.title,
    p.category
ORDER BY units_in_carts DESC
LIMIT 10;
"""

with sqlite3.connect(DB_PATH) as conn:
    top_products = pd.read_sql_query(
        top_products_query,
        conn
    )


fig2 = px.bar(
    top_products.sort_values(
        "units_in_carts"
    ),
    x="units_in_carts",
    y="title",
    orientation="h",
    title="Top Products by Quantity in Carts",
    labels={
        "units_in_carts": "Units",
        "title": "Product"
    }
)

st.plotly_chart(
    fig2,
    width="stretch"
)


# =========================================================
# TOP 3 PRODUCTS PER CATEGORY
# DENSE_RANK()
# =========================================================

st.subheader("Top 3 Products by Category")

top_category_products_query = """
WITH product_demand AS (
    SELECT
        p.product_id,
        p.title,
        p.category,
        SUM(ci.quantity) AS units_in_carts
    FROM products p
    JOIN cart_items ci
        ON p.product_id = ci.product_id
    GROUP BY
        p.product_id,
        p.title,
        p.category
),

ranked_products AS (
    SELECT
        *,
        DENSE_RANK() OVER (
            PARTITION BY category
            ORDER BY units_in_carts DESC
        ) AS product_rank
    FROM product_demand
)

SELECT
    product_id,
    title,
    category,
    units_in_carts,
    product_rank
FROM ranked_products
WHERE product_rank <= 3
ORDER BY
    category,
    product_rank;
"""

with sqlite3.connect(DB_PATH) as conn:
    top_category_products = pd.read_sql_query(
        top_category_products_query,
        conn
    )

st.dataframe(
    top_category_products,
    width="stretch"
)


# =========================================================
# CART VALUE SEGMENTATION
# CASE WHEN
# =========================================================

st.subheader("Cart Value Segmentation")

segment_query = """
SELECT
    cart_id,
    reported_total,
    CASE
        WHEN reported_total < 100 THEN 'Low'
        WHEN reported_total < 500 THEN 'Medium'
        ELSE 'High'
    END AS cart_segment
FROM carts
ORDER BY reported_total DESC;
"""

with sqlite3.connect(DB_PATH) as conn:
    cart_segments = pd.read_sql_query(
        segment_query,
        conn
    )


segment_summary = (
    cart_segments
    .groupby("cart_segment")
    .size()
    .reset_index(name="cart_count")
)

fig3 = px.bar(
    segment_summary,
    x="cart_segment",
    y="cart_count",
    title="Number of Carts by Value Segment",
    labels={
        "cart_segment": "Cart Segment",
        "cart_count": "Number of Carts"
    }
)

st.plotly_chart(
    fig3,
    width="stretch"
)


# =========================================================
# DATA QUALITY
# =========================================================

st.subheader("Data Quality Checks")

q1, q2, q3, q4 = st.columns(4)

# Duplicate products
duplicate_products = (
    products["product_id"]
    .duplicated()
    .sum()
)

# Missing product titles
missing_titles = (
    products["title"]
    .isna()
    .sum()
)

# Missing cart totals
missing_cart_totals = (
    carts["reported_total"]
    .isna()
    .sum()
)

# Invalid quantities
invalid_quantities = (
    items["quantity"]
    .isna()
    .sum()
    +
    (items["quantity"] <= 0).sum()
)

q1.metric(
    "Duplicate Products",
    f"{duplicate_products:,}"
)

q2.metric(
    "Missing Titles",
    f"{missing_titles:,}"
)

q3.metric(
    "Missing Cart Totals",
    f"{missing_cart_totals:,}"
)

q4.metric(
    "Invalid Quantities",
    f"{invalid_quantities:,}"
)


# =========================================================
# PRODUCT SHARE OF CATEGORY
# SUM() OVER()
# =========================================================

st.subheader("Product Share of Category Value")

product_share_query = """
WITH product_value AS (
    SELECT
        p.product_id,
        p.title,
        p.category,
        SUM(ci.line_total) AS item_value
    FROM products p
    JOIN cart_items ci
        ON p.product_id = ci.product_id
    GROUP BY
        p.product_id,
        p.title,
        p.category
)

SELECT
    product_id,
    title,
    category,
    ROUND(item_value, 2) AS item_value,

    ROUND(
        100.0 * item_value /
        NULLIF(
            SUM(item_value) OVER (
                PARTITION BY category
            ),
            0
        ),
        2
    ) AS category_value_percentage

FROM product_value

ORDER BY
    category,
    category_value_percentage DESC;
"""

with sqlite3.connect(DB_PATH) as conn:
    product_share = pd.read_sql_query(
        product_share_query,
        conn
    )

st.dataframe(
    product_share,
    width="stretch"
)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "E-commerce Orders & Cart Analytics | "
    "Python + SQLite + SQL + Streamlit"
)