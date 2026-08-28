# Amazon Q2 2026 profitability assessment

This README is the 20–25 minute presentation. Links provide calculation receipts and implementation detail.

| Deliverable | Primary evidence |
|---|---|
| **1. BigQuery data model** | [Model](docs/data_model.md) · [identity rules](docs/identity_resolution_and_confidence.md) · [drift/replay](docs/schema_drift_replay_and_validation.md) |
| **2. Profitability analysis** | [Workbook](deliverables/Amazon_Q2_2026_Profitability_Analysis.xlsx) · [brand results](processed/brand_profitability.csv) · [24 SKU results](processed/sku_profitability.csv) |
| **3. 90-day automation plan** | [Plan](docs/automation_90_day_plan.md) · [architecture](docs/architecture_options.md) |
| **Supporting files** | [Original inputs](Originals/) · [BigQuery SQL](sql/bigquery/) |

## 1. BigQuery model: confidence before perfection

**Method:** preserve raw evidence, resolve identity once, and expose only controlled reporting models.

![Trusted data foundation](assets/trusted-data-foundation.svg)

### How the supplied files become governed models

Each assessment file has one replayable landing and one controlled path into shared finance models.

![Supplied assessment files mapped to the proposed BigQuery model](assets/supplied-data-to-bigquery-model.svg)

Settlement and PO facts converge in profitability; the inventory snapshot remains an as-of operational fact.

Exact canonical SKU can identify a product; a prefix can suggest only its brand. Conflicts remain visible.

![Confidence-based identity resolution](assets/identity-confidence-ladder.svg)

**Publish:** high-confidence matches proceed, provisional matches warn, and conflicts quarantine with owner and dollar exposure.

## 2. Q2 profitability

`Contribution margin = net product sales after refunds/promotions − referral fees − FBA fulfillment − landed COGS`

**Leadership headline:** Q2 generated $51.2K of SKU-attributable contribution margin, but $50.6K of advertising consumed **98.7%** of it. After storage and subscription, the run-rate result was **($5.6K)** before corporate overhead.

| Q2 result | Amount |
|---|---:|
| Net sales after refunds and promotions | **$132,341.93** |
| Contribution margin before advertising | **$51,242.63** |
| Contribution margin rate | **38.7%** |
| Advertising expense | **($50,576.12)** |
| Advertising as % of contribution margin | **98.7%** |
| Contribution remaining after advertising | **$666.51** |
| FBA storage fees | **($6,119.25)** |
| Subscription fees | **($119.97)** |
| Run-rate result after platform costs | **($5,572.71)** |
| Reported result including $89.25 adjustment income | **($5,483.46)** |

Advertising did not exceed contribution margin: it consumed 98.7% of it. Only $666.51, or 0.5% of net sales, remained to cover storage, subscription, corporate overhead, and profit.

![Contribution margin and platform costs](assets/contribution-margin-and-platform-costs.svg)

![Contribution margin by brand](assets/brand-contribution-margin.svg)

### Transaction receipt

Order `114-1003986-4269335`, SKU `PH-BED-MED-GRY`:

| Step | Source | Amount |
|---|---|---:|
| Product sale | Settlement `product_sales` | $42.99 |
| Promotion | Settlement `promotional_rebates` | ($4.30) |
| Net product sales | Calculated | $38.69 |
| Referral fee | Settlement `selling_fees` | ($5.80) |
| FBA fulfillment | Settlement `fba_fees` | ($12.40) |
| Landed COGS | PO weighted landed cost | ($19.70) |
| **Contribution margin** | Calculated | **$0.79** |

Landed cost receipt: ($23,556.00 product + $2,048.80 freight/duty) ÷ 1,300 units = **$19.696 per unit**.

This receipt is intentionally an outlier: the dog bed is the lowest-margin **non-imputed** SKU. Its $12.40 FBA fee is 28.8% of the $42.99 selling price before COGS, supporting a reprice, packaging/dimensional-weight review, or FBM test.

[Settlement rows](processed/settlement_transactions_transformed.csv) · [PO costs](processed/po_unit_costs.csv) · [SKU results](processed/sku_profitability.csv)

### Data-quality decisions

| Issue found | Resolution used |
|---|---|
| Missing PO cost: `GT-LIP-BALM`, `PH-TOY-ROPE-L` | Used flagged brand-median cost; $3,040.90 net sales affected and ±25% cost moves total CM by ±$378 |
| `PH-DENTAL-30CT` ordered by case | Converted each case to 12 sellable units before unit-cost calculation |
| `PF-ELECTRO-CITRUS` alias | Mapped through an auditable alias to `PF-ELECTRO-CIT` |
| ASIN `B0GTRLRJDE` identifies two products | Joined by approved SKU and blocked ASIN-only matching |
| PO file includes one July 2 line | Excluded it from Q2 costing; used available PO records dated through June 30 |
| Shared platform costs lack SKU keys | Kept below reported SKU CM; adjustments remain separate because their accounting purpose is unknown |

