-- ============================================================
-- NOXVÉ Analytics — Business Question Queries
-- Run against noxve_analytics.db (SQLite)
-- ============================================================

-- Q1. Monthly revenue trend (delivered orders only, net of discounts/shipping)
SELECT
    strftime('%Y-%m', order_datetime) AS month,
    COUNT(*)                          AS delivered_orders,
    ROUND(SUM(net_revenue), 0)        AS net_revenue,
    ROUND(AVG(net_revenue), 0)        AS avg_order_value
FROM orders
WHERE order_status = 'Delivered'
GROUP BY month
ORDER BY month;


-- Q2. Top-selling products by revenue and units
SELECT
    p.product_name,
    p.collection,
    SUM(oi.quantity)                 AS units_sold,
    ROUND(SUM(oi.line_total), 0)     AS gross_revenue,
    ROUND(SUM(oi.quantity * (p.price - p.unit_cost)), 0) AS gross_profit
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY p.product_id
ORDER BY gross_revenue DESC;


-- Q3. COD vs Prepaid — order volume, AOV, and RTO / failure rate
-- (the single most important operational question for an India D2C brand
--  fulfilling via COD-heavy Qikink POD)
SELECT
    payment_method,
    COUNT(*) AS total_orders,
    ROUND(AVG(net_revenue), 0) AS avg_order_value,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) / COUNT(*), 1) AS rto_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Delivered' THEN 1 ELSE 0 END) / COUNT(*), 1) AS delivered_rate_pct
FROM orders
GROUP BY payment_method;


-- Q4. RTO rate trend over time (has it improved since Razorpay/prepaid push?)
SELECT
    strftime('%Y-%m', order_datetime) AS month,
    payment_method,
    COUNT(*) AS orders,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) / COUNT(*), 1) AS rto_rate_pct
FROM orders
GROUP BY month, payment_method
ORDER BY month, payment_method;


-- Q5. City-wise performance (where is demand concentrated?)
SELECT
    c.city,
    COUNT(DISTINCT o.order_id) AS orders,
    ROUND(SUM(o.net_revenue), 0) AS net_revenue,
    ROUND(100.0 * SUM(CASE WHEN o.order_status='RTO' THEN 1 ELSE 0 END) / COUNT(*), 1) AS rto_rate_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.city
ORDER BY net_revenue DESC;


-- Q6. Acquisition channel performance — orders & revenue generated per channel
SELECT
    c.acquisition_channel,
    COUNT(DISTINCT c.customer_id)  AS customers_acquired,
    COUNT(o.order_id)              AS total_orders,
    ROUND(SUM(o.net_revenue), 0)   AS total_revenue
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.order_status='Delivered'
GROUP BY c.acquisition_channel
ORDER BY total_revenue DESC;


-- Q7. Marketing spend vs revenue by channel (ROAS) — paid channels only
-- Attributes delivered revenue to the channel that acquired the customer,
-- compared against that channel's total ad spend for the period.
WITH channel_revenue AS (
    SELECT c.acquisition_channel AS channel, SUM(o.net_revenue) AS revenue
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id AND o.order_status = 'Delivered'
    GROUP BY c.acquisition_channel
),
channel_spend AS (
    SELECT channel, SUM(spend) AS total_spend, SUM(clicks) AS total_clicks
    FROM marketing_spend
    GROUP BY channel
)
SELECT
    s.channel,
    ROUND(s.total_spend, 0) AS total_spend,
    s.total_clicks,
    ROUND(COALESCE(r.revenue, 0), 0) AS attributed_revenue,
    ROUND(COALESCE(r.revenue, 0) / NULLIF(s.total_spend, 0), 2) AS roas
FROM channel_spend s
LEFT JOIN channel_revenue r ON r.channel = s.channel
ORDER BY roas DESC;


-- Q8. Discount code effectiveness — does discounting grow AOV or shrink margin?
SELECT
    discount_code,
    COUNT(*) AS orders,
    ROUND(AVG(gross_amount), 0)  AS avg_gross_before_discount,
    ROUND(AVG(net_revenue), 0)   AS avg_net_after_discount,
    ROUND(SUM(discount_amount), 0) AS total_discount_given
FROM orders
WHERE order_status = 'Delivered'
GROUP BY discount_code
ORDER BY orders DESC;


-- Q9. New vs Repeat customer contribution to revenue
WITH order_rank AS (
    SELECT order_id, customer_id, net_revenue,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_datetime) AS purchase_no
    FROM orders
    WHERE order_status = 'Delivered'
)
SELECT
    CASE WHEN purchase_no = 1 THEN 'New Customer' ELSE 'Repeat Customer' END AS customer_type,
    COUNT(*) AS orders,
    ROUND(SUM(net_revenue), 0) AS revenue,
    ROUND(100.0 * SUM(net_revenue) / (SELECT SUM(net_revenue) FROM orders WHERE order_status='Delivered'), 1) AS pct_of_total_revenue
FROM order_rank
GROUP BY customer_type;


-- Q10. Monthly cohort retention — of customers acquired in month X,
-- what % placed another order in each subsequent month?
WITH first_order AS (
    SELECT customer_id, MIN(strftime('%Y-%m', order_datetime)) AS cohort_month
    FROM orders WHERE order_status = 'Delivered'
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT customer_id, strftime('%Y-%m', order_datetime) AS active_month
    FROM orders WHERE order_status = 'Delivered'
)
SELECT
    f.cohort_month,
    a.active_month,
    (CAST(strftime('%Y', a.active_month || '-01') AS INTEGER) * 12 + CAST(strftime('%m', a.active_month || '-01') AS INTEGER))
    - (CAST(strftime('%Y', f.cohort_month || '-01') AS INTEGER) * 12 + CAST(strftime('%m', f.cohort_month || '-01') AS INTEGER)) AS month_index,
    COUNT(DISTINCT a.customer_id) AS active_customers
FROM first_order f
JOIN activity a ON a.customer_id = f.customer_id
GROUP BY f.cohort_month, a.active_month
ORDER BY f.cohort_month, a.active_month;


-- Q11. RFM base table — Recency, Frequency, Monetary per customer
-- (feeds the Python segmentation script / Power BI or Tableau model)
SELECT
    customer_id,
    julianday('2026-09-01') - julianday(MAX(order_datetime)) AS recency_days,
    COUNT(*)                     AS frequency,
    ROUND(SUM(net_revenue), 0)   AS monetary
FROM orders
WHERE order_status = 'Delivered'
GROUP BY customer_id;


-- Q12. Combo vs Individual-item performance — do bundles drive higher AOV?
SELECT
    p.category,
    COUNT(DISTINCT oi.order_id) AS orders_containing,
    ROUND(AVG(o.net_revenue), 0) AS avg_order_value
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY p.category
ORDER BY avg_order_value DESC;
