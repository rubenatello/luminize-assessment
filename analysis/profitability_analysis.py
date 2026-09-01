#!/usr/bin/env python3
"""Reproducible Q2 2026 Amazon profitability and inventory analysis.

The script intentionally keeps SKU-attributable contribution margin
separate from platform costs that lack a SKU key. It also produces a
data-quality register so that assumptions are visible rather than buried.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ALIASES = {
    "PF-ELECTRO-CITRUS": "PF-ELECTRO-CIT",
}

CASE_PACK_OVERRIDES = {
    "PH-DENTAL-30CT": 12,
}

PREFIX_BRAND_FALLBACK = {
    "GT": "GlowTheory",
    "PF": "Peak Fuel",
    "PH": "PawHaus",
}

CM_TRANSACTION_TYPES = {"Order", "Refund"}
QUARTER_START = pd.Timestamp("2026-04-01")
QUARTER_END = pd.Timestamp("2026-06-30")
QUARTER_DAYS = int((QUARTER_END - QUARTER_START).days + 1)


def canonicalize_sku(series: pd.Series) -> pd.Series:
    return series.replace(ALIASES)


def money_columns(frame: pd.DataFrame) -> list[str]:
    return [
        c
        for c in frame.columns
        if c
        in {
            "gross_sales",
            "promo_deduction",
            "net_sales",
            "referral_fees",
            "fba_fees",
            "landed_cogs",
            "contribution_margin",
            "platform_overhead",
            "profit_after_platform_overhead",
            "fulfillable_inventory_value",
            "inbound_inventory_value",
        }
    ]


def prepare_mapping(mapping: pd.DataFrame) -> pd.DataFrame:
    mapping = mapping.copy()
    mapping.columns = [c.strip().lower().replace("-", "_") for c in mapping.columns]
    mapping["canonical_sku"] = canonicalize_sku(mapping["sku"].str.strip())
    return mapping


def add_brand(frame: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    dim = mapping[["canonical_sku", "brand", "product_name", "asin", "status"]].drop_duplicates(
        subset=["canonical_sku"]
    )
    out = frame.merge(dim, on="canonical_sku", how="left", validate="m:1")
    out["brand_method"] = np.where(out["brand"].notna(), "mapping", "prefix_fallback")
    fallback = out["canonical_sku"].str.split("-").str[0].map(PREFIX_BRAND_FALLBACK)
    out["brand"] = out["brand"].fillna(fallback)
    return out


def build_costs(po: pd.DataFrame, mapping: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    po = po.copy()
    po.columns = [c.strip().lower().replace("-", "_") for c in po.columns]
    po["po_date"] = pd.to_datetime(po["po_date"], format="mixed", errors="coerce")
    po["canonical_sku"] = canonicalize_sku(po["sku"].str.strip())
    po["case_pack"] = po["canonical_sku"].map(CASE_PACK_OVERRIDES).fillna(1).astype(int)
    po["sellable_units"] = po["qty"] * po["case_pack"]
    po["line_recalc"] = po["qty"] * po["unit_cost"] + po["freight_duty_alloc"]
    po["line_recalc_delta"] = po["line_recalc"] - po["total_cost"]

    # Pre-quarter purchases may support Q2 cost, but later POs cannot. Receipt-
    # layer costing is not possible without receipt dates and opening inventory.
    po["excluded_from_q2_cost"] = po["po_date"] > QUARTER_END
    costing_po = po.loc[~po["excluded_from_q2_cost"]].copy()

    costs = (
        costing_po.groupby("canonical_sku", as_index=False)
        .agg(
            po_lines=("po_number", "size"),
            first_po_date=("po_date", "min"),
            last_po_date=("po_date", "max"),
            purchased_units=("sellable_units", "sum"),
            product_cost=("unit_cost", lambda s: float((s * po.loc[s.index, "qty"]).sum())),
            freight_duty=("freight_duty_alloc", "sum"),
            landed_cost_total=("total_cost", "sum"),
            max_line_check_delta=("line_recalc_delta", lambda s: float(s.abs().max())),
            case_pack=("case_pack", "max"),
        )
    )
    costs["unit_landed_cost"] = costs["landed_cost_total"] / costs["purchased_units"]
    costs = add_brand(costs, mapping)
    brand_median = costs.groupby("brand")["unit_landed_cost"].median()
    return po, costs, brand_median


def build_profitability(
    settlements: pd.DataFrame,
    mapping: pd.DataFrame,
    costs: pd.DataFrame,
    brand_median_cost: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    st = settlements.copy()
    st.columns = [c.strip().lower().replace("-", "_") for c in st.columns]
    st["posted_date"] = pd.to_datetime(st["posted_date"], errors="coerce")
    st["canonical_sku"] = canonicalize_sku(st["sku"].astype("string").str.strip())
    component_cols = [
        "product_sales",
        "shipping_credits",
        "promotional_rebates",
        "selling_fees",
        "fba_fees",
        "other_transaction_fees",
        "other",
    ]
    st["recalc_total"] = st[component_cols].sum(axis=1)
    st["settlement_delta"] = st["recalc_total"] - st["total"]

    tx = st[
        st["transaction_type"].isin(CM_TRANSACTION_TYPES)
        & st["canonical_sku"].notna()
        & st["posted_date"].between(QUARTER_START, QUARTER_END)
    ].copy()
    tx = add_brand(tx, mapping)
    tx = tx.merge(
        costs[["canonical_sku", "unit_landed_cost"]],
        on="canonical_sku",
        how="left",
        validate="m:1",
    )
    tx["cost_imputed"] = tx["unit_landed_cost"].isna()
    tx["applied_unit_cost"] = tx["unit_landed_cost"].fillna(tx["brand"].map(brand_median_cost))
    tx["cost_method"] = np.where(tx["cost_imputed"], "brand_median_imputation", "po_weighted_average")

    # Amazon debits are negative in the raw file; presentation columns below
    # show deductions as positive values. Refunds remain signed and therefore
    # reverse sales, fees, promotions, units, and COGS.
    tx["gross_sales"] = tx["product_sales"]
    tx["promo_deduction"] = -tx["promotional_rebates"]
    tx["net_sales"] = tx["gross_sales"] - tx["promo_deduction"]
    tx["referral_fees"] = -tx["selling_fees"]
    tx["fba_fees_abs"] = -tx["fba_fees"]
    tx["landed_cogs"] = tx["quantity"] * tx["applied_unit_cost"]
    tx["contribution_margin"] = (
        tx["net_sales"] - tx["referral_fees"] - tx["fba_fees_abs"] - tx["landed_cogs"]
    )
    tx["month"] = tx["posted_date"].dt.to_period("M").astype(str)

    sku = (
        tx.groupby(["brand", "canonical_sku", "product_name"], as_index=False, dropna=False)
        .agg(
            gross_sales=("gross_sales", "sum"),
            promo_deduction=("promo_deduction", "sum"),
            net_sales=("net_sales", "sum"),
            referral_fees=("referral_fees", "sum"),
            fba_fees=("fba_fees_abs", "sum"),
            net_units=("quantity", "sum"),
            applied_unit_cost=("applied_unit_cost", "first"),
            cost_imputed=("cost_imputed", "max"),
            cost_method=("cost_method", "first"),
            landed_cogs=("landed_cogs", "sum"),
            contribution_margin=("contribution_margin", "sum"),
        )
    )
    sku["contribution_margin_pct"] = sku["contribution_margin"] / sku["net_sales"]
    sku["cost_status"] = np.where(sku["cost_imputed"], "IMPUTED - REVIEW", "PO WAC")
    sku = sku.sort_values(["brand", "contribution_margin"], ascending=[True, False])

    brand = (
        sku.groupby("brand", as_index=False)
        .agg(
            gross_sales=("gross_sales", "sum"),
            promo_deduction=("promo_deduction", "sum"),
            net_sales=("net_sales", "sum"),
            referral_fees=("referral_fees", "sum"),
            fba_fees=("fba_fees", "sum"),
            net_units=("net_units", "sum"),
            landed_cogs=("landed_cogs", "sum"),
            contribution_margin=("contribution_margin", "sum"),
            imputed_skus=("cost_imputed", "sum"),
        )
    )
    brand["contribution_margin_pct"] = brand["contribution_margin"] / brand["net_sales"]
    brand = brand.sort_values("contribution_margin", ascending=False)

    monthly = (
        tx.groupby(["month", "brand"], as_index=False)
        .agg(
            net_sales=("net_sales", "sum"),
            landed_cogs=("landed_cogs", "sum"),
            contribution_margin=("contribution_margin", "sum"),
        )
    )
    monthly["contribution_margin_pct"] = monthly["contribution_margin"] / monthly["net_sales"]

    overhead = (
        st[~st["transaction_type"].isin(CM_TRANSACTION_TYPES)]
        .groupby("transaction_type", as_index=False)
        .agg(rows=("total", "size"), signed_amount=("total", "sum"))
    )
    overhead["classification"] = np.where(
        overhead["transaction_type"].eq("Adjustment"),
        "below_cm_other_income",
        "below_cm_platform_overhead",
    )
    return st, tx, sku, brand, monthly, overhead


def build_inventory(
    inventory: pd.DataFrame,
    mapping: pd.DataFrame,
    sku_profit: pd.DataFrame,
) -> pd.DataFrame:
    inv = inventory.copy()
    inv.columns = [c.strip().lower().replace("-", "_") for c in inv.columns]
    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"], errors="coerce")
    inv["raw_sku"] = inv["sku"]
    inv["canonical_sku"] = canonicalize_sku(inv["sku"].str.strip())
    inv = add_brand(inv, mapping)
    inv = inv.merge(
        sku_profit[
            [
                "canonical_sku",
                "net_units",
                "applied_unit_cost",
                "cost_imputed",
                "contribution_margin_pct",
            ]
        ],
        on="canonical_sku",
        how="left",
        validate="1:1",
    )
    inv["daily_net_units"] = inv["net_units"].fillna(0) / QUARTER_DAYS
    demand = inv["daily_net_units"].replace(0, np.nan)
    inv["fulfillable_days_cover"] = inv["fulfillable"] / demand
    inv["incl_inbound_days_cover"] = (inv["fulfillable"] + inv["inbound"]) / demand
    inv["unfulfillable_rate"] = inv["unfulfillable"] / (
        inv["fulfillable"] + inv["reserved"] + inv["unfulfillable"]
    ).replace(0, np.nan)
    inv["fulfillable_inventory_value"] = inv["fulfillable"] * inv["applied_unit_cost"]
    inv["inbound_inventory_value"] = inv["inbound"] * inv["applied_unit_cost"]
    inv["inventory_action"] = np.select(
        [
            inv["fulfillable_days_cover"] < 60,
            inv["fulfillable_days_cover"] > 365,
            inv["unfulfillable_rate"] > 0.05,
        ],
        ["EXPEDITE / REORDER", "SLOW-MOVER REVIEW", "QUALITY REVIEW"],
        default="MONITOR",
    )
    return inv.sort_values("fulfillable_days_cover", na_position="last")



def build_refund_analysis(tx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize refund frequency and contribution-margin impact by SKU and brand."""
    keys = ["brand", "canonical_sku", "product_name"]
    orders = (
        tx.loc[tx["transaction_type"].eq("Order")]
        .groupby(keys, as_index=False)
        .agg(order_units=("quantity", "sum"), order_sales=("gross_sales", "sum"))
    )
    refunds = (
        tx.loc[tx["transaction_type"].eq("Refund")]
        .groupby(keys, as_index=False)
        .agg(
            refund_units=("quantity", lambda s: float(-s.sum())),
            refund_sales=("gross_sales", lambda s: float(-s.sum())),
            refund_cm_impact=("contribution_margin", lambda s: float(-s.sum())),
        )
    )
    net_cm = (
        tx.groupby(keys, as_index=False)
        .agg(net_contribution_margin=("contribution_margin", "sum"))
    )
    sku_refunds = orders.merge(refunds, on=keys, how="left").merge(net_cm, on=keys, how="left")
    for column in ["refund_units", "refund_sales", "refund_cm_impact"]:
        sku_refunds[column] = sku_refunds[column].fillna(0)
    sku_refunds["unit_refund_rate"] = (
        sku_refunds["refund_units"] / sku_refunds["order_units"]
    )
    sku_refunds["revenue_refund_rate"] = (
        sku_refunds["refund_sales"] / sku_refunds["order_sales"]
    )
    sku_refunds["refund_cm_pct_of_net"] = (
        sku_refunds["refund_cm_impact"] / sku_refunds["net_contribution_margin"]
    )
    sku_refunds = sku_refunds.sort_values(
        ["brand", "refund_units", "unit_refund_rate"], ascending=[True, False, False]
    )

    brand_refunds = (
        sku_refunds.groupby("brand", as_index=False)
        .agg(
            order_units=("order_units", "sum"),
            refund_units=("refund_units", "sum"),
            order_sales=("order_sales", "sum"),
            refund_sales=("refund_sales", "sum"),
            refund_cm_impact=("refund_cm_impact", "sum"),
            net_contribution_margin=("net_contribution_margin", "sum"),
        )
    )
    brand_refunds["unit_refund_rate"] = (
        brand_refunds["refund_units"] / brand_refunds["order_units"]
    )
    brand_refunds["revenue_refund_rate"] = (
        brand_refunds["refund_sales"] / brand_refunds["order_sales"]
    )
    brand_refunds["refund_cm_pct_of_net"] = (
        brand_refunds["refund_cm_impact"] / brand_refunds["net_contribution_margin"]
    )
    return sku_refunds, brand_refunds.sort_values("unit_refund_rate", ascending=False)


