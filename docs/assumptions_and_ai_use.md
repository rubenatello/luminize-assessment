# Assumptions, limitations, and AI-use disclosure

## Profitability assumptions

- Quarter scope is April 1 through June 30, 2026, based on settlement posted date.
- CM1 includes only `Order` and `Refund` rows with a SKU. Product sales, promotional rebates, selling fees, and quantities retain their source signs; displayed deductions are positive for readability.
- Refunds reverse sales, promotions, referral fees, units, and landed COGS. This assumes returned units are economically recoverable because disposition data is absent. Leadership should add a return-disposition feed and a damaged-return reserve if material.
- FBA fees are used as reported; refund rows contain no FBA fee reversal in the supplied data.
- Landed unit cost is quarter-wide weighted average PO landed cost: total PO cost divided by sellable units. It is not a perpetual/receipt-date moving average because opening inventory layers and receiving dates were not provided.
- `PH-DENTAL-30CT` is converted from PO cases to sellable units at 12 units per case, based on the description.
- Missing PO costs for `GT-LIP-BALM` and `PH-TOY-ROPE-L` are imputed using the median landed unit cost of their respective brands and flagged. Replace these assumptions before final financial reporting.
- `PF-ELECTRO-CITRUS` is an alias of `PF-ELECTRO-CIT`, based on matching ASIN and product identity.
- Advertising, storage, subscription, and adjustment rows are shown below CM1 because the supplied settlement data does not provide a defensible SKU allocation key.
- Inventory days cover uses quarter net units / 91 days as the demand rate and fulfillable units as the on-hand numerator. Inbound is shown as a separate forward-looking scenario, not treated as received inventory.
- PO quantities are not labeled as inbound because the PO extract lacks lifecycle/status and receipt information.

## AI-use disclosure

AI was used to accelerate data profiling, draft reproducible transformation code, propose the dimensional model, and format the workbook/document/deck. All calculations were independently reconciled to the supplied source files using explicit arithmetic checks, and every material assumption or imputation is surfaced in the data-quality register. No external factual data was introduced into the profitability calculation.