[Full quality register](processed/data_quality_register.csv) · [assumptions and limitations](docs/assumptions_and_limitations.md)

### Net-sales allocation threshold check

SKU-less costs are allocated by net-sales share for direction—not reported SKU profit.

`Allocation share = SKU net sales ÷ $132,341.93`

`Allocated advertising = $50,576.12 × brand net sales share`

`Shared-cost load = ($50,576.12 + $6,119.25 + $119.97) ÷ $132,341.93 = 42.9%`

Every brand receives that same percentage. This is a breakeven threshold check—not cost attribution—and it cannot change the reported CM ranking. FBA fulfillment is already recorded by SKU and is not reallocated.

| Brand | Net sales | Reported CM | Advertising | Storage | Subscription | Run-rate threshold | Margin |
|---|---:|---:|---:|---:|---:|---:|---:|
| GlowTheory | $42,872.51 | $20,548.22 | ($16,384.27) | ($1,982.35) | ($38.87) | **$2,142.73** | **5.0%** |
| Peak Fuel | $55,656.70 | $22,027.05 | ($21,269.90) | ($2,573.46) | ($50.45) | **($1,866.76)** | **(3.4%)** |
| PawHaus | $33,812.72 | $8,667.36 | ($12,921.95) | ($1,563.44) | ($30.65) | **($5,848.68)** | **(17.3%)** |
| **Total** | **$132,341.93** | **$51,242.63** | **($50,576.12)** | **($6,119.25)** | **($119.97)** | **($5,572.71)** | **(4.2%)** |

Displayed allocated cents use residual rounding so every row and the total foot. Exact unrounded allocations remain in the linked scenario files.

![Reported contribution margin versus net-sales allocation threshold](assets/reported-vs-allocated-brand-result.svg)

The threshold excludes the nonrecurring $89.25 adjustment because its accounting purpose is unknown. The reported channel result is **($5,572.71) + $89.25 = ($5,483.46)**. Preferred production drivers are advertised-ASIN spend and SKU cubic-foot-days.

### Advertising guardrail sensitivity

With current CM, storage, and subscription held constant, Q2 had **$45,003.41** available for advertising before adjustment income.

`Maximum advertising = $51,242.63 CM − $6,119.25 storage − $119.97 subscription − target profit`

| Target post-platform margin | Maximum advertising | Change from Q2 spend |
|---:|---:|---:|
| Break-even | $45,003.41 | ($5,572.71) |
| 1% | $43,679.99 | ($6,896.13) |
| **5%** | **$38,386.31** | **($12,189.81)** |
| 8% | $34,416.06 | ($16,160.06) |

A 5% target creates a provisional **$38.4K** quarterly ad cap. Campaign/ASIN contribution data should determine where to reduce or reallocate spend; equivalent price, fee, or COGS improvements can also close the gap.

[Brand scenario](processed/allocated_profitability_scenario_by_brand.csv) · [SKU scenario](processed/allocated_profitability_scenario_by_sku.csv) · [script](analysis/allocate_shared_costs.py)

### Refund risk

`Refund rate = refunded units ÷ ordered units`

| Brand | Brand rate | Highest-risk SKU | Refunded / ordered | SKU rate | CM effect |
|---|---:|---|---:|---:|---:|
| GlowTheory | **4.9%** | `GT-MASK-CLAY` | 17 / 159 | **10.7%** | $143 reversed; 28.9% of remaining SKU CM |
| Peak Fuel | **2.8%** | `PF-WHEY-CHOC` | 14 / 411 | **3.4%** | $328 reversed |
| PawHaus | **2.7%** | `PH-BED-MED-GRY` | 8 / 122 | **6.6%** | $138 reversed; 47.2% of remaining SKU CM |

![Q2 unit refund rate by brand](assets/refund-rate-by-brand.svg)

These are posted-period rates, not order cohorts: Q2 refunds may relate to Q1 orders, while Q2 orders can refund in Q3. Refund-row CM is an optimistic view of total return economics: the original FBA charge remains in total SKU CM, while return processing and nonrecoverable inventory are unavailable.

### Selected SKU unit economics

| SKU | Order ASP | FBA / order unit | Landed cost / unit | CM / net unit | CM rate |
|---|---:|---:|---:|---:|---:|
| `GT-MASK-CLAY` | $14.99 | $3.85 | $4.60 | $3.49 | 23.8% |
| `PF-WHEY-CHOC` | $44.99 | $6.10 | $14.20 | $16.63 | 38.0% |
| `PH-BED-MED-GRY` | $42.99 | **$12.40** | $19.70 | **$2.56** | **6.1%** |