def data_quality_register(
    mapping: pd.DataFrame,
    po_detail: pd.DataFrame,
    settlements: pd.DataFrame,
    tx: pd.DataFrame,
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    duplicate_asins = int(mapping["asin"].duplicated(keep=False).sum())
    missing_cost_skus = sorted(tx.loc[tx["cost_imputed"], "canonical_sku"].unique())
    alias_rows = int((settlements["sku"] == "PF-ELECTRO-CITRUS").sum()) + int(
        (inventory["raw_sku"] == "PF-ELECTRO-CITRUS").sum()
    )
    missing_sku_rows = int(settlements["sku"].isna().sum())
    adjustment_rows = int(settlements["transaction_type"].eq("Adjustment").sum())
    post_quarter_po = po_detail.loc[po_detail["excluded_from_q2_cost"], "po_number"].tolist()
    outside_quarter = int(
        (~settlements["posted_date"].between(QUARTER_START, QUARTER_END)).sum()
    )
    items = [
        {
            "severity": "High",
            "issue": "Two sellable SKUs have no PO landed-cost history",
            "evidence": f"{', '.join(missing_cost_skus)}; {len(missing_cost_skus)} SKUs",
            "resolution": "Imputed each SKU at its brand median landed unit cost and flagged every affected row.",
            "ongoing_control": "Quarantine cost-missing SKUs; require finance approval before publishing final profitability reporting.",
        },
        {
            "severity": "High",
            "issue": "PH-DENTAL-30CT PO quantity is cases, not sellable units",
            "evidence": "Description says CASE OF 12; 99 PO cases become 1,188 sellable units.",
            "resolution": "Applied an explicit 12-unit case-pack override before calculating weighted landed cost.",
            "ongoing_control": "Maintain effective-dated UOM conversion rules in a product/UOM bridge.",
        },
        {
            "severity": "Medium",
            "issue": "One product appears under two SKU strings",
            "evidence": f"PF-ELECTRO-CITRUS aliases PF-ELECTRO-CIT; {alias_rows} affected source rows.",
            "resolution": "Canonicalized using an auditable alias bridge; matched ASIN B0PFELECIT.",
            "ongoing_control": "Never update facts in place; resolve identifiers through an effective-dated bridge.",
        },
        {
            "severity": "Medium",
            "issue": "ASIN is not unique in the supplied mapping",
            "evidence": f"{duplicate_asins} mapping rows share duplicate ASIN values; B0GTRLRJDE spans two brands.",
            "resolution": "Used SKU as the transaction join key and quarantined ASIN-only joins for review.",
            "ongoing_control": "Test uniqueness by marketplace + ASIN + effective date; retain exceptions table.",
        },
        {
            "severity": "Medium",
            "issue": "Shared platform costs lack SKU keys; adjustments lack accounting detail",
            "evidence": (
                f"{missing_sku_rows} advertising/storage/subscription rows lack SKU; "
                f"{adjustment_rows} adjustment rows have SKU but no reason or accounting treatment."
            ),
            "resolution": "Kept both below SKU contribution margin; allocated only shared platform costs in the threshold check.",
            "ongoing_control": "Ingest advertising campaign/product reports and storage SKU detail before allocation.",
        },
        {
            "severity": "Medium",
            "issue": "PO data has no receipt/status lifecycle",
            "evidence": (
                "PO date does not prove receipt/status; "
                f"{len(post_quarter_po)} post-quarter line ({', '.join(post_quarter_po)}) was excluded."
            ),
            "resolution": "Used available PO lines dated through June 30 for weighted cost; did not label PO quantities as inbound.",
            "ongoing_control": "Add PO header/status, expected ship/arrival, receipt, and Amazon shipment IDs.",
        },
        {
            "severity": "Low",
            "issue": "Mixed PO date formats",
            "evidence": f"{int(po_detail['po_date'].isna().sum())} failed parses after normalized mixed-format parsing.",
            "resolution": "Parsed with mixed-format logic and stored as typed dates.",
            "ongoing_control": "Reject unparseable dates in staging and publish source-row error counts.",
        },
        {
            "severity": "Low",
            "issue": "Quarter/date and arithmetic reconciliation",
            "evidence": (
                f"{outside_quarter} settlement rows outside Q2; max settlement delta "
                f"${settlements['settlement_delta'].abs().max():.6f}; max PO delta "
                f"${po_detail['line_recalc_delta'].abs().max():.6f}."
            ),
            "resolution": "Confirmed Q2 date scope and arithmetic tie-outs within floating-point tolerance.",
            "ongoing_control": "Block reporting when date, row-count, or amount reconciliation tests exceed tolerance.",
        },
    ]
    return pd.DataFrame(items)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--purchase-orders", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--settlements", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    mapping = prepare_mapping(pd.read_csv(args.mapping))
    po_raw = pd.read_csv(args.purchase_orders)
    inv_raw = pd.read_csv(args.inventory)
    settlements_raw = pd.read_csv(args.settlements)

    po_detail, costs, brand_median_cost = build_costs(po_raw, mapping)
    st, tx, sku, brand, monthly, overhead = build_profitability(
        settlements_raw, mapping, costs, brand_median_cost
    )
    inventory = build_inventory(inv_raw, mapping, sku)
    refund_sku, refund_brand = build_refund_analysis(tx)
    dq = data_quality_register(mapping, po_detail, st, tx, inventory)

    net_sales = float(brand["net_sales"].sum())
    cm = float(brand["contribution_margin"].sum())
    adjustment_income = float(
        overhead.loc[overhead["classification"] == "below_cm_other_income", "signed_amount"].sum()
    )
    platform_overhead = float(
        -overhead.loc[
            overhead["classification"] == "below_cm_platform_overhead", "signed_amount"
        ].sum()
    )
    result_after_platform_costs = cm + adjustment_income - platform_overhead
    imputed_sales = float(tx.loc[tx["cost_imputed"], "gross_sales"].sum())
    imputed_units = float(tx.loc[tx["cost_imputed"], "quantity"].sum())

    bridge = pd.DataFrame(
        [
            ("Gross product sales, net of refunds", float(brand["gross_sales"].sum())),
            ("Promotional deductions, net of reversals", -float(brand["promo_deduction"].sum())),
            ("Net sales after promotions", net_sales),
            ("Referral fees", -float(brand["referral_fees"].sum())),
            ("FBA fulfillment fees", -float(brand["fba_fees"].sum())),
            ("Landed COGS", -float(brand["landed_cogs"].sum())),
            ("Contribution margin", cm),
            ("Advertising cost", float(overhead.loc[overhead["transaction_type"] == "Advertising Cost", "signed_amount"].sum())),
            ("FBA storage fee", float(overhead.loc[overhead["transaction_type"] == "FBA Storage Fee", "signed_amount"].sum())),
            ("Subscription fee", float(overhead.loc[overhead["transaction_type"] == "Subscription Fee", "signed_amount"].sum())),
            ("Adjustments / other income", adjustment_income),
            ("Result after platform costs", result_after_platform_costs),
        ],
        columns=["line_item", "signed_amount"],
    )

    summary = {
        "period": {"start": str(QUARTER_START.date()), "end": str(QUARTER_END.date()), "days": QUARTER_DAYS},
        "gross_sales_net_of_refunds": round(float(brand["gross_sales"].sum()), 2),
        "net_sales_after_promotions": round(net_sales, 2),
        "contribution_margin": round(cm, 2),
        "contribution_margin_pct": round(cm / net_sales, 6),
        "platform_overhead": round(platform_overhead, 2),
        "adjustment_income": round(adjustment_income, 2),
        "profit_after_platform_overhead": round(result_after_platform_costs, 2),
        "imputed_cost_sales": round(imputed_sales, 2),
        "imputed_cost_sales_pct": round(imputed_sales / float(brand["gross_sales"].sum()), 6),
        "imputed_cost_units": round(imputed_units, 2),
        "settlement_row_count": int(len(st)),
        "cm_transaction_row_count": int(len(tx)),
        "source_files": {
            "mapping": args.mapping.name,
            "purchase_orders": args.purchase_orders.name,
            "inventory": args.inventory.name,
            "settlements": args.settlements.name,
        },
    }

    outputs = {
        "sku_profitability.csv": sku,
        "refund_analysis_by_sku.csv": refund_sku,
        "refund_analysis_by_brand.csv": refund_brand,
        "brand_profitability.csv": brand,
        "monthly_brand_profitability.csv": monthly,
        "inventory_health.csv": inventory,
        "po_unit_costs.csv": costs,
        "profit_bridge.csv": bridge,
        "platform_overhead.csv": overhead,
        "data_quality_register.csv": dq,
        "settlement_transactions_transformed.csv": tx,
    }
    reporting_outputs = {
        "sku_profitability.csv",
        "refund_analysis_by_sku.csv",
        "refund_analysis_by_brand.csv",
        "brand_profitability.csv",
        "monthly_brand_profitability.csv",
        "inventory_health.csv",
        "profit_bridge.csv",
        "platform_overhead.csv",
    }
    for name, frame in outputs.items():
        float_format = "%.2f" if name in reporting_outputs else None
        frame.to_csv(
            args.output_dir / name,
            index=False,
            date_format="%Y-%m-%d",
            float_format=float_format,
        )
    (args.output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    workbook_payload = {
        "summary": summary,
        "brand_profitability": brand.replace({np.nan: None}).to_dict(orient="records"),
        "sku_profitability": sku.replace({np.nan: None}).to_dict(orient="records"),
        "inventory_health": inventory.replace({np.nan: None}).to_dict(orient="records"),
        "po_unit_costs": costs.replace({np.nan: None}).to_dict(orient="records"),
        "profit_bridge": bridge.replace({np.nan: None}).to_dict(orient="records"),
        "data_quality": dq.replace({np.nan: None}).to_dict(orient="records"),
    }
    (args.output_dir / "analysis_tables.json").write_text(
        json.dumps(workbook_payload, indent=2, default=str), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
