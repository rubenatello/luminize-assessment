# First 90 days: finance automation proposal

## Prioritization principle

Automate the financial close and decision-critical facts before adding sophisticated dashboards. Each phase creates a controlled dataset that the next phase can trust.

### Days 1-30: establish the control plane

- Inventory every recurring QuickBooks, REACH, Amazon, and Google Sheets report; assign owner, cadence, grain, and reconciliation target.
- Stand up scheduled raw ingestion into BigQuery with immutable files, load timestamps, source-row hashes, and backfill capability.
- Build governed product, brand, vendor, UOM, and identifier mappings. Add an alias workflow and cost-missing exception queue.
- Automate daily source freshness, schema, row-count, duplicate, and amount-reconciliation tests.
- Deliverable: a daily source-control dashboard and a weekly exception review with finance.

**Why first:** automation without source controls scales errors. This phase removes manual downloading and creates trust.

### Days 31-60: automate the management P&L

- Build marketplace transaction, landed-cost, inventory snapshot, advertising, and GL facts.
- Publish daily/monthly brand and SKU CM with drill-through to source transactions.
- Reconcile Amazon cash activity and fees to QuickBooks clearing accounts; produce a close-ready exception list.
- Replace recurring cut-and-paste Sheets with Connected Sheets or governed extracts from BigQuery.
- Deliverable: automated channel P&L and settlement-to-GL reconciliation with sign-off workflow.

**Why second:** this attacks the highest-value recurring finance work and makes profitability decisions repeatable.

### Days 61-90: automate inventory and forward-looking actions

- Add PO lifecycle events from REACH: approved, sent, confirmed, produced, shipped, received, canceled, and Amazon inbound shipment IDs.
- Build inventory days cover, inbound ETA, stockout risk, excess/aging, and cash-at-risk alerts by SKU.
- Add campaign/SKU advertising detail to support attributable CM2 and budget pacing.
- Introduce owner-based alerts, monthly forecast refreshes, and a documented close calendar with SLAs.
- Deliverable: inventory/action dashboard and a 13-week cash/inventory outlook.

**Why third:** inventory recommendations require reliable demand, cost, receipt, and lifecycle data. This phase turns the foundation into operating decisions.

## Success measures

- 95%+ automated source delivery and test pass rate by day 30.
- Marketplace-to-QuickBooks reconciliation within a documented tolerance by day 60.
- 100% sold-SKU identity coverage and 98%+ landed-cost coverage by day 60.
- Close/report preparation time reduced by at least 50% by day 90.
- Every material exception has an owner, aging, and resolution status.