### Leadership findings and actions

1. **Acquisition economics erase portfolio margin.** The portfolio generates **38.7% CM before advertising**, but $50.6K of advertising consumes 98.7% of that CM and the channel loses $5.6K after storage and subscription. Use a provisional **$38.4K quarterly ad guardrail** for a 5% post-platform margin, or require an equivalent $12.2K contribution improvement.
2. **PawHaus needs an economic decision.** It has the lowest reported brand CM rate at **25.6%** and reaches **(17.3%)** under the proportional threshold check. The dog bed earns only 6.1% CM before advertising because FBA consumes 28.8% of price. Reprice, reduce dimensional weight, test FBM, or exit products that cannot clear a defined margin floor.
3. **Advertising attribution determines what to cut.** The supplied data shows advertising at **38.2% of net sales**, but not whether losses are broad or concentrated in a few ASINs. Ingest campaign and advertised-ASIN spend, then manage contribution after advertising—not ROAS alone.

**Validation next steps**

- Match returns to order cohorts and add reason, disposition, reimbursement, and processing-cost data.
- Replace the two imputed costs with approved costs and add receipt-layer inventory costing.
- Add historical inventory movements before making replenishment or stock-health decisions.

[Refund detail](processed/refund_analysis_by_sku.csv) · [assumptions](docs/assumptions_and_limitations.md) · [quality register](processed/data_quality_register.csv)

## 3. First 90 days

QuickBooks is the accounting ledger; REACH is the financial reporting system; Sheets hold governed manual inputs. BigQuery is the warehouse, and dbt transforms, tests, and documents models.

![Resilient BigQuery and dbt model flow](assets/resilient-dbt-model-flow.svg)

| Timing | Priority | Outcome |
|---|---|---|
| **Days 1–30: protect** | Catalog Amazon, QuickBooks, REACH, and Sheet feeds; document REACH report definitions, adjustments, lineage, and exports; retain raw history/run metadata; add drift, null, retry, and replay controls | Recoverable feeds and visible source changes |
| **Days 31–60: stabilize** | Build dbt Silver/Core models with tolerant parsing and approved rename aliases; add identity tests, Gold contracts, and QuickBooks-to-REACH reconciliation | Stable profitability reporting with drill-through |
| **Days 61–90: close gaps** | Add advertising-by-ASIN, storage detail, return reasons, and PO/receipt status; govern Sheet inputs; assign owners and test replay | Better SKU economics and an operating runbook |

**Drift rule:** Bronze retains changed payloads. Optional keys warn; missing required fields, null spikes, or failed financial tie-outs hold only affected Gold models. API outages still require retries and replay.

[Detailed plan](docs/automation_90_day_plan.md) · [model](docs/data_model.md) · [drift controls](docs/schema_drift_replay_and_validation.md)

## Key assumptions

- Refund signs reverse sales, promotions, fees, units, and COGS; FBA is not reversed.
- Refund rates use posted-period activity, not matched order cohorts.
- Shared costs remain below reported SKU CM; the net-sales view is a threshold check.
- Adjustment income is excluded from run-rate ad guardrails.
- Available PO records dated through June 30 set one weighted cost; receipt-layer COGS is unavailable.
- `PH-DENTAL-30CT` uses a 12-unit case pack.
- `GT-LIP-BALM` and `PH-TOY-ROPE-L` use flagged brand-median costs.
- `PF-ELECTRO-CITRUS` aliases `PF-ELECTRO-CIT`.
- Duplicate ASIN `B0GTRLRJDE` is blocked from ASIN-only joins.

## Reproduce

The supplied source files are preserved unchanged in [`Originals/`](Originals/).

```bash
pip install -r requirements.txt

python analysis/profitability_analysis.py \
  --mapping "Originals/sku_asin_brand_mapping.csv" \
  --purchase-orders "Originals/purchase_orders_landed_cost.csv" \
  --inventory "Originals/inventory_snapshot_2026-06-30.csv" \
  --settlements "Originals/amazon_settlements_apr-jun_2026.csv" \
  --output-dir processed

python analysis/identity_resolution_audit.py \
  --transactions processed/settlement_transactions_transformed.csv \
  --output-dir processed

python analysis/allocate_shared_costs.py
python analysis/build_repo_charts.py
```

Bash/zsh is shown; on PowerShell, run each Python command on one line.

## AI-use disclosure

OpenAI Codex 5.6 Sol assisted with documentation, pipeline-design examples, and illustrative SQL/Python. I reviewed the analysis and remain responsible for its conclusions. Production dbt/SQL would be authored and tested against the actual BigQuery schemas and business rules.

Claude Fable 5 provided an independent critique of the profitability interpretation, prompting clearer advertising guardrails, refund caveats, and sensitivity notes.
