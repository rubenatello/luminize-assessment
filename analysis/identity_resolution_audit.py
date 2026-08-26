"""Generate row- and dollar-weighted identity coverage and exception reports."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def summarize(mask: pd.Series, scoped: pd.DataFrame) -> tuple[int, float, float, float]:
    rows = int(mask.sum())
    sales = float(scoped.loc[mask, "net_sales"].sum())
    return (
        rows,
        rows / len(scoped) * 100 if len(scoped) else 0.0,
        sales,
        sales / scoped["net_sales"].sum() * 100 if scoped["net_sales"].sum() else 0.0,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    transactions = pd.read_csv(args.transactions)
    scoped = transactions.loc[
        transactions["transaction_type"].isin(["Order", "Refund"])
    ].copy()
    scoped["sku"] = scoped["sku"].fillna("")
    scoped["canonical_sku"] = scoped["canonical_sku"].fillna("")
    scoped["brand"] = scoped["brand"].fillna("")
    scoped["asin"] = scoped["asin"].fillna("")

    alias = scoped["sku"].ne(scoped["canonical_sku"]) & scoped["canonical_sku"].ne("")
    exact = scoped["sku"].eq(scoped["canonical_sku"]) & scoped["canonical_sku"].ne("")
    unresolved_product = scoped["canonical_sku"].eq("")
    mapped_brand = scoped["brand_method"].eq("mapping") & scoped["brand"].ne("")
    inferred_brand = scoped["brand_method"].eq("prefix_fallback") & scoped["brand"].ne("")
    unresolved_brand = scoped["brand"].eq("")

    asin_product_counts = (
        scoped.loc[scoped["asin"].ne("")]
        .groupby("asin")["canonical_sku"]
        .nunique()
    )
    conflicting_asins = set(asin_product_counts[asin_product_counts > 1].index)
    asin_conflict = scoped["asin"].isin(conflicting_asins)
    asin_missing = scoped["asin"].eq("")
    asin_unique = ~(asin_conflict | asin_missing)

    definitions = [
        ("product", "exact_canonical_sku", "A", 100, exact, "publish"),
        ("product", "approved_sku_alias", "A", 95, alias, "publish_monitor_alias_volume"),
        ("product", "unresolved", "F", 0, unresolved_product, "quarantine"),
        ("brand", "approved_product_mapping", "A", 100, mapped_brand, "publish"),
        ("brand", "prefix_inference", "C", 60, inferred_brand, "brand_only_review"),
        ("brand", "unresolved", "F", 0, unresolved_brand, "quarantine"),
        ("asin_attribute", "unique_enriched_from_sku", "B", 90, asin_unique, "publish_attribute"),
        ("asin_attribute", "conflicting_asin", "F", 0, asin_conflict, "block_asin_only_join"),
        ("asin_attribute", "missing", "F", 0, asin_missing, "do_not_join"),
    ]

    coverage_rows = []
    for dimension, method, grade, score, mask, action in definitions:
        rows, row_pct, sales, sales_pct = summarize(mask, scoped)
        coverage_rows.append(
            {
                "dimension": dimension,
                "match_method": method,
                "confidence_grade": grade,
                "confidence_score": score,
                "rows": rows,
                "row_pct": round(row_pct, 2),
                "net_sales": round(sales, 2),
                "net_sales_pct": round(sales_pct, 2),
                "control_action": action,
            }
        )

    exceptions = []
    for asin in sorted(conflicting_asins):
        rows = scoped.loc[scoped["asin"].eq(asin)]
        exceptions.append(
            {
                "exception_type": "ASIN_CONFLICT",
                "identifier": asin,
                "affected_skus": "|".join(sorted(rows["canonical_sku"].unique())),
                "affected_brands": "|".join(sorted(rows["brand"].unique())),
                "rows": len(rows),
                "net_sales": round(float(rows["net_sales"].sum()), 2),
                "resolution": "Use approved SKU; block ASIN-only join until the product data owner corrects the mapping",
                "owner": "product_data_owner",
                "status": "open",
            }
        )
    for raw_sku, rows in scoped.loc[alias].groupby("sku"):
        exceptions.append(
            {
                "exception_type": "APPROVED_SKU_ALIAS",
                "identifier": raw_sku,
                "affected_skus": "|".join(sorted(rows["canonical_sku"].unique())),
                "affected_brands": "|".join(sorted(rows["brand"].unique())),
                "rows": len(rows),
                "net_sales": round(float(rows["net_sales"].sum()), 2),
                "resolution": "Effective-dated approved alias; monitor usage trend",
                "owner": "product_data_owner",
                "status": "approved_monitor",
            }
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(coverage_rows).to_csv(
        output_dir / "identity_resolution_coverage.csv", index=False
    )
    pd.DataFrame(exceptions).to_csv(
        output_dir / "identity_resolution_exceptions.csv", index=False
    )


if __name__ == "__main__":
    main()
