# Assumptions and limitations

## Assumptions

- April 1 through June 30, 2026 is treated as the quarter, using settlement posted date.
- Contribution margin includes only Order and Refund rows with a resolved SKU.
- Refunds retain the Amazon signs and reverse sales, promotions, referral fees, units, and landed COGS.
- FBA fees are used as reported. The supplied refund rows do not contain FBA fee reversals.
- Landed unit cost uses quarter-wide weighted PO cost divided by sellable units. Receipt-date or perpetual moving-average costing would require opening layers and receipt dates that were not supplied.
- `PH-DENTAL-30CT` PO cases are converted to sellable units at 12 units per case based on the description.
- `GT-LIP-BALM` and `PH-TOY-ROPE-L` have no PO cost history. Each uses its brand median landed unit cost as a temporary estimate and remains flagged.
- `PF-ELECTRO-CITRUS` is treated as a proposed alias of `PF-ELECTRO-CIT` based on the supplied product/ASIN mapping.
- Advertising, storage, subscription fees, and adjustments remain below SKU-level contribution margin because the settlement rows do not contain a reliable SKU allocation key.
- Inventory days cover uses quarter net units divided by 91 days as its demand rate and fulfillable units as on-hand inventory.
- Refund rate is refunded units divided by ordered units. Refund contribution impact is the absolute contribution margin reversed by Refund rows.

## Limitations

- SKU-less platform costs reduce the Amazon-level result but cannot support a defensible brand or SKU allocation from the supplied settlement file.
- The PO file does not show receipt, shipment, cancelation, or open-PO status.
- The inventory file is a June 30 snapshot rather than inventory-movement history.
- Refund reason codes were not supplied, so the analysis identifies financial exposure but cannot distinguish product quality, fulfillment, listing expectation, or customer-preference causes.
- Imputed costs and inventory signals should be confirmed before a posted financial result or purchasing decision.

No external operating or financial data is used in the profitability calculation.

## Landed COGS lineage

Landed cost originates in the supplied `purchase_orders_landed_cost.csv` file.

| Source column | Use |
|---|---|
| `sku` | Joins the PO cost to the canonical product |
| `qty` | Purchased quantity; converted to sellable units when a case-pack rule applies |
| `unit_cost` | Product cost per PO quantity unit |
| `freight_duty_alloc` | Freight and duty assigned to the PO line |
| `total_cost` | Product cost plus allocated freight and duty |

The calculation is:

`unit landed cost = sum(total_cost) / sum(sellable units)`

`landed COGS = signed settlement quantity × applied unit landed cost`

Refund rows have negative quantity and therefore reverse landed COGS. The generated [PO cost summary](../processed/po_unit_costs.csv) preserves purchased units, product cost, freight/duty, total landed cost, case pack, and resulting unit landed cost by SKU.
