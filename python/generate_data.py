"""
NOXVÉ Analytics — Synthetic Dataset Generator
------------------------------------------------
Generates a realistic 12-month order history for a D2C streetwear brand
(modeled on NOXVÉ's real catalog, POD fulfillment via Qikink, and COD-heavy
Indian D2C dynamics) for portfolio / resume project purposes.

This is SYNTHETIC data engineered to be realistic (seasonality, growth,
COD vs prepaid RTO risk, repeat-customer behaviour) — not real NOXVÉ sales.
"""

import numpy as np
import pandas as pd
import sqlite3
import os

np.random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "noxve_analytics.db")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. PRODUCTS  (real NOXVÉ launch catalog)
# ---------------------------------------------------------------------------
products = [
    # product_id, name, collection, category, price, cost_pct_of_price
    (1, "Oversized Tee - Noir",     "Noir",  "Tee",       999,  0.52),
    (2, "Oversized Tee - Blanc",    "Blanc", "Tee",       999,  0.52),
    (3, "Terry Oversized Tee",      "Noir",  "Tee",       1299, 0.50),
    (4, "Acid Wash Tee",            "Noir",  "Tee",       1199, 0.48),
    (5, "Men's Polo",               "Blanc", "Polo",      1099, 0.50),
    (6, "Oversized Shirt",          "Noir",  "Shirt",     1599, 0.47),
    (7, "Sweatpants",               "Noir",  "Bottoms",   1499, 0.49),
    (8, "Baseball Cap",             "Blanc", "Accessory", 699,  0.55),
    (9, "Terry Shorts",             "Blanc", "Bottoms",   999,  0.50),
    (10, "Noir Starter Combo",      "Noir",  "Combo",     2199, 0.51),
    (11, "Blanc Essentials Combo",  "Blanc", "Combo",     2299, 0.50),
    (12, "Full Fit Combo",          "Noir",  "Combo",     3499, 0.49),
]
products_df = pd.DataFrame(products, columns=[
    "product_id", "product_name", "collection", "category", "price", "cost_pct"
])
products_df["unit_cost"] = (products_df["price"] * products_df["cost_pct"]).round(0)
products_df.drop(columns=["cost_pct"], inplace=True)

# popularity weights (tees & combos sell more than shirts/caps)
pop_weight = {1: 14, 2: 11, 3: 9, 4: 8, 5: 6, 6: 5, 7: 9, 8: 7, 9: 8, 10: 9, 11: 7, 12: 7}

# ---------------------------------------------------------------------------
# 2. TIMELINE & MONTHLY ORDER TARGETS (12 months, seasonality baked in)
# ---------------------------------------------------------------------------
months = pd.date_range("2025-09-01", periods=12, freq="MS")
monthly_targets = {
    "2025-09": 25,   # soft launch
    "2025-10": 55,   # Diwali festive push
    "2025-11": 70,   # post-Diwali momentum, paid ads start
    "2025-12": 90,   # year-end sale
    "2026-01": 75,   # Republic Day sale, post-holiday dip
    "2026-02": 55,   # lull
    "2026-03": 60,
    "2026-04": 65,
    "2026-05": 70,
    "2026-06": 85,   # Razorpay prepaid launch, summer drop
    "2026-07": 95,   # influencer collabs, ad scale-up
    "2026-08": 90,
}

cities = ["Nagpur", "Mumbai", "Pune", "Delhi", "Bengaluru", "Hyderabad",
          "Ahmedabad", "Jaipur", "Lucknow", "Indore", "Nashik", "Kolkata"]
city_weight = [22, 12, 9, 10, 8, 6, 6, 5, 5, 6, 5, 6]  # Nagpur weighted (founder's home base/network)

channels = ["Instagram Ads", "Influencer", "Organic/Direct", "Google Ads", "Referral"]
channel_weight_early = [30, 15, 35, 10, 10]   # Sep-Nov
channel_weight_mid   = [35, 20, 25, 12, 8]    # Dec-Mar
channel_weight_late  = [32, 25, 18, 15, 10]   # Apr-Aug (influencer + google ramp)

