
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PRIMARY = "#1F4E79"
ACCENT  = "#C8553D"

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

# Only the two CSVs we actually need
REQUIRED_FILES = ["order_items.csv", "products.csv"]


def find_data_folder(user_path: Path) -> Path:
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
        f"Files actually present: {found if found else '(none)'}"
    )


def chart_0_promo_roi(items: pd.DataFrame, products: pd.DataFrame, out_dir: Path) -> None:
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

    # 4a — GPM comparison
    ax = axes[0]
    labels   = ["Without Promo", "With Promo"]
    gpm_vals = [grp.loc[False, "gpm"], grp.loc[True, "gpm"]]
    bars = ax.bar(labels, gpm_vals, color=[PRIMARY, ACCENT],
                  edgecolor="white", linewidth=1.5, width=0.55)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Gross-Profit Margin: Promotions Erase Profit Entirely")
    ax.set_ylabel("Gross-Profit Margin (%)")
    for bar, v in zip(bars, gpm_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + (1 if v > 0 else -2.5),
                f"{v:+.1f}%", ha="center", fontsize=12, fontweight="bold",
                color="black" if v > 0 else "white")
    ax.set_ylim(-22, 28)

    # Compute the promo-line callout dynamically rather than hardcoding
    promo_lines = int(grp.loc[True, "lines"])
    total_lines = int(grp["lines"].sum())
    pct_promo   = promo_lines / total_lines * 100
    ax.text(0.02, 0.97,
            f"{promo_lines/1000:.0f}K lines used promo ({pct_promo:.0f}% of all)",
            transform=ax.transAxes, va="top", fontsize=9, color="#555",
            bbox=dict(boxstyle="round", facecolor="white", edgecolor="#ccc"))

    # 4b — volume / revenue / profit
    no_promo, yes_promo = grp.loc[False], grp.loc[True]
    cats = ["Lines\n(thousands)", "Net Revenue\n(B VND)", "Gross Profit\n(B VND)"]
    vals_no  = [no_promo["lines"]/1000,  no_promo["net"]/1e9,  no_promo["gp"]/1e9]
    vals_yes = [yes_promo["lines"]/1000, yes_promo["net"]/1e9, yes_promo["gp"]/1e9]

    x = np.arange(len(cats))
    w = 0.35
    ax = axes[1]
    b1 = ax.bar(x - w/2, vals_no,  w, label="Without Promo", color=PRIMARY, edgecolor="white")
    b2 = ax.bar(x + w/2, vals_yes, w, label="With Promo",    color=ACCENT,  edgecolor="white")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(cats)
    ax.set_title("Promotions Generate ~30% of Revenue but Negative Profit")
    ax.legend()
    for bars, vals in [(b1, vals_no), (b2, vals_yes)]:
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, v + (0.1 if v > 0 else -0.2),
                    f"{v:.1f}", ha="center", fontsize=9, fontweight="bold",
                    color="black" if v >= 0 else ACCENT)

    plt.tight_layout()

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "0_promo_roi.png"
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out_path.name}")

    # Also print the headline numbers so you have them for the report
    print("\n--- Insight 4 numbers (for your report) ---")
    print(f"  Lines without promo:  {int(no_promo['lines']):>10,}")
    print(f"  Lines with promo:     {int(yes_promo['lines']):>10,}  ({pct_promo:.1f}% of all)")
    print(f"  Net revenue no promo: {no_promo['net']/1e9:>10.2f} B VND")
    print(f"  Net revenue w/ promo: {yes_promo['net']/1e9:>10.2f} B VND")
    print(f"  Gross profit no promo:{no_promo['gp']/1e9:>10.2f} B VND  ({no_promo['gpm']:+.1f}% GPM)")
    print(f"  Gross profit w/ promo:{yes_promo['gp']/1e9:>10.2f} B VND  ({yes_promo['gpm']:+.1f}% GPM)")
    print(f"  Lifetime profit destroyed by promo: {-yes_promo['gp']/1e9:.2f} B VND")


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
    items    = pd.read_csv(data_dir / "order_items.csv", low_memory=False)
    products = pd.read_csv(data_dir / "products.csv")
    print(f"Loaded order_items ({len(items):,} rows) and products ({len(products):,} rows).")
    print(f"Writing chart → {out_dir}\n")

    chart_0_promo_roi(items, products, out_dir)

    print(f"\nDone. Chart saved to:\n  {out_dir / 'promo_roi.png'}")


if __name__ == "__main__":
    main()
