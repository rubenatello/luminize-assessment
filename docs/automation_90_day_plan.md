# Deliverable 3: what I would automate in the first 90 days

My recommendation is to start with the cost-aware BigQuery option and solve the source-control problems before adding more reporting. If leadership already has budget for managed Amazon and QuickBooks connectors, those can be substituted without changing the finance model.

## Proposed order

| Timing | What I would do | Why I would do it then | Expected result |
|---|---|---|---|
| **Days 1–30** | Document the Amazon, QuickBooks, REACH, and Google Sheets feeds; schedule raw loads; save source and schema history; add product/SKU/ASIN/UOM mappings; test dates, totals, required columns, and duplicate behavior | A faster report is not useful if a source change or bad mapping can alter it without warning | Repeatable loads, schema-change alerts, source-to-target documentation, and an exception list |
| **Days 31–60** | Build the settlement, landed-cost, inventory, advertising, and GL facts; calculate contribution margin by brand and SKU; reconcile Amazon activity to QuickBooks; replace copy-and-paste reporting | This addresses the recurring close work and gives finance one repeatable channel P&L | Brand/SKU profitability, source drill-through, and Amazon-to-QuickBooks reconciliation |
| **Days 61–90** | Add REACH PO lifecycle and receipts, inventory cover and aging alerts, campaign/SKU advertising data, and a 13-week cash and inventory outlook | Inventory and forecast outputs are more useful after demand, receipts, cost, and accounting history are reliable | Inventory exceptions, replenishment actions, advertising decisions, and a short-term cash view |

## Cost-aware versus managed

| Component | Cost-aware starting point | Managed alternative |
|---|---|---|
| Ingestion | Cloud Scheduler/Run jobs for the APIs and file exports | Managed Amazon and QuickBooks connectors; managed or custom REACH connector |
| Transformations | Dataform in BigQuery | dbt Cloud |
| Raw history | Cloud Storage plus append-only BigQuery tables | Connector-managed source history in BigQuery |
| Reporting | Connected Sheets and Looker Studio | Looker and Connected Sheets |
| Monitoring | BigQuery control tables, Dataform assertions, and Cloud Monitoring | Managed data observability plus dbt tests |
| Main tradeoff | Lower cost, more connector ownership | Faster setup and less maintenance, higher recurring cost |

## How I would measure progress

By day 90, I would expect:

- At least 95% of scheduled feeds to arrive and pass source checks.
- At least 99.5% of net sales to resolve to an approved product and brand, with the remainder visible and assigned for review.
- Amazon activity to reconcile to QuickBooks within an agreed tolerance.
- Monthly channel-P&L preparation time to fall by at least 50%.
- Inventory reporting to use actual PO status and receipt data rather than assuming every open PO is inbound.

I would not make real-time streaming, a large master-data program, or advanced forecasting part of the first 90 days. Those can be revisited after the daily loads and month-end reconciliation are dependable.
