# How I approached the assessment

I treated this as three related questions rather than a platform build.

## 1. What can I support from the files provided?

I first profiled the four files, checked their grains and identifiers, and reconciled the numerical fields. That step determined which conclusions I could support and which would require more data.

- The settlement file supports SKU-level sales, promotions, referral fees, FBA fees, refunds, and other platform charges.
- The mapping file provides the approved SKU, ASIN, and brand relationship.
- The PO file supports a weighted landed-cost estimate. It does not provide PO status, receipts, or shipment lifecycle.
- The inventory file is a point-in-time snapshot as of June 30. It does not provide historical inventory movements.

## 2. How would I organize the data?

I would preserve each source exactly as received, then create typed staging tables, shared dimensions and facts, and finance reporting tables. The reporting layer would hold one definition of contribution margin by SKU and brand.

The most important modeling decision is not the name of the layer. It is resolving product identity once and carrying the resulting key into the facts. I would use exact SKU first, followed by an approved alias and then a unique ASIN. A prefix can help identify the brand, but it should not create a product match.

I would also record how each match was made. That makes it possible to show leadership what percentage of sales is based on an exact mapping versus an assumption or unresolved exception.

## 3. How did I calculate profitability?

I used the assignment's contribution-margin definition:

`net product sales after refunds - promotions - referral fees - FBA fees - landed COGS`

I kept advertising, storage, subscription fees, and adjustments below SKU-level contribution margin because the source does not provide a reliable allocation key. This avoids making one SKU look better or worse based on an arbitrary allocation.

Where cost was missing, I used a clearly flagged temporary estimate rather than dropping the sales or assigning zero cost.

## 4. What would I automate first?

My first priority would be making the source data reliable and repeatable. That includes saving the raw API response or file, detecting schema changes, keeping a run log, validating totals, and maintaining the SKU/ASIN/UOM mappings.

Once those controls are working, I would automate the management P&L and QuickBooks reconciliation. Inventory and forecasting come after that because they need dependable PO, receipt, cost, and demand history.
