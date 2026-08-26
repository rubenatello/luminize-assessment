# Assumptions, limitations, and AI use

## Assumptions I made

- I treated April 1 through June 30, 2026 as the quarter, using settlement posted date.
- Contribution margin includes only Order and Refund rows that have a SKU. Refunds retain the signs supplied by Amazon and reverse sales, promotions, referral fees, units, and landed COGS.
- I used FBA fees as reported. The supplied refund rows do not contain FBA fee reversals.
- I estimated landed unit cost using quarter-wide weighted PO cost divided by sellable units. A receipt-date or perpetual moving average would require opening inventory layers and receipt dates that were not provided.
- I converted `PH-DENTAL-30CT` PO cases to sellable units at 12 units per case based on the description.
- `GT-LIP-BALM` and `PH-TOY-ROPE-L` have no PO cost history. I used the median landed unit cost for each brand as a temporary estimate and flagged the affected rows.
- I treated `PF-ELECTRO-CITRUS` as an alias of `PF-ELECTRO-CIT` because the mapping data shows the same product/ASIN relationship.
- I kept advertising, storage, subscription fees, and adjustments below SKU-level contribution margin because the settlement rows do not contain a reliable SKU allocation key.
- Inventory days cover uses quarter net units divided by 91 days as the demand rate and fulfillable units as on-hand inventory.
- I show the inventory file's inbound quantity separately, but I do not treat PO quantities as inbound. The PO file has no status, shipment, or receipt fields.

These choices are appropriate for the assessment, but I would replace the imputed costs and inventory assumptions before using the output for a posted financial result or a purchasing decision.

## Where I used AI

I used AI to help profile the files, draft portions of the Python and SQL, and format the workbook, written response, and presentation. I reviewed the transformation logic, tied the outputs back to the supplied source totals, and kept the assumptions and imputed values visible in the workbook and documentation.

I did not use external operating or financial data in the profitability calculation.
