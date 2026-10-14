
import json
import sqlite3
import time

import requests

BASE_URL = "https://dummyjson.com"
DB_PATH = "data/ecommerce.db"


def fetch_all(endpoint):
    """Fetch all pages returned by a DummyJSON endpoint."""
    results = []
    skip = 0
    limit = 100

    while True:
        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(
            url,
            params={"limit": limit, "skip": skip},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        batch = payload.get(endpoint, [])
        results.extend(batch)

        print(f"{endpoint}: fetched {len(batch)} records")

        if not batch or skip + len(batch) >= payload.get("total", 0):
            break

        skip += len(batch)
        time.sleep(0.2)

    return results


def main():
    products = fetch_all("products")
    carts = fetch_all("carts")

    # Create the local data directory and database.
    import os
    os.makedirs("data", exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_api_responses (
                endpoint TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (endpoint, record_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT,
                price REAL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                cart_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                reported_total REAL,
                total_quantity INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                cart_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER,
                unit_price REAL,
                line_total REAL,
                PRIMARY KEY (cart_id, product_id)
            )
        """)

        # Save raw records and load the structured tables.
        for product in products:
            conn.execute("""
                INSERT OR REPLACE INTO raw_api_responses
                VALUES ('products', ?, ?)
            """, (product["id"], json.dumps(product)))

            conn.execute("""
                INSERT OR REPLACE INTO products
                VALUES (?, ?, ?, ?)
            """, (
                product["id"],
                product.get("title") or "Unknown",
                product.get("category"),
                product.get("price"),
            ))

        for cart in carts:
            conn.execute("""
                INSERT OR REPLACE INTO raw_api_responses
                VALUES ('carts', ?, ?)
            """, (cart["id"], json.dumps(cart)))

            conn.execute("""
                INSERT OR REPLACE INTO carts
                VALUES (?, ?, ?, ?)
            """, (
                cart["id"],
                cart.get("userId"),
                cart.get("total"),
                cart.get("totalQuantity"),
            ))

            for item in cart.get("products", []):
                quantity = item.get("quantity") or 0
                price = item.get("price") or 0

                conn.execute("""
                    INSERT OR REPLACE INTO cart_items
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    cart["id"],
                    item["id"],
                    quantity,
                    price,
                    quantity * price,
                ))

    print(f"Loaded {len(products)} products and {len(carts)} carts.")
    print(f"Database saved to {DB_PATH}")


if __name__ == "__main__":
    main()
