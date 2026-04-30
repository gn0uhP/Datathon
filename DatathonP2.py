"""
Datathon 2026 — Part 2: Chart generation script
================================================
Reads CSVs from a data folder and writes 9 PNG charts.

Usage:
    python generate_charts.py "<path-to-data-folder>"
    python generate_charts.py "<path-to-data-folder>" "<path-to-output-folder>"

Examples (Windows):
    python generate_charts.py "C:\\Users\\phong\\Downloads\\datathon-2026-round-1 (1)"
    python generate_charts.py "C:\\Users\\phong\\Downloads\\datathon-2026-round-1 (1)" "C:\\Users\\phong\\Downloads\\charts"

Examples (Mac / Linux):
    python generate_charts.py ~/Downloads/datathon-2026

If only the data folder is given, charts are written to a "charts" subfolder
next to the data folder.

Required CSVs in the data folder:
    sales.csv, orders.csv, order_items.csv, products.csv,
    customers.csv, returns.csv, reviews.csv, shipments.csv,
    web_traffic.csv, inventory.csv, geography.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
PRIMARY = "#1F4E79"
ACCENT  = "#C8553D"
TEAL    = "#2A9D8F"

plt.rcParams.update({
    "font.family":         "DejaVu Sans",
    "figure.facecolor":    "white",
    "axes.facecolor":      "white",
    "axes.spines.top":     False,
    "axes.spines.right":   False,
    "axes.grid":           True,
    "grid.alpha":          0.25,
    "grid.linestyle":      "--",
    "axes.titleweight":    "bold",
    "axes.titlesize":      12,
    "axes.labelsize":      10,
    "figure.dpi":          110,
})

REQUIRED_FILES = [
    "sales.csv", "orders.csv", "order_items.csv", "products.csv",
    "customers.csv", "returns.csv", "reviews.csv", "shipments.csv",
    "web_traffic.csv", "inventory.csv", "geography.csv",
]


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
def find_data_folder(user_path: Path) -> Path:
    """
    Locate the folder that actually contains the CSVs. If they aren't directly
    inside `user_path`, look one level deep — common for unzipped archives.
    """
    if not user_path.exists():
        raise SystemExit(
            f"Path not found:\n  {user_path}\n\n"
            "Check the spelling and that the folder exists. On Windows, wrap "
            "the path in double quotes if it contains spaces or parentheses."
        )
    if not user_path.is_dir():
        raise SystemExit(f"Not a folder: {user_path}")

    if all((user_path / f).exists() for f in REQUIRED_FILES):
        return user_path

    for sub in user_path.iterdir():
        if sub.is_dir() and all((sub / f).exists() for f in REQUIRED_FILES):
            print(f"(found CSVs in subfolder: {sub.name})")
            return sub

    found = sorted(p.name for p in user_path.iterdir() if p.is_file())
    missing = [f for f in REQUIRED_FILES if not (user_path / f).exists()]
    raise SystemExit(
        f"Couldn't find the dataset CSVs in:\n  {user_path}\n\n"
        f"Missing files: {missing}\n"
        f"Files actually present: {found if found else '(none)'}\n\n"
        "Make sure the folder contains the 11 CSVs directly "
        "(sales.csv, orders.csv, etc.)."
    )


def load_data(data_dir: Path) -> dict:
    def read(name, **kwargs):
        return pd.read_csv(data_dir / name, **kwargs)
    return {
        "sales":      read("sales.csv",       parse_dates=["Date"]),
        "orders":     read("orders.csv",      parse_dates=["order_date"]),
        "items":      read("order_items.csv", low_memory=False),
        "products":   read("products.csv"),
        "customers":  read("customers.csv",   parse_dates=["signup_date"]),
        "returns":    read("returns.csv",     parse_dates=["return_date"]),
        "reviews":    read("reviews.csv",     parse_dates=["review_date"]),
        "shipments":  read("shipments.csv",   parse_dates=["ship_date", "delivery_date"]),
        "web":        read("web_traffic.csv", parse_dates=["date"]),
        "inventory":  read("inventory.csv",   parse_dates=["snapshot_date"]),
        "geography":  read("geography.csv"),
    }


def save(fig, out_dir: Path, name: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / name, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {name}")


# ---------------------------------------------------------------------------
# Chart 1 — Revenue arc
# ---------------------------------------------------------------------------
def chart_01_revenue_arc(d, out):
    sales, orders, items = d["sales"], d["orders"], d["items"]
    web, returns, reviews, inventory = d["web"], d["returns"], d["reviews"], d["inventory"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    yearly_rev = sales.groupby(sales["Date"].dt.year)["Revenue"].sum() / 1e9
    ax = axes[0, 0]
    colors = [ACCENT if y == 2016 else PRIMARY for y in yearly_rev.index]
    ax.bar(yearly_rev.index, yearly_rev.values, color=colors, edgecolor="white", linewidth=1.2)
    ax.set_title("Annual Revenue: Rise (2012-16) → Peak → Collapse (2019)")
    ax.set_ylabel("Revenue (B VND)")
    ax.set_xlabel("Year")
    ax.set_xticks(yearly_rev.index)
    peak_y, peak_v = yearly_rev.idxmax(), yearly_rev.max()
    ax.annotate(f"PEAK\n{peak_v:.2f}B",
        xy=(peak_y, peak_v), xytext=(peak_y, peak_v + 0.25),
        ha="center", fontsize=9, fontweight="bold", color=ACCENT,
        arrowprops=dict(arrowstyle="->", color=ACCENT))
    ax.annotate("-50% drop\nin 2 years",
        xy=(2020, yearly_rev[2020]), xytext=(2020, yearly_rev[2020] + 0.6),
        ha="center", fontsize=9, color="#444",
        arrowprops=dict(arrowstyle="->", color="#666"))

    items["gross"] = items["quantity"] * items["unit_price"] - items["discount_amount"]
    order_value = items.groupby("order_id")["gross"].sum().reset_index()
    ord_full = orders.merge(order_value, on="order_id", how="left")
    ord_full["year"] = ord_full["order_date"].dt.year
    yearly = ord_full.groupby("year").agg(
        orders=("order_id", "count"),
        rev=("gross", "sum"),
    ).reset_index()
    yearly["aov"] = yearly["rev"] / yearly["orders"]

    ax = axes[0, 1]; ax2 = ax.twinx()
    ax.bar(yearly["year"], yearly["orders"] / 1000, color=PRIMARY, alpha=0.85)
    ax2.plot(yearly["year"], yearly["aov"] / 1000, color=ACCENT, marker="o", lw=2.4)
    ax.set_ylabel("Orders (thousands)", color=PRIMARY)
    ax2.set_ylabel("Avg Order Value (000 VND)", color=ACCENT)
    ax.set_title("Order Volume Crashed, but AOV Kept Rising")
    ax.set_xticks(yearly["year"])
    ax2.spines["right"].set_visible(True)
    ax.tick_params(axis="y", labelcolor=PRIMARY)
    ax2.tick_params(axis="y", labelcolor=ACCENT)
    ax2.grid(False)

    web["year"] = web["date"].dt.year
    sessions_y = web.groupby("year")["sessions"].sum() / 1e6
    orders_y   = orders.groupby(orders["order_date"].dt.year).size()
    conv = (orders_y / web.groupby("year")["sessions"].sum() * 100).dropna()

    ax = axes[1, 0]; ax2 = ax.twinx()
    ax.fill_between(sessions_y.index, sessions_y.values, color=PRIMARY, alpha=0.55)
    ax2.plot(conv.index, conv.values, color=ACCENT, marker="s", lw=2.4)
    ax.set_ylabel("Web Sessions (millions)", color=PRIMARY)
    ax2.set_ylabel("Order Conversion Rate (%)", color=ACCENT)
    ax.set_title("Traffic +63% but Conversion Collapsed -71%")
    ax2.spines["right"].set_visible(True)
    ax.tick_params(axis="y", labelcolor=PRIMARY)
    ax2.tick_params(axis="y", labelcolor=ACCENT)
    ax2.grid(False)
    ax.set_xticks(list(sessions_y.index))

    returns["year"] = returns["return_date"].dt.year
    reviews["year"] = reviews["review_date"].dt.year
    ret_rate  = returns.groupby("year").size() / orders.groupby(orders["order_date"].dt.year).size() * 100
    avg_rate  = reviews.groupby("year")["rating"].mean()
    fill_rate = inventory.groupby("year")["fill_rate"].mean() * 100

    ax = axes[1, 1]
    ax.plot(ret_rate.index, ret_rate.values, marker="o", lw=2, label="Return rate (%)", color=ACCENT)
    ax.plot(avg_rate.index, avg_rate.values * 20, marker="s", lw=2, label="Avg rating × 20", color=PRIMARY)
    ax.plot(fill_rate.index, fill_rate.values, marker="^", lw=2, label="Fill rate (%)", color=TEAL)
    ax.set_title("Operations Are Pristine — Quality, Returns, Fill Rate All Flat")
    ax.set_ylabel("Index value")
    ax.set_xticks(list(ret_rate.index))
    ax.legend(loc="center right", fontsize=8)
    ax.set_ylim(0, 100)

    plt.tight_layout()
    save(fig, out, "01_revenue_arc.png")


# ---------------------------------------------------------------------------
# Chart 2 — Seasonality
# ---------------------------------------------------------------------------
def chart_02_seasonality(d, out):
    sales = d["sales"].copy()
    sales["month"] = sales["Date"].dt.month
    sales["dow"]   = sales["Date"].dt.dayofweek

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))

    mom_idx = (sales.groupby("month")["Revenue"].mean()
               / sales.groupby("month")["Revenue"].mean().mean() * 100)
    months  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    colors  = [ACCENT if v > 120 else (PRIMARY if v < 80 else "#888") for v in mom_idx.values]

    ax = axes[0]
    ax.bar(months, mom_idx.values, color=colors, edgecolor="white", linewidth=1.2)
    ax.axhline(100, color="#444", lw=1, ls="--")
    ax.set_title("Monthly Revenue Index — Apr-Jun is Peak Season (+50% vs avg)")
    ax.set_ylabel("Index (100 = avg month)")
    for i, v in enumerate(mom_idx.values):
        ax.text(i, v + 1.5, f"{v:.0f}", ha="center", fontsize=8.5)

    heat = sales.pivot_table(index="dow", columns="month", values="Revenue", aggfunc="mean") / 1e6
    ax = axes[1]
    im = ax.imshow(heat.values, cmap="RdYlBu_r", aspect="auto")
    ax.set_xticks(range(12)); ax.set_xticklabels(months)
    ax.set_yticks(range(7));  ax.set_yticklabels(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    ax.set_title("Heatmap: Avg Daily Revenue (M VND) by Month × Weekday")
    ax.grid(False)
    plt.colorbar(im, ax=ax, label="M VND")
    for i in range(7):
        for j in range(12):
            v = heat.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 4 else "black")

    plt.tight_layout()
    save(fig, out, "02_seasonality.png")


# ---------------------------------------------------------------------------
# Chart 3 — Category & segment evolution
# ---------------------------------------------------------------------------
def chart_03_category_segment(d, out):
    items, orders, products = d["items"], d["orders"], d["products"]
    items = items.copy()
    items["gross"] = items["quantity"] * items["unit_price"] - items["discount_amount"]
    oi = (items.merge(orders[["order_id", "order_date"]], on="order_id")
                .merge(products[["product_id", "category", "segment"]], on="product_id"))
    oi["year"] = oi["order_date"].dt.year

    cat_pivot = oi.groupby(["year", "category"])["gross"].sum().unstack(fill_value=0) / 1e9
    seg_pivot = oi.groupby(["year", "segment"])["gross"].sum().unstack(fill_value=0) / 1e9

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    cat_colors = ["#264653", "#E76F51", "#2A9D8F", "#E9C46A"]
    ax = axes[0]
    cat_pivot.plot(kind="bar", stacked=True, ax=ax, color=cat_colors, edgecolor="white", linewidth=0.4)
    ax.set_title("Revenue by Category — Streetwear Concentration Risk")
    ax.set_ylabel("Revenue (B VND)"); ax.set_xlabel("Year")
    ax.legend(title="Category", loc="upper right", fontsize=9)
    ax.tick_params(axis="x", rotation=0)

    seg_colors = plt.cm.tab10(np.linspace(0, 1, len(seg_pivot.columns)))
    seg_share  = seg_pivot.div(seg_pivot.sum(axis=1), axis=0) * 100
    ax = axes[1]
    seg_share.plot(kind="area", stacked=True, ax=ax, alpha=0.85, color=seg_colors)
    ax.set_title("'Balanced' Segment Doubled (26%→49%); 'Everyday' Halved")
    ax.set_ylabel("Share of Revenue (%)"); ax.set_xlabel("Year")
    ax.set_xlim(2012, 2022); ax.set_ylim(0, 100)
    ax.legend(title="Segment", loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8)

    plt.tight_layout()
    save(fig, out, "03_category_segment.png")


# ---------------------------------------------------------------------------
# Chart 4 — Promotion ROI
# ---------------------------------------------------------------------------
def chart_04_promo_roi(d, out):
    items, products = d["items"], d["products"]
    items = items.copy()
    items["gross"]     = items["quantity"] * items["unit_price"]
    items["net"]       = items["gross"] - items["discount_amount"]
    items["has_promo"] = items["promo_id"].notna()

    oi = items.merge(products[["product_id", "cogs"]], on="product_id")
    oi["cogs_line"] = oi["quantity"] * oi["cogs"]
    oi["gp"]        = oi["net"] - oi["cogs_line"]

    grp = oi.groupby("has_promo").agg(
        lines=("gross", "count"),
        gross=("gross", "sum"),
        discount=("discount_amount", "sum"),
        net=("net", "sum"),
        cogs=("cogs_line", "sum"),
    )
    grp["gp"]  = grp["net"] - grp["cogs"]
    grp["gpm"] = grp["gp"] / grp["net"] * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    labels   = ["Without Promo", "With Promo"]
    gpm_vals = [grp.loc[False, "gpm"], grp.loc[True, "gpm"]]
    bars = ax.bar(labels, gpm_vals, color=[PRIMARY, ACCENT], edgecolor="white", linewidth=1.5, width=0.55)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Gross-Profit Margin: Promotions Erase Profit Entirely")
    ax.set_ylabel("Gross-Profit Margin (%)")
    for bar, v in zip(bars, gpm_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + (1 if v > 0 else -2.5),
                f"{v:+.1f}%", ha="center", fontsize=12, fontweight="bold",
                color="black" if v > 0 else "white")
    ax.set_ylim(-22, 28)
    ax.text(0.02, 0.97, "276K lines used promo (39% of all)",
            transform=ax.transAxes, va="top", fontsize=9, color="#555",
            bbox=dict(boxstyle="round", facecolor="white", edgecolor="#ccc"))

    no_promo, yes_promo = grp.loc[False], grp.loc[True]
    cats = ["Lines\n(thousands)", "Net Revenue\n(B VND)", "Gross Profit\n(B VND)"]
    vals_no  = [no_promo["lines"]/1000,  no_promo["net"]/1e9,  no_promo["gp"]/1e9]
    vals_yes = [yes_promo["lines"]/1000, yes_promo["net"]/1e9, yes_promo["gp"]/1e9]

    x = np.arange(len(cats)); w = 0.35
    ax = axes[1]
    b1 = ax.bar(x - w/2, vals_no,  w, label="Without Promo", color=PRIMARY, edgecolor="white")
    b2 = ax.bar(x + w/2, vals_yes, w, label="With Promo",    color=ACCENT,  edgecolor="white")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(cats)
    ax.set_title("Promotions Generate 30% of Revenue but Negative Profit")
    ax.legend()
    for bars, vals in [(b1, vals_no), (b2, vals_yes)]:
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, v + (0.1 if v > 0 else -0.2),
                    f"{v:.1f}", ha="center", fontsize=9, fontweight="bold",
                    color="black" if v >= 0 else ACCENT)

    plt.tight_layout()
    save(fig, out, "04_promo_roi.png")


# ---------------------------------------------------------------------------
# Chart 5 — Inventory paradox
# ---------------------------------------------------------------------------
def chart_05_inventory(d, out):
    inv = d["inventory"]
    inv_y = inv.groupby("year").agg(
        dos=("days_of_supply", "mean"),
        overstock=("overstock_flag", "mean"),
        stockout=("stockout_flag", "mean"),
        sell_through=("sell_through_rate", "mean"),
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]; ax2 = ax.twinx()
    ax.fill_between(inv_y.index, inv_y["dos"], color=ACCENT, alpha=0.4)
    ax.plot(inv_y.index, inv_y["dos"], color=ACCENT, lw=2.5, marker="o")
    ax2.plot(inv_y.index, inv_y["sell_through"] * 100, color=PRIMARY, lw=2, marker="s")
    ax.set_ylabel("Days of Supply", color=ACCENT)
    ax2.set_ylabel("Sell-through Rate (%)", color=PRIMARY)
    ax.set_title("Inventory Aging: 161 → 1,638 Days of Supply (10×)")
    ax.set_xticks(inv_y.index)
    ax.tick_params(axis="y", labelcolor=ACCENT)
    ax2.tick_params(axis="y", labelcolor=PRIMARY)
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)

    ax = axes[1]
    x = inv_y.index
    ax.bar(x - 0.2, inv_y["overstock"] * 100, 0.4, color=ACCENT, label="% Overstock months", edgecolor="white")
    ax.bar(x + 0.2, inv_y["stockout"]  * 100, 0.4, color=PRIMARY, label="% Stockout months", edgecolor="white")
    ax.set_title("Paradox: Both Overstock AND Stockout Rates Are High")
    ax.set_ylabel("% of Product-Months")
    ax.set_xticks(x); ax.legend(loc="upper left")
    ax.text(0.02, 0.55,
            "76% of product-months\nhave overstock\n67% have stockouts\n→ wrong inventory mix",
            transform=ax.transAxes, fontsize=9, color="#333",
            bbox=dict(boxstyle="round", facecolor="#fff3e6", edgecolor="#ccc"))

    plt.tight_layout()
    save(fig, out, "05_inventory.png")


# ---------------------------------------------------------------------------
# Chart 6 — Channel attribution gap
# ---------------------------------------------------------------------------
def chart_06_channel_gap(d, out):
    web, orders = d["web"], d["orders"]
    w22 = web[web["date"].dt.year == 2022]
    o22 = orders[orders["order_date"].dt.year == 2022]
    trf_share = w22.groupby("traffic_source")["sessions"].sum() / w22["sessions"].sum() * 100
    ord_share = o22["order_source"].value_counts(normalize=True) * 100

    combined = (pd.DataFrame({"traffic_share": trf_share, "order_share": ord_share})
                  .fillna(0)
                  .assign(gap=lambda x: x["order_share"] - x["traffic_share"])
                  .sort_values("traffic_share"))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    y = np.arange(len(combined))
    ax.barh(y - 0.2, combined["traffic_share"], 0.4, color=PRIMARY, label="Traffic share (%)")
    ax.barh(y + 0.2, combined["order_share"],   0.4, color=ACCENT,  label="Order share (%)")
    ax.set_yticks(y); ax.set_yticklabels(combined.index)
    ax.set_title("Channel Conversion Gap (2022): Where Traffic Doesn't Convert")
    ax.set_xlabel("Share (%)"); ax.legend(loc="lower right")
    for i, (_, row) in enumerate(combined.iterrows()):
        gap = row["gap"]
        color = TEAL if gap > 0 else ACCENT
        ax.text(max(row["traffic_share"], row["order_share"]) + 0.5, i,
                f"{gap:+.1f}pp", va="center", fontsize=9, fontweight="bold", color=color)

    plt.tight_layout()
    save(fig, out, "06_channel_gap.png")


# ---------------------------------------------------------------------------
# Chart 7 — Cohort + CLV
# ---------------------------------------------------------------------------
def chart_07_cohort_clv(d, out):
    items, orders, customers = d["items"], d["orders"], d["customers"]
    items = items.copy()
    items["gross"] = items["quantity"] * items["unit_price"] - items["discount_amount"]
    ord_rev = items.groupby("order_id")["gross"].sum().reset_index()

    ow = (orders.merge(ord_rev, on="order_id")
                .merge(customers[["customer_id", "signup_date", "acquisition_channel"]],
                       on="customer_id"))
    ow["cohort_year"] = ow["signup_date"].dt.year
    ow["order_year"]  = ow["order_date"].dt.year
    ow["years_since"] = ow["order_year"] - ow["cohort_year"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    cohorts_to_show = [2013, 2015, 2017, 2019, 2021]
    palette = plt.cm.viridis(np.linspace(0.15, 0.85, len(cohorts_to_show)))
    for c, color in zip(cohorts_to_show, palette):
        sub = ow[ow["cohort_year"] == c]
        size = sub["customer_id"].nunique()
        if size == 0:
            continue
        by_year = sub.groupby("years_since")["gross"].sum() / size / 1000
        ax.plot(by_year.index, by_year.values, marker="o", lw=2,
                label=f"{c} cohort (n={size:,})", color=color)
    ax.set_xlabel("Years Since Signup")
    ax.set_ylabel("Revenue per Customer (K VND)")
    ax.set_title("Cohort Revenue Curves — Stable Repeat Behaviour Across Cohorts")
    ax.legend(fontsize=8, loc="upper right")

    clv = (ow.groupby("acquisition_channel")
             .agg(customers=("customer_id", "nunique"), revenue=("gross", "sum"))
             .assign(clv=lambda x: x["revenue"] / x["customers"] / 1000)
             .sort_values("clv"))
    ax = axes[1]
    ax.barh(clv.index, clv["clv"], color=PRIMARY, edgecolor="white")
    ax.set_title("Customer Lifetime Value by Acquisition Channel (K VND)")
    ax.set_xlabel("Avg Lifetime Revenue per Customer (K VND)")
    for i, (idx, v) in enumerate(zip(clv.index, clv["clv"])):
        ax.text(v + 1, i, f"{v:.0f}K  ({clv.loc[idx, 'customers']:,} cust)", va="center", fontsize=9)
    ax.set_xlim(0, clv["clv"].max() * 1.25)

    plt.tight_layout()
    save(fig, out, "07_cohort_clv.png")


# ---------------------------------------------------------------------------
# Chart 8 — Forecast
# ---------------------------------------------------------------------------
def chart_08_forecast(d, out):
    sales = d["sales"].sort_values("Date").reset_index(drop=True)
    monthly = sales.set_index("Date").resample("ME")["Revenue"].sum() / 1e9

    trend = monthly.rolling(12, center=True, min_periods=6).mean()

    last24 = monthly.tail(24)
    x = np.arange(len(last24))
    slope, _ = np.polyfit(x, last24.values, 1)
    last_value = last24.values[-1]
    last_idx   = monthly.index[-1]

    future_dates = pd.date_range(last_idx + pd.offsets.MonthEnd(1), periods=18, freq="ME")
    future_x     = np.arange(1, 19)
    trend_proj   = last_value + slope * future_x

    seas_means       = monthly.groupby(monthly.index.month).mean() - monthly.mean()
    seas_for_future  = np.array([seas_means[d.month] for d in future_dates])
    forecast = np.maximum(trend_proj + seas_for_future * 0.5, monthly.min() * 0.7)

    fig, ax = plt.subplots(figsize=(14, 5.5))
    ax.plot(monthly.index, monthly.values, color=PRIMARY, lw=1.5, label="Historical Monthly Revenue")
    ax.plot(trend.index, trend.values, color=ACCENT, lw=2.5, ls="--", label="12-mo Trend")
    ax.plot(future_dates, forecast, color=TEAL, lw=2.5, marker="o", label="Naive Forecast 2023-H1 2024")
    ax.axvspan(future_dates[0], future_dates[-1], color=TEAL, alpha=0.08)
    ax.set_title("Monthly Revenue (B VND): History, Trend & Naive Forecast")
    ax.set_ylabel("Revenue (B VND)")
    ax.legend(loc="upper right")
    ax.set_xlim(monthly.index.min(), future_dates[-1])

    plt.tight_layout()
    save(fig, out, "08_forecast.png")


# ---------------------------------------------------------------------------
# Chart 9 — Geography
# ---------------------------------------------------------------------------
def chart_09_geography(d, out):
    items, orders, geography = d["items"], d["orders"], d["geography"]
    items = items.copy()
    items["gross"] = items["quantity"] * items["unit_price"] - items["discount_amount"]
    oi = (items.merge(orders[["order_id", "order_date", "zip"]], on="order_id")
                .merge(geography[["zip", "region", "city"]].drop_duplicates("zip"),
                       on="zip", how="left"))
    oi["year"] = oi["order_date"].dt.year

    reg_year   = oi.groupby(["year", "region"])["gross"].sum().unstack() / 1e9
    city_total = (oi.groupby(["region", "city"])["gross"].sum()
                    .sort_values(ascending=False).head(15) / 1e6)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    reg_year.plot(ax=ax, marker="o", lw=2.2, color=["#264653", "#E76F51", "#2A9D8F"])
    ax.set_title("Regional Revenue Trajectory — All Three Regions Track Together")
    ax.set_ylabel("Revenue (B VND)"); ax.set_xlabel("Year")
    ax.legend(title="Region")

    ax = axes[1]
    top_cities = city_total.reset_index()
    top_cities["label"] = top_cities["city"] + " (" + top_cities["region"] + ")"
    region_color = {"East": "#264653", "Central": "#E76F51", "West": "#2A9D8F"}
    ax.barh(top_cities["label"][::-1],
            top_cities["gross"][::-1],
            color=[region_color[r] for r in top_cities["region"][::-1]],
            edgecolor="white")
    ax.set_title("Top 15 Cities by Lifetime Revenue (M VND)")
    ax.set_xlabel("Revenue (M VND)")

    plt.tight_layout()
    save(fig, out, "09_geography.png")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
CHART_FUNCTIONS = [
    chart_01_revenue_arc,
    chart_02_seasonality,
    chart_03_category_segment,
    chart_04_promo_roi,
    chart_05_inventory,
    chart_06_channel_gap,
    chart_07_cohort_clv,
    chart_08_forecast,
    chart_09_geography,
]


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    user_path = Path(sys.argv[1]).expanduser().resolve()
    data_dir  = find_data_folder(user_path)

    if len(sys.argv) >= 3:
        out_dir = Path(sys.argv[2]).expanduser().resolve()
    else:
        out_dir = data_dir.parent / "charts"

    print(f"Loading data from: {data_dir}")
    data = load_data(data_dir)
    print(f"Loaded {len(data)} tables. Writing charts → {out_dir}\n")

    for fn in CHART_FUNCTIONS:
        fn(data, out_dir)

    print(f"\nDone. {len(CHART_FUNCTIONS)} charts saved to:\n  {out_dir}")


if __name__ == "__main__":
    main()