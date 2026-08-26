# How I would match SKU, ASIN, and brand

The files do not all contain the same identifiers which can be difficult. I would avoid building separate join logic in every report. Instead, I would resolve the source identifier once, store the selected product and brand keys on the fact, and retain the rule that produced the match.

## Matching order

| Priority | Evidence | What I would assign | Confidence | Use in reporting |
|---:|---|---|---:|---|
| 1 | Exact approved SKU | Product and brand | A / 100 | Use normally |
| 2 | Approved SKU alias | Product and brand | A / 95 | Use and monitor alias volume |
| 3 | ASIN maps to one active product in the marketplace and period | Provisional product and brand | B / 85 | Use only within an agreed threshold and review |
| 4 | Approved brand field or SKU prefix | Brand only | C / 60 | Brand-level exception reporting only |
| 5 | Missing or conflicting identifiers | No forced match | F / 0 | Hold in the exception table |

I would not use fuzzy text matching to post a product key. It could suggest a possible match for review, but someone should approve the mapping before it affects finance reporting.

## Why I separate the scores

Product, brand, and ASIN are related but not the same question.

- If an exact SKU is approved but ASIN is missing, the product match can still be A-grade.
- If a prefix says `GT`, `PF`, or `PH`, I may know the likely brand without knowing the exact product.
- If one ASIN is attached to two SKUs, I can still use a valid source SKU while refusing to use the ASIN as a join.

I would therefore store `product_match_method`, `product_confidence`, `brand_confidence`, and `asin_status` separately.

## Identifier mapping table

I would keep a versioned `bridge_product_identifier` with this grain:

`identifier type + normalized value + marketplace/account + valid-from date + valid-to date`

It would also include the canonical product key, match method, approval status, reviewer, approval date, source, and rule version. The effective dates matter because correcting a mapping today should not silently rewrite a closed historical period.

## What I found in this assessment

- All 4,604 order/refund rows have a SKU and resolve to a product and brand.
- 4,552 rows use the canonical SKU.
- 52 rows use the approved alias `PF-ELECTRO-CITRUS → PF-ELECTRO-CIT`.
- The settlement file has no ASIN, so any ASIN shown later is an attribute added from the product mapping, not source evidence from the settlement row.
- ASIN `B0GTRLRJDE` is attached to both `GT-ROLLER-JADE` and `PH-BRUSH-DBL`. It affects 220 rows and $3,168.19 of net sales. The SKU still resolves those transactions, but the ASIN should not be used by itself.
- The Peak Fuel prefix in the files is `PF`, not `PK`.

The generated [coverage file](../processed/identity_resolution_coverage.csv) and [exception file](../processed/identity_resolution_exceptions.csv) show these results.

