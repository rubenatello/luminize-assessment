# Amazon Q2 2026 profitability assessment

This repository contains my response to the three parts of the assessment: a proposed BigQuery data model, a Q2 Amazon profitability analysis, and a 90-day automation plan.

I kept the raw CSV files out of the public repository. The calculation outputs, checks, assumptions, SQL, and Python are included so the work can still be reviewed.

## Start here

| What I would present | File |
|---|---|
| Leadership presentation | [PPTX](deliverables/Amazon_Q2_2026_Leadership_Presentation.pptx) |
| Profitability analysis and supporting schedules | [XLSX](deliverables/Amazon_Q2_2026_Profitability_Analysis.xlsx) |
| Written assessment | [DOCX](deliverables/Amazon_Q2_2026_Assessment_Brief.docx) |
| Short explanation of my approach | [Assessment approach](docs/assessment_approach.md) |

## How I approached the assignment

### 1. Data model

I would land each source in BigQuery without changing the raw record, then build typed staging tables, shared dimensions and facts, and finally the reporting tables used by finance. I used Bronze, Silver, and Gold labels in the diagrams because they make the layers easy to discuss, but the important part is the separation of raw data, transformation logic, and reporting definitions.

The main join issue is product identity. My proposed order is:

1. Exact approved SKU.
2. Approved SKU alias.
3. ASIN only when it maps to one product in the relevant marketplace and period.
4. SKU prefix for brand reporting only.
5. Leave the product unresolved when the evidence conflicts.

I score product, brand, and ASIN confidence separately. A missing ASIN should not lower product confidence when the SKU is already an approved match.

Supporting files: [data model](docs/data_model.md), [identifier rules](docs/identity_resolution_and_confidence.md), [schema-change controls](docs/schema_drift_replay_and_validation.md), and [BigQuery SQL](sql/bigquery/).

### 2. Profitability analysis

I calculated contribution margin as product sales net of refunds, less promotions, referral fees, FBA fees, and landed COGS.

| Q2 result | Amount |
|---|---:|
| Net sales after refunds and promotions | **$132,341.93** |
| SKU-attributable contribution margin | **$51,242.63** |
| Contribution margin rate | **38.7%** |
| Result after SKU-less platform costs and adjustments | **($5,483.46)** |

The last line is shown separately because advertising, storage, subscription fees, and adjustments do not have a reliable SKU allocation key in the supplied settlement file. I did not force those costs across products.

![Contribution margin and platform costs](assets/contribution-margin-and-platform-costs.svg)

![Contribution margin by brand](assets/brand-contribution-margin.svg)

Two SKUs did not have PO cost history. I used each brand's median landed unit cost as a temporary estimate and flagged every affected row. The workbook shows the brand and SKU results, assumptions, data-quality issues, inventory view, and reconciliation checks.

### 3. First 90 days

I would start with the lower-cost Google Cloud option unless the team wants to pay for managed connectors immediately.

- **Days 1–30:** automate source delivery, preserve raw history, add schema-change alerts, establish product and UOM mappings, and reconcile the source totals.
- **Days 31–60:** automate the Amazon management P&L and the Amazon-to-QuickBooks reconciliation.
- **Days 61–90:** add REACH PO/receipt activity, inventory exceptions, SKU-level advertising, and a short-term cash and inventory outlook.

I included both a [cost-aware and managed option](docs/architecture_options.md) because the model should not depend on which connector vendor is selected.

## Important data observations

- The settlement file has SKU but no ASIN. SKU is therefore the primary transaction join.
- The actual Peak Fuel prefix is `PF`, not `PK`.
- `PF-ELECTRO-CITRUS` resolves to `PF-ELECTRO-CIT` through an approved alias based on the mapping data.
- ASIN `B0GTRLRJDE` is assigned to two different SKUs. I did not use that ASIN as a join key.
- The PO file supports landed-cost calculations, but it does not establish whether inventory is open, shipped, received, or inbound to Amazon.
- The inventory file is a 6/30 snapshot. I use it for days-cover and exception analysis, not as a transaction history.

## Schema changes and duplicate handling

Amazon can change an API or report without the finance team being ready for it. The proposed load records the observed columns and a schema hash on every run, compares them with an approved contract, and writes any differences to a drift log.

- A new optional field creates a warning and is retained in raw data.
- A missing or renamed required field, duplicate column, or type change stops the reporting-table refresh.
- Raw data is not deduplicated away.
- A replay of the same source report is handled by a source-record key.
- Rows with the same business values but different source keys remain in the data and are flagged for review.

The example contract and audit can be run locally:

```powershell
python analysis/schema_contract_audit.py `
  "<path>/amazon_settlements_apr-jun_2026.csv" `
  contracts/amazon_settlements.schema.json
```

## Repository guide

```text
analysis/        Python used for the calculations and audits
contracts/       Expected source schemas
databricks/      Optional Databricks demonstration
deliverables/    Workbook, written response, and presentation
docs/            Design notes, assumptions, and automation plan
processed/       Generated analysis outputs and exception reports
sql/bigquery/    Proposed BigQuery tables, transformations, and tests
```

## Reproduce the analysis

```powershell
python analysis/profitability_analysis.py `
  --mapping "<path>/sku_asin_brand_mapping.csv" `
  --purchase-orders "<path>/purchase_orders_landed_cost.csv" `
  --inventory "<path>/inventory_snapshot_2026-06-30.csv" `
  --settlements "<path>/amazon_settlements_apr-jun_2026.csv" `
  --output-dir processed

python analysis/identity_resolution_audit.py `
  --transactions processed/settlement_transactions_transformed.csv `
  --output-dir processed

python analysis/build_repo_charts.py
```

Python 3.11+, pandas, and NumPy are required.

## AI use

I used AI to help profile the files, draft portions of the Python/SQL, and format the deliverables. I reviewed the logic, reconciled the outputs to the supplied files, and documented the assumptions and exceptions. More detail is in [assumptions and AI use](docs/assumptions_and_ai_use.md).