discount_codes = ["NONE", "WELCOME10", "LAUNCH15", "FESTIVE20", "REF10"]

age_groups = ["18-22", "23-27", "28-34", "35+"]
age_weight = [35, 40, 18, 7]

# ---------------------------------------------------------------------------
# 3. GENERATE CUSTOMERS + ORDERS DAY BY DAY
# ---------------------------------------------------------------------------
customers = {}  # customer_id -> dict
next_cust_id = 1
orders = []
order_items = []
next_order_id = 1
next_item_id = 1

for m_start in months:
    m_key = m_start.strftime("%Y-%m")
    m_target = monthly_targets[m_key]
    days_in_month = pd.Period(m_key).days_in_month
    days = pd.date_range(m_start, periods=days_in_month, freq="D")

    # month index 0-11 drives repeat-customer probability growth
    m_idx = months.get_loc(m_start)
    repeat_prob = min(0.05 + m_idx * 0.028, 0.38)

    # payment mix shifts after Razorpay + Video KYC rollout (~June 2026, m_idx=9)
    prepaid_prob = 0.15 if m_idx < 9 else 0.45

    if m_key <= "2025-11":
        chan_w = channel_weight_early
    elif m_key <= "2026-03":
        chan_w = channel_weight_mid
    else:
        chan_w = channel_weight_late

    # distribute month's orders across days: weekends get ~1.6x weight
    day_weights = np.array([1.6 if d.weekday() >= 5 else 1.0 for d in days])
    day_weights = day_weights / day_weights.sum()
    daily_counts = np.random.multinomial(m_target, day_weights)

    for day, n_orders in zip(days, daily_counts):
        for _ in range(n_orders):
            is_repeat = (len(customers) > 0) and (np.random.rand() < repeat_prob)
            if is_repeat:
                cust_id = np.random.choice(list(customers.keys()))
            else:
                cust_id = next_cust_id
                next_cust_id += 1
                customers[cust_id] = {
                    "customer_id": cust_id,
                    "signup_date": day.strftime("%Y-%m-%d"),
                    "city": np.random.choice(cities, p=np.array(city_weight) / sum(city_weight)),
                    "acquisition_channel": np.random.choice(channels, p=np.array(chan_w) / sum(chan_w)),
                    "age_group": np.random.choice(age_groups, p=np.array(age_weight) / sum(age_weight)),
                }

            order_id = next_order_id
            next_order_id += 1

            payment_method = "Prepaid" if np.random.rand() < prepaid_prob else "COD"

            # RTO risk: much higher for COD
            rto_prob = 0.20 if payment_method == "COD" else 0.04
            return_prob = 0.05  # post-delivery size/quality return, independent of payment
            cancel_prob = 0.03

            roll = np.random.rand()
            if roll < cancel_prob:
                status = "Cancelled"
            elif roll < cancel_prob + rto_prob:
                status = "RTO"
            elif roll < cancel_prob + rto_prob + return_prob:
                status = "Returned"
            else:
                status = "Delivered"

            # discount code — more common in festive months
            festive = m_key in ("2025-10", "2025-11", "2025-12", "2026-01")
            discount_prob = 0.55 if festive else 0.35
            if np.random.rand() < discount_prob:
                code = np.random.choice(["WELCOME10", "LAUNCH15", "FESTIVE20", "REF10"])
                discount_pct = {"WELCOME10": 10, "LAUNCH15": 15, "FESTIVE20": 20, "REF10": 10}[code]
            else:
                code = "NONE"
                discount_pct = 0

            n_items = np.random.choice([1, 2, 3], p=[0.62, 0.28, 0.10])
            chosen_products = np.random.choice(
                products_df["product_id"],
                size=n_items,
                replace=False if n_items <= len(pop_weight) else True,
                p=np.array([pop_weight[p] for p in products_df["product_id"]]) / sum(pop_weight.values())
            )

            order_gross = 0.0
            for pid in chosen_products:
                qty = 1 if np.random.rand() < 0.85 else 2
                unit_price = float(products_df.loc[products_df.product_id == pid, "price"].values[0])
                line_total = unit_price * qty
                order_gross += line_total
                order_items.append((next_item_id, order_id, int(pid), qty, unit_price, line_total))
                next_item_id += 1

            discount_amount = round(order_gross * discount_pct / 100, 2)
            net_revenue = round(order_gross - discount_amount, 2)
            shipping_fee = 0 if net_revenue >= 1499 or payment_method == "Prepaid" else 49
            net_revenue += shipping_fee

            order_hour = int(np.clip(np.random.normal(15, 4), 8, 23))
            order_datetime = day + pd.Timedelta(hours=order_hour, minutes=int(np.random.rand() * 60))

            orders.append((
                order_id, cust_id, order_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                payment_method, status, code, discount_pct, discount_amount,
                shipping_fee, round(order_gross, 2), net_revenue
            ))

