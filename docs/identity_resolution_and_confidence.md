# Identity resolution and confidence framework

## Objective

Every financial fact should carry stable foreign keys plus enough metadata to explain exactly how those keys were assigned. The system should maximize deterministic matches, preserve uncertainty, and prevent ambiguous identifiers from silently entering finance marts.

The key design choice is to score **product**, **brand**, and **ASIN attribute** confidence separately. A transaction can have a high-confidence product because its SKU is approved even when the source omits ASIN. Conversely, a recognizable brand prefix does not establish a product key.

## Keys and join scope

Facts store surrogate keys for stable history and efficient joins:

| Key | Target | Rule |
|---|---|---|
| `product_key` | `dim_product` | Assigned only by an approved deterministic rule or an explicitly monitored provisional ASIN rule |
| `brand_key` | `dim_brand` | Normally inherited from the resolved product; may be populated alone for brand-level exception reporting |
| `channel_key` | `dim_channel` | Source system + marketplace/account |
| `date_key` | `dim_date` | Transaction, snapshot, PO, or receipt date according to fact grain |
| `source_row_key` | raw/staging lineage | File/object ID + row hash; never discarded |

Identifiers are stored in `bridge_product_identifier` at this grain:

`identifier_type + normalized_identifier + marketplace/account scope + valid_from + valid_to`

The bridge also stores `resolution_method`, `rule_id`, `is_approved`, `resolution_status`, confidence scores, steward, approval timestamp, and source lineage. Effective dates prevent a corrected alias or reassigned identifier from rewriting history.

## Resolution precedence

1. **Exact canonical SKU — A/100.** Normalize case and whitespace only; do not remove meaningful punctuation unless the rule is versioned and tested.
2. **Approved SKU alias — A/95.** Exact match to a steward-approved alias with effective dates. Alias volume is monitored because growth can indicate upstream master-data drift.
3. **Unique scoped ASIN — B/85.** Use only when ASIN maps to one active product inside marketplace/account/date scope. Mark provisional and send to review if used for a finance fact.
4. **Brand evidence — C/60 or lower.** An approved source-brand normalization may identify brand; a SKU-prefix rule is weaker. Both can populate `brand_key` for exception reporting but cannot invent `product_key`.
5. **Conflict or missing evidence — F/0.** Preserve the row in quarantine with amount exposure, candidate matches, owner, and SLA.

Fuzzy product-name similarity and generative suggestions may rank candidates for a steward. They are never automatic finance joins.

## Attribute-specific confidence grades

### Product confidence

| Grade | Score | Evidence | Treatment |
|---|---:|---|---|
| A | 95–100 | Exact approved SKU or alias | Publish to finance marts |
| B | 80–94 | Unique scoped ASIN with no contradictory SKU | Provisional; publish only below threshold and review |
| C | 50–79 | Partial identifiers or human-unapproved rule | Exception reporting only |
| F | 0–49 | Missing, ambiguous, or contradictory | Quarantine |

### Brand confidence

| Grade | Score | Evidence | Treatment |
|---|---:|---|---|
| A | 100 | Brand inherited from approved product mapping | Publish |
| B | 85–95 | Normalized source brand consistent with product/ASIN | Publish with control |
| C | 60 | Versioned SKU-prefix inference, such as `GT`, `PF`, or `PH` | Brand-only reporting; review |
| D | 30 | Text inference or fuzzy candidate | Steward queue only |
| F | 0 | Missing or conflicting brand evidence | Quarantine |

### ASIN attribute confidence

| Grade | Score | Evidence | Treatment |
|---|---:|---|---|
| A | 100 | Source ASIN agrees with a unique approved SKU/product mapping | Publish and may be used as corroboration |
| B | 90 | ASIN is enriched from a resolved SKU and is unique in scope | Publish as an attribute, not source evidence |
| C | 70 | Source ASIN is unique but crosswalk approval is pending | Review queue |
| F | 0 | ASIN missing, duplicated, or contradictory | Do not use for joins |

Missing ASIN is not itself a failed product match. Store `asin_confidence_score = 0` or `asin_status = 'NOT_AVAILABLE'` while retaining the independently supported product score.

## Current assessment application

- All 4,604 order/refund rows contain a SKU and resolve to a product and brand.
- 4,552 rows resolve by exact canonical SKU; 52 resolve through approved alias `PF-ELECTRO-CITRUS -> PF-ELECTRO-CIT`.
- The settlement file supplies no ASIN. ASIN is therefore an enriched attribute, not source evidence.
- ASIN `B0GTRLRJDE` is assigned to both `GT-ROLLER-JADE` and `PH-BRUSH-DBL`. It affects 220 rows and $3,168.19 of net sales. Those facts remain correctly resolved by SKU, but the ASIN is graded F/0 and blocked from ASIN-only joins.
- The actual Peak Fuel SKU prefix is `PF`, not `PK`. Prefix rules must be reference data, not code assumptions.

## At-a-glance identity control panel

The production dashboard should show both row coverage and financial exposure:

1. Product resolution A/B/C/F distribution by row count and net sales.
2. Brand resolution A/B/C/F distribution by row count and net sales.
3. ASIN status: source-confirmed, enriched-unique, missing, or conflicting.
4. Unresolved and provisional net sales against the finance materiality threshold.
5. Top aliases by volume and quarter-over-quarter change.
6. Identifier collisions, first-seen date, age, owner, and SLA status.
7. Mapping freshness and percentage of facts resolved by each bridge version.

Recommended publication gates:

- **Block:** any unresolved/conflicted product identity above the agreed materiality threshold; any ASIN-only join using a conflicted ASIN; any many-to-many bridge result.
- **Warn:** provisional product matches exceed 0.5% of net sales; alias usage grows materially; brand-prefix inference is non-zero.
- **Pass:** at least 99.5% of net sales has A-grade product and brand resolution, with the remainder owned and immaterial.

## Exception workflow

Each exception record includes source row, raw identifiers, candidates, confidence by attribute, financial exposure, first/last seen, owner, status, decision, reviewer, and effective date. Approved resolutions create a new version in the identifier bridge; rejected candidates remain auditable. The pipeline reruns affected facts rather than editing published tables manually.

