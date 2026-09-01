#!/usr/bin/env python3
"""Allocate SKU-less Amazon costs for a directional management scenario.

Reported SKU contribution margin remains unchanged. This script creates a
separate estimated view using net sales share because the supplied settlement
rows do not include a reliable product key for these costs.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd


COST_TYPES = {
    "Advertising Cost": "allocated_advertising",
    "FBA Storage Fee": "allocated_fba_storage",
    "Subscription Fee": "allocated_subscription",
}


def build_two_decimal_export(frame: pd.DataFrame) -> pd.DataFrame:
    """Round allocations to cents while preserving each shared-cost total."""
    out = frame.copy()
    reconciled_money_columns = [
        "reported_contribution_margin",
        *COST_TYPES.values(),
    ]

    for column in reconciled_money_columns:
        exact = out[column].copy()
        rounded = exact.round(2)
        target = round(float(exact.sum()), 2)
        residual_cents = int(round((target - float(rounded.sum())) * 100))

        if residual_cents:
            remainders = exact - rounded
            order = remainders.sort_values(
                ascending=residual_cents < 0
            ).index.tolist()
            step = 0.01 if residual_cents > 0 else -0.01
            for offset in range(abs(residual_cents)):
                rounded.loc[order[offset % len(order)]] += step

        out[column] = rounded

    out["run_rate_threshold_result"] = (
        out["reported_contribution_margin"]
        - out["allocated_advertising"]
        - out["allocated_fba_storage"]
        - out["allocated_subscription"]
    )
    out["run_rate_threshold_margin_pct"] = (
        out["run_rate_threshold_result"] / out["net_sales"]
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sku-profitability",
        type=Path,
        default=Path("processed/sku_profitability.csv"),
    )
    parser.add_argument(
        "--platform-overhead",
        type=Path,
        default=Path("processed/platform_overhead.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("processed"))
    args = parser.parse_args()

    sku = pd.read_csv(args.sku_profitability)
    overhead = pd.read_csv(args.platform_overhead)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    required_sku = {"brand", "canonical_sku", "product_name", "net_sales", "contribution_margin"}
    missing_sku = required_sku.difference(sku.columns)
    if missing_sku:
        raise ValueError(f"Missing SKU profitability columns: {sorted(missing_sku)}")

    amounts = overhead.set_index("transaction_type")["signed_amount"]
    missing_types = set(COST_TYPES).difference(amounts.index)
    if missing_types:
        raise ValueError(f"Missing overhead transaction types: {sorted(missing_types)}")

    total_net_sales = float(sku["net_sales"].sum())
    if total_net_sales <= 0:
        raise ValueError("Total net sales must be positive for a net-sales allocation.")

    scenario = sku[
        [
            "brand",
            "canonical_sku",
            "product_name",
            "net_sales",
            "contribution_margin",
            "contribution_margin_pct",
        ]
    ].copy()
    scenario = scenario.rename(
        columns={
            "contribution_margin": "reported_contribution_margin",
            "contribution_margin_pct": "reported_contribution_margin_pct",
        }
    )
    scenario["net_sales_allocation_share"] = scenario["net_sales"] / total_net_sales

    for transaction_type, output_column in COST_TYPES.items():
        # Cost rows are negative in the source; allocation columns show positive deductions.
        scenario[output_column] = (
            -float(amounts.loc[transaction_type]) * scenario["net_sales_allocation_share"]
        )

    scenario["run_rate_threshold_result"] = (
        scenario["reported_contribution_margin"]
        - scenario["allocated_advertising"]
        - scenario["allocated_fba_storage"]
        - scenario["allocated_subscription"]
    )
    scenario["run_rate_threshold_margin_pct"] = (
        scenario["run_rate_threshold_result"] / scenario["net_sales"]
    )
    scenario["allocation_method"] = "net_sales_share"
    scenario["is_estimated"] = True

    brand = (
        scenario.groupby("brand", as_index=False)
        .agg(
            net_sales=("net_sales", "sum"),
            reported_contribution_margin=("reported_contribution_margin", "sum"),
            allocated_advertising=("allocated_advertising", "sum"),
            allocated_fba_storage=("allocated_fba_storage", "sum"),
            allocated_subscription=("allocated_subscription", "sum"),
            run_rate_threshold_result=("run_rate_threshold_result", "sum"),
        )
    )
    brand["reported_contribution_margin_pct"] = (
        brand["reported_contribution_margin"] / brand["net_sales"]
    )
    brand["run_rate_threshold_margin_pct"] = (
        brand["run_rate_threshold_result"] / brand["net_sales"]
    )
    brand["allocation_method"] = "net_sales_share"
    brand["is_estimated"] = True
    brand = brand.sort_values("net_sales", ascending=False)

    shared_cost_total = sum(float(-amounts.loc[name]) for name in COST_TYPES)
    expected_result = float(scenario["reported_contribution_margin"].sum() - shared_cost_total)
    actual_result = float(scenario["run_rate_threshold_result"].sum())
    if not math.isclose(actual_result, expected_result, abs_tol=0.01):
        raise AssertionError(
            f"Scenario does not reconcile: actual={actual_result:.2f}, "
            f"expected={expected_result:.2f}"
        )

    scenario_export = build_two_decimal_export(scenario)
    brand_export = build_two_decimal_export(brand)
    scenario_export.to_csv(
        args.output_dir / "allocated_profitability_scenario_by_sku.csv",
        index=False,
        float_format="%.2f",
    )
    brand_export.to_csv(
        args.output_dir / "allocated_profitability_scenario_by_brand.csv",
        index=False,
        float_format="%.2f",
    )

    summary = {
        "allocation_method": "net_sales_share",
        "is_estimated": True,
        "total_net_sales": round(total_net_sales, 2),
        "reported_contribution_margin": round(
            float(scenario["reported_contribution_margin"].sum()), 2
        ),
        "run_rate_threshold_result": round(actual_result, 2),
        "negative_skus": int((scenario["run_rate_threshold_result"] < 0).sum()),
        "total_skus": int(len(scenario)),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