customers_df = pd.DataFrame(customers.values())
orders_df = pd.DataFrame(orders, columns=[
    "order_id", "customer_id", "order_datetime", "payment_method", "order_status",
    "discount_code", "discount_pct", "discount_amount", "shipping_fee",
    "gross_amount", "net_revenue"
])
order_items_df = pd.DataFrame(order_items, columns=[
    "order_item_id", "order_id", "product_id", "quantity", "unit_price", "line_total"
])

# ---------------------------------------------------------------------------
# 4. MARKETING SPEND (daily, by channel) — scales up over the year
# ---------------------------------------------------------------------------
all_days = pd.date_range("2025-09-01", "2026-08-31", freq="D")
marketing_rows = []
paid_channels = ["Instagram Ads", "Influencer", "Google Ads"]
base_spend = {"Instagram Ads": 250, "Influencer": 150, "Google Ads": 100}
for d in all_days:
    m_idx = (d.year - 2025) * 12 + d.month - 9 if d.year == 2025 else (d.month + 3)
    growth_factor = 1 + (m_idx * 0.16)
    for ch in paid_channels:
        spend = round(base_spend[ch] * growth_factor * np.random.uniform(0.7, 1.3), 2)
        impressions = int(spend * np.random.uniform(35, 55))
        ctr = np.random.uniform(0.015, 0.035)
        clicks = int(impressions * ctr)
        marketing_rows.append((d.strftime("%Y-%m-%d"), ch, spend, impressions, clicks))

marketing_df = pd.DataFrame(marketing_rows, columns=[
    "date", "channel", "spend", "impressions", "clicks"
])

# ---------------------------------------------------------------------------
# 5. SAVE CSVs
# ---------------------------------------------------------------------------
products_df.to_csv(os.path.join(OUT_DIR, "products.csv"), index=False)
customers_df.to_csv(os.path.join(OUT_DIR, "customers.csv"), index=False)
orders_df.to_csv(os.path.join(OUT_DIR, "orders.csv"), index=False)
order_items_df.to_csv(os.path.join(OUT_DIR, "order_items.csv"), index=False)
marketing_df.to_csv(os.path.join(OUT_DIR, "marketing_spend.csv"), index=False)

# ---------------------------------------------------------------------------
# 6. BUILD SQLITE DATABASE (for SQL practice module)
# ---------------------------------------------------------------------------
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
products_df.to_sql("products", conn, index=False)
customers_df.to_sql("customers", conn, index=False)
orders_df.to_sql("orders", conn, index=False)
order_items_df.to_sql("order_items", conn, index=False)
marketing_df.to_sql("marketing_spend", conn, index=False)
conn.close()

print(f"Customers: {len(customers_df)}")
print(f"Orders: {len(orders_df)}")
print(f"Order items: {len(order_items_df)}")
print(f"Marketing rows: {len(marketing_df)}")
print(f"Total net revenue (all statuses): Rs.{orders_df['net_revenue'].sum():,.0f}")
print(f"Delivered-only revenue: Rs.{orders_df.loc[orders_df.order_status=='Delivered','net_revenue'].sum():,.0f}")
print("Order status split:")
print(orders_df.order_status.value_counts())
print("Payment method split:")
print(orders_df.payment_method.value_counts())
