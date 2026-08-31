-- ============================================================
-- NOXVÉ Analytics — Database Schema
-- SQLite (portable to MySQL/Postgres with minor type tweaks)
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    collection   TEXT,               -- 'Noir' or 'Blanc'
    category     TEXT,               -- Tee / Polo / Shirt / Bottoms / Accessory / Combo
    price        REAL NOT NULL,
    unit_cost    REAL NOT NULL       -- Qikink POD cost
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id         INTEGER PRIMARY KEY,
    signup_date          TEXT NOT NULL,   -- date of first order
    city                 TEXT,
    acquisition_channel   TEXT,           -- Instagram Ads / Influencer / Organic / Google Ads / Referral
    age_group             TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER REFERENCES customers(customer_id),
    order_datetime  TEXT NOT NULL,
    payment_method  TEXT,             -- COD / Prepaid
    order_status    TEXT,             -- Delivered / RTO / Returned / Cancelled
    discount_code   TEXT,
    discount_pct    REAL,
    discount_amount REAL,
    shipping_fee    REAL,
    gross_amount    REAL,
    net_revenue     REAL
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER REFERENCES orders(order_id),
    product_id    INTEGER REFERENCES products(product_id),
    quantity      INTEGER,
    unit_price    REAL,
    line_total    REAL
);

CREATE TABLE IF NOT EXISTS marketing_spend (
    date        TEXT,
    channel     TEXT,
    spend       REAL,
    impressions INTEGER,
    clicks      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id);
