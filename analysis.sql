--Query 1: Overall cart metrics

SELECT
    COUNT(*) AS total_carts,
    COUNT(DISTINCT user_id) AS unique_users,
    SUM(total_quantity) AS total_items,
    ROUND(AVG(reported_total), 2) AS average_cart_value,
    ROUND(SUM(reported_total), 2) AS total_sample_cart_value
FROM carts;

--Query 2: Top 10 products by quantity

SELECT
    p.product_id,
    p.title,
    p.category,
    SUM(ci.quantity) AS units_in_carts
FROM cart_items ci
JOIN products p
    ON ci.product_id = p.product_id
GROUP BY p.product_id, p.title, p.category
ORDER BY units_in_carts DESC
LIMIT 10;

--Query 3: Top three products in each category

WITH product_demand AS (
    SELECT
        p.product_id,
        p.title,
        p.category,
        SUM(ci.quantity) AS units_in_carts
    FROM products p
    JOIN cart_items ci
        ON p.product_id = ci.product_id
    GROUP BY p.product_id, p.title, p.category
),
ranked_products AS (
    SELECT *,
        DENSE_RANK() OVER (
            PARTITION BY category
            ORDER BY units_in_carts DESC
        ) AS product_rank
    FROM product_demand
)
SELECT *
FROM ranked_products
WHERE product_rank <= 3
ORDER BY category, product_rank;

--Query 4: Classify carts by value

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

--Query 5: Product share of category value

WITH product_value AS (
    SELECT
        p.product_id,
        p.title,
        p.category,
        SUM(ci.line_total) AS item_value
    FROM products p
    JOIN cart_items ci
        ON p.product_id = ci.product_id
    GROUP BY p.product_id, p.title, p.category
)
SELECT
    product_id,
    title,
    category,
    item_value,
    ROUND(
        100.0 * item_value /
        NULLIF(SUM(item_value) OVER (
            PARTITION BY category
        ), 0),
        2
    ) AS category_value_percentage
FROM product_value
ORDER BY category, category_value_percentage DESC;

-- Query 6: Rank products by units in carts

WITH product_sales AS (
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
)
SELECT
    product_id,
    title,
    category,
    units_in_carts,
    ROW_NUMBER() OVER (
        ORDER BY units_in_carts DESC
    ) AS overall_rank
FROM product_sales
ORDER BY overall_rank;

-- Query 7: Running total of cart value

WITH cart_values AS (
    SELECT
        cart_id,
        reported_total
    FROM carts
)
SELECT
    cart_id,
    reported_total,
    ROUND(
        SUM(reported_total) OVER (
            ORDER BY cart_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS running_cart_value
FROM cart_values
ORDER BY cart_id;
-- Query 8: Category performance

SELECT
    p.category,
    COUNT(DISTINCT ci.cart_id) AS carts_with_category,
    SUM(ci.quantity) AS total_units,
    ROUND(SUM(ci.line_total), 2) AS category_value,
    ROUND(AVG(ci.line_total), 2) AS average_item_value
FROM products p
JOIN cart_items ci
    ON p.product_id = ci.product_id
GROUP BY p.category
ORDER BY category_value DESC;


-- DATA QUALITY CHECKS

-- Query 9: Record count validation

SELECT
    'Products' AS table_name,
    COUNT(*) AS record_count
FROM products

UNION ALL

SELECT
    'Carts',
    COUNT(*)
FROM carts

UNION ALL

SELECT
    'Cart Items',
    COUNT(*)
FROM cart_items;


-- Query 10: Duplicate product IDs

SELECT
    product_id,
    COUNT(*) AS duplicate_count
FROM products
GROUP BY product_id
HAVING COUNT(*) > 1;


-- Query 11: Duplicate cart IDs

SELECT
    cart_id,
    COUNT(*) AS duplicate_count
FROM carts
GROUP BY cart_id
HAVING COUNT(*) > 1;


-- Query 12: Missing values

SELECT
    COUNT(*) AS total_products,
    SUM(CASE
        WHEN title IS NULL OR TRIM(title) = ''
        THEN 1 ELSE 0
    END) AS missing_title,
    SUM(CASE
        WHEN category IS NULL OR TRIM(category) = ''
        THEN 1 ELSE 0
    END) AS missing_category,
    SUM(CASE
        WHEN price IS NULL
        THEN 1 ELSE 0
    END) AS missing_price
FROM products;


-- Query 13: Invalid product prices

SELECT
    product_id,
    title,
    price
FROM products
WHERE price IS NULL
   OR price <= 0;


-- Query 14: Invalid cart quantities

SELECT
    cart_id,
    product_id,
    quantity
FROM cart_items
WHERE quantity IS NULL
   OR quantity <= 0;


-- Query 15: Orphan product references

SELECT
    ci.product_id,
    COUNT(*) AS item_count
FROM cart_items ci
LEFT JOIN products p
    ON ci.product_id = p.product_id
WHERE p.product_id IS NULL
GROUP BY ci.product_id;


-- Query 16: Cart total reconciliation

SELECT
    c.cart_id,
    c.reported_total,
    ROUND(SUM(ci.line_total), 2) AS calculated_total,
    ROUND(
        c.reported_total - SUM(ci.line_total),
        2
    ) AS difference
FROM carts c
JOIN cart_items ci
    ON c.cart_id = ci.cart_id
GROUP BY
    c.cart_id,
    c.reported_total
ORDER BY ABS(difference) DESC;

