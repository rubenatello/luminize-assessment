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
