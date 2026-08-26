# Deliverable 3 — first 90 days of finance automation

## Recommendation

Begin with the **efficient / cost-aware BigQuery path** unless leadership already has budget and operating support for managed ELT. Preserve the same Bronze → Silver → Gold contracts so ingestion can later move to the premium path without rebuilding dimensions, facts, tests, or reporting.

| Period | Automate first | Why this order | Tangible output |
|---|---|---|---|
| **Days 1–30: control the sources** | Inventory QuickBooks, REACH, Amazon, and Sheets feeds; schedule immutable raw loads; snapshot/diff schemas; establish product/SKU/ASIN/UOM bridges; add freshness, uniqueness, dedup, and reconciliation tests | Automation without source contracts scales errors. Identity and amount controls are prerequisites for a trusted P&L | Daily ingestion/control dashboard, drift alerts/publication gates, replayable history, owned exception queue |
| **Days 31–60: automate the management P&L** | Build settlement, landed-cost, inventory, advertising, and GL facts; publish brand/SKU CM; reconcile Amazon settlement activity to QuickBooks clearing accounts; replace copy/paste Sheets with governed outputs | This removes the highest-value recurring close work and makes profitability repeatable | Close-ready channel P&L, source drill-through, Amazon-to-QuickBooks reconciliation |
| **Days 61–90: turn history into action** | Add REACH PO lifecycle and receipts; inventory cover/aging/stockout alerts; campaign-to-SKU advertising; 13-week cash/inventory outlook; owner-based alerts and close SLAs | Inventory and forecast automation require reliable demand, cost, receipts, and accounting first | Inventory/action dashboard, replenishment exceptions, cash outlook |

## Two delivery paths

| Component | Efficient / cost-aware | Premium / managed |
|---|---|---|
| Ingestion | Scheduled Cloud Run jobs using Amazon SP-API, QuickBooks API, REACH API/SFTP/export, and governed Sheets inputs | Managed ELT for Amazon and QuickBooks; managed file/API connector or custom connector for REACH |
| Orchestration | Cloud Scheduler + Workflows; Dataform schedules | Managed connector scheduling + dbt Cloud jobs; Composer only for complex dependencies |
| Bronze | GCS immutable objects + append-only BigQuery raw tables | Managed source replicas in BigQuery with history/metadata |
| Silver | Dataform: typed staging, deduplication, identity bridge, core dimensions/facts, assertions | dbt Cloud: tested staging/core models, documentation, lineage, CI |
| Gold | BigQuery finance marts | BigQuery finance marts + governed semantic layer |
| Consumption | Connected Sheets and Looker Studio | Looker plus Connected Sheets |
| Monitoring | Dataform assertions, control tables, Cloud Logging/Monitoring | Managed observability plus dbt tests and source freshness |
| Tradeoff | Lower recurring software cost; higher connector maintenance | Faster implementation and lower maintenance; higher subscription and vendor dependence |

## Day-90 success measures

- At least 95% of scheduled feeds arrive and pass source controls.
- 99.5%+ of net sales has A-grade product and brand identity; all remaining exposure has an owner and SLA.
- Amazon activity reconciles to QuickBooks within an approved tolerance.
- Monthly channel P&L preparation time falls by at least 50%.
- Inventory exceptions use actual receipt/lifecycle data rather than treating open POs as inbound.

## Why not automate everything at once

The first 90 days should deliver a controlled close and actionable exceptions, not a large platform program. Advanced forecasting, enterprise MDM, real-time streaming, and broad self-service BI remain backlog items until source reliability and finance ownership are demonstrated.
