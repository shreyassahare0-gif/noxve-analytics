"""
NOXVÉ Analytics — EDA, RFM Segmentation, Cohort Retention & Statistical Testing
--------------------------------------------------------------------------------
Data Analyst portfolio project. Reads from noxve_analytics.db (SQLite),
cleans/validates data, answers business questions with Pandas, runs a
chi-square significance test on the COD RTO problem, segments customers
with RFM scoring, and exports clean tables for Power BI / Tableau + charts.
"""

import sqlite3
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

sns.set_theme(style="whitegrid")
BASE = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE, "..", "noxve_analytics.db")
CHART_DIR = os.path.join(BASE, "..", "charts")
DATA_DIR = os.path.join(BASE, "..", "data")
os.makedirs(CHART_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
orders = pd.read_sql("SELECT * FROM orders", conn, parse_dates=["order_datetime"])
customers = pd.read_sql("SELECT * FROM customers", conn, parse_dates=["signup_date"])
products = pd.read_sql("SELECT * FROM products", conn)
order_items = pd.read_sql("SELECT * FROM order_items", conn)
marketing = pd.read_sql("SELECT * FROM marketing_spend", conn, parse_dates=["date"])

print("=" * 70)
print("STEP 1 — DATA QUALITY CHECK")
print("=" * 70)
for name, df in [("orders", orders), ("customers", customers),
                  ("order_items", order_items), ("marketing", marketing)]:
    nulls = df.isnull().sum().sum()
    dupes = df.duplicated().sum()
    print(f"{name:15s} rows={len(df):5d}  nulls={nulls:3d}  duplicate_rows={dupes}")

delivered = orders[orders.order_status == "Delivered"].copy()
delivered["month"] = delivered["order_datetime"].dt.to_period("M").astype(str)

# ---------------------------------------------------------------------------
# STEP 2 — MONTHLY REVENUE TREND
# ---------------------------------------------------------------------------
monthly = delivered.groupby("month").agg(
    orders=("order_id", "count"),
    revenue=("net_revenue", "sum"),
    aov=("net_revenue", "mean")
).reset_index()

fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(monthly["month"], monthly["revenue"], color="#B08D57", label="Net Revenue (Rs.)")
ax1.set_ylabel("Net Revenue (Rs.)")
ax1.set_xlabel("Month")
ax1.tick_params(axis="x", rotation=45)
ax2 = ax1.twinx()
ax2.plot(monthly["month"], monthly["orders"], color="#111111", marker="o", label="Orders")
ax2.set_ylabel("Delivered Orders")
fig.suptitle("NOXVÉ — Monthly Revenue & Order Volume (Year 1)")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "01_monthly_revenue_trend.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# STEP 3 — PRODUCT PERFORMANCE
# ---------------------------------------------------------------------------
items_full = order_items.merge(products, on="product_id").merge(
    orders[["order_id", "order_status"]], on="order_id"
)
items_delivered = items_full[items_full.order_status == "Delivered"]
prod_perf = items_delivered.groupby("product_name").agg(
    units_sold=("quantity", "sum"),
    revenue=("line_total", "sum")
).reset_index().sort_values("revenue", ascending=False)

fig, ax = plt.subplots(figsize=(9, 6))
sns.barplot(data=prod_perf, y="product_name", x="revenue", color="#B08D57", ax=ax)
ax.set_title("NOXVÉ — Revenue by Product")
ax.set_xlabel("Revenue (Rs.)")
ax.set_ylabel("")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "02_product_performance.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# STEP 4 — COD vs PREPAID RTO ANALYSIS + CHI-SQUARE TEST (Stats module)
# ---------------------------------------------------------------------------
orders["is_rto"] = (orders["order_status"] == "RTO").astype(int)
contingency = pd.crosstab(orders["payment_method"], orders["is_rto"])
chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

rto_summary = orders.groupby("payment_method").agg(
    total_orders=("order_id", "count"),
    rto_orders=("is_rto", "sum")
)
rto_summary["rto_rate_pct"] = (rto_summary["rto_orders"] / rto_summary["total_orders"] * 100).round(1)

print("\n" + "=" * 70)
print("STEP 4 — COD vs PREPAID RTO (RETURN-TO-ORIGIN) ANALYSIS")
print("=" * 70)
print(rto_summary)
print(f"\nChi-square test of independence (payment_method vs RTO):")
print(f"  chi2 = {chi2:.2f}, p-value = {p_value:.6f}, dof = {dof}")
print(f"  --> {'Statistically significant' if p_value < 0.05 else 'Not significant'} "
      f"relationship between payment method and RTO risk (alpha=0.05)")

fig, ax = plt.subplots(figsize=(6, 5))
sns.barplot(data=rto_summary.reset_index(), x="payment_method", y="rto_rate_pct",
            palette=["#111111", "#B08D57"], ax=ax)
ax.set_title(f"RTO Rate: COD vs Prepaid  (chi2 p-value={p_value:.4f})")
ax.set_ylabel("RTO Rate (%)")
ax.set_xlabel("")
for i, v in enumerate(rto_summary["rto_rate_pct"]):
    ax.text(i, v + 0.4, f"{v}%", ha="center", fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "03_cod_rto_analysis.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# STEP 5 — MARKETING CHANNEL ROAS
# ---------------------------------------------------------------------------
cust_rev = orders[orders.order_status == "Delivered"].merge(
    customers[["customer_id", "acquisition_channel"]], on="customer_id"
).groupby("acquisition_channel")["net_revenue"].sum().reset_index()

spend_by_channel = marketing.groupby("channel")["spend"].sum().reset_index()
roas = spend_by_channel.merge(cust_rev, left_on="channel", right_on="acquisition_channel", how="left")
roas["net_revenue"] = roas["net_revenue"].fillna(0)
roas["roas"] = (roas["net_revenue"] / roas["spend"]).round(2)

fig, ax = plt.subplots(figsize=(8, 5))
sns.barplot(data=roas.sort_values("roas", ascending=False), x="channel", y="roas",
            color="#B08D57", ax=ax)
ax.set_title("Marketing Channel ROAS (Revenue / Spend)")
ax.set_ylabel("ROAS (x)")
ax.set_xlabel("")
ax.tick_params(axis="x", rotation=20)
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "04_channel_roas.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# STEP 6 — RFM SEGMENTATION
# ---------------------------------------------------------------------------
snapshot_date = orders["order_datetime"].max() + pd.Timedelta(days=1)
rfm = delivered.groupby("customer_id").agg(
    recency=("order_datetime", lambda x: (snapshot_date - x.max()).days),
    frequency=("order_id", "count"),
    monetary=("net_revenue", "sum")
).reset_index()

rfm["r_score"] = pd.qcut(rfm["recency"], 4, labels=[4, 3, 2, 1]).astype(int)
rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["m_score"] = pd.qcut(rfm["monetary"], 4, labels=[1, 2, 3, 4]).astype(int)
rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

def segment(row):
    if row.rfm_score >= 10:
        return "Champions"
    elif row.rfm_score >= 8:
        return "Loyal Customers"
    elif row.r_score <= 2 and row.f_score >= 3:
        return "At Risk (was loyal)"
    elif row.r_score >= 3 and row.f_score == 1:
        return "New / Recent"
    else:
        return "Needs Attention"

rfm["segment"] = rfm.apply(segment, axis=1)
rfm.to_csv(os.path.join(DATA_DIR, "customer_rfm_segments.csv"), index=False)

print("\n" + "=" * 70)
print("STEP 6 — RFM CUSTOMER SEGMENTS")
print("=" * 70)
print(rfm["segment"].value_counts())
print("\nRevenue contribution by segment:")
seg_rev = rfm.groupby("segment")["monetary"].sum().sort_values(ascending=False)
print(seg_rev)

fig, ax = plt.subplots(figsize=(8, 6))
seg_counts = rfm["segment"].value_counts()
colors = sns.color_palette("dark:#B08D57", n_colors=len(seg_counts))
wedges, texts, autotexts = ax.pie(
    seg_counts, labels=seg_counts.index, autopct="%1.0f%%", colors=colors,
    wedgeprops={"edgecolor": "white"}, pctdistance=0.75
)
for t in autotexts:
    t.set_color("white")
    t.set_fontweight("bold")
ax.set_title("Customer Base by RFM Segment")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "05_rfm_segments.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# STEP 7 — COHORT RETENTION HEATMAP
# ---------------------------------------------------------------------------
first_order = delivered.groupby("customer_id")["order_datetime"].min().dt.to_period("M")
delivered["cohort_month"] = delivered["customer_id"].map(first_order)
delivered["order_month"] = delivered["order_datetime"].dt.to_period("M")
delivered["month_index"] = (delivered["order_month"] - delivered["cohort_month"]).apply(lambda x: x.n)

cohort_counts = delivered.groupby(["cohort_month", "month_index"])["customer_id"].nunique().reset_index()
cohort_pivot = cohort_counts.pivot(index="cohort_month", columns="month_index", values="customer_id")
cohort_size = cohort_pivot.iloc[:, 0]
retention = cohort_pivot.divide(cohort_size, axis=0).round(3) * 100

fig, ax = plt.subplots(figsize=(11, 6))
sns.heatmap(retention, annot=True, fmt=".0f", cmap="YlOrBr", cbar_kws={"label": "% retained"}, ax=ax)
ax.set_title("Monthly Cohort Retention (%)")
ax.set_xlabel("Months since first order")
ax.set_ylabel("Acquisition cohort")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "06_cohort_retention.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# STEP 8 — EXPORT DENORMALIZED TABLE FOR POWER BI / TABLEAU
# ---------------------------------------------------------------------------
bi_export = (order_items
             .merge(orders, on="order_id")
             .merge(products, on="product_id")
             .merge(customers, on="customer_id"))
bi_export.to_csv(os.path.join(DATA_DIR, "bi_master_table.csv"), index=False)

print("\n" + "=" * 70)
print("DONE. Charts saved to /charts, BI-ready tables saved to /data")
print("=" * 70)
print(f"Overall delivered revenue: Rs.{delivered['net_revenue'].sum():,.0f}")
print(f"Overall AOV (delivered): Rs.{delivered['net_revenue'].mean():,.0f}")
print(f"Total customers: {len(customers)} | Repeat purchase customers: {(rfm.frequency > 1).sum()} "
      f"({(rfm.frequency > 1).mean()*100:.1f}%)")

conn.close()
