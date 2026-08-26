# Amazon Q2 2026 Profitability Assessment

This is a GitHub-ready, reproducible submission package. The same dimensional model can be implemented in BigQuery or Databricks; the included analysis is generated locally from the four supplied CSV files.

## Executive result

- CM1 is defined as product sales net of refunds, less promotional deductions, referral fees, FBA fulfillment fees, and landed COGS.
- SKU-attributable CM1 is **$51.2K**, or **38.7% of net sales after promotions**.
- Advertising, storage, and subscription charges do not contain SKU keys. They are kept below CM1 rather than force-allocated. Including those items and two adjustments produces an estimated **$5.5K loss after platform overhead**.
- Two SKUs lack PO cost history. Their landed unit costs are imputed using the median landed cost for their brands and clearly flagged; together they represent about 2.3% of gross product sales.

## Presentation-ready deliverables

- [Profitability analysis workbook](deliverables/Amazon_Q2_2026_Profitability_Analysis.xlsx)
- [Assessment brief](deliverables/Amazon_Q2_2026_Assessment_Brief.docx)
- [Leadership presentation](deliverables/Amazon_Q2_2026_Leadership_Presentation.pptx)

## Repository map

```text
analysis/        Reproducible Python transformation and calculations
databricks/      Databricks notebook source showing the lakehouse implementation
deliverables/    Verified workbook, written brief, and leadership presentation
docs/            Data model, automation proposal, assumptions, and AI-use note
processed/       Generated analysis tables and data-quality register
sql/bigquery/    BigQuery staging, core, mart, and quality-control SQL
```

The four raw assessment CSV files are intentionally excluded from the public repository. The `processed/` folder contains the generated tables needed to review the calculations and findings without publishing the source extracts.

## Run locally

```powershell
python analysis/profitability_analysis.py `
  --mapping "<path>/sku_asin_brand_mapping.csv" `
  --purchase-orders "<path>/purchase_orders_landed_cost.csv" `
  --inventory "<path>/inventory_snapshot_2026-06-30.csv" `
  --settlements "<path>/amazon_settlements_apr-jun_2026.csv" `
  --output-dir processed
```

Dependencies: Python 3.11+, pandas, and NumPy.

## BigQuery vs. Databricks recommendation

For a finance team already using Google Sheets and seeking a pragmatic single source of truth, **BigQuery + dbt/Dataform + Looker Studio/Connected Sheets** is the faster first production choice. It has lower operational overhead and a natural path into finance-owned reporting. Databricks is still useful as a polished demo or if the company already has a lakehouse, streaming, ML, or large multi-channel data-engineering roadmap.

The submission can therefore be shown in two ways:

1. GitHub: code quality, lineage, tests, assumptions, and reproducibility.
2. BigQuery or Databricks: live tables/views and filterable brand/SKU profitability.

Avoid making platform choice the centerpiece of the interview. Lead with reconciled economics and controls; use the repo and notebook as evidence that the approach scales.
