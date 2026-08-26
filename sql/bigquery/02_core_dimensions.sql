-- Conformed product/brand dimensions and governed identifier bridge.
-- Replace the hard-coded marketplace/account and alias seed with governed
-- reference tables in production.

CREATE OR REPLACE TABLE `your_project.finance.dim_brand` AS
SELECT DISTINCT
  FARM_FINGERPRINT(UPPER(TRIM(brand))) AS brand_key,
  TRIM(brand) AS brand_name,
  TRUE AS is_active
FROM `your_project.finance.stg_product_mapping`
WHERE NULLIF(TRIM(brand), '') IS NOT NULL;

CREATE OR REPLACE TABLE `your_project.finance.dim_product` AS
SELECT
  FARM_FINGERPRINT(UPPER(TRIM(m.raw_sku))) AS product_key,
  UPPER(TRIM(m.raw_sku)) AS canonical_sku,
  UPPER(TRIM(m.asin)) AS asin,
  b.brand_key,
  m.brand,
  m.product_name,
  m.status,
  DATE '1900-01-01' AS valid_from,
  DATE '9999-12-31' AS valid_to,
  TRUE AS is_current
FROM `your_project.finance.stg_product_mapping` m
LEFT JOIN `your_project.finance.dim_brand` b
  ON UPPER(TRIM(m.brand)) = UPPER(TRIM(b.brand_name))
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY UPPER(TRIM(m.raw_sku))
  ORDER BY m._loaded_at DESC, m._row_hash DESC
) = 1;

CREATE OR REPLACE TABLE `your_project.finance.bridge_product_identifier` AS
WITH asin_counts AS (
  SELECT
    UPPER(TRIM(asin)) AS asin,
    COUNT(DISTINCT UPPER(TRIM(raw_sku))) AS product_count
  FROM `your_project.finance.stg_product_mapping`
  WHERE NULLIF(TRIM(asin), '') IS NOT NULL
  GROUP BY 1
), products AS (
  SELECT
    p.*,
    COALESCE(a.product_count, 0) AS asin_product_count,
    IF(a.product_count = 1, 'UNIQUE', 'CONFLICT') AS asin_resolution_status
  FROM `your_project.finance.dim_product` p
  LEFT JOIN asin_counts a USING (asin)
  WHERE p.is_current
), sku_identifiers AS (
  SELECT
    'SKU' AS identifier_type,
    canonical_sku AS identifier_value,
    canonical_sku AS identifier_value_normalized,
    'US' AS marketplace_code,
    'DEFAULT_ACCOUNT' AS account_scope,
    product_key,
    canonical_sku,
    brand_key,
    'SKU_EXACT' AS resolution_method,
    'R1_EXACT_CANONICAL_SKU' AS rule_id,
    1 AS resolution_priority,
    100 AS product_confidence_score,
    100 AS brand_confidence_score,
    IF(asin_product_count = 1, 90, 0) AS asin_confidence_score,
    asin_resolution_status,
    'APPROVED' AS resolution_status,
    TRUE AS is_approved,
    valid_from,
    valid_to,
    is_current
  FROM products
), approved_aliases AS (
  -- Assessment-specific evidence. Production aliases belong in a governed
  -- effective-dated table with approver and ticket metadata.
  SELECT 'PF-ELECTRO-CITRUS' AS alias_sku, 'PF-ELECTRO-CIT' AS canonical_sku
), alias_identifiers AS (
  SELECT
    'SKU' AS identifier_type,
    a.alias_sku AS identifier_value,
    UPPER(TRIM(a.alias_sku)) AS identifier_value_normalized,
    'US' AS marketplace_code,
    'DEFAULT_ACCOUNT' AS account_scope,
    p.product_key,
    p.canonical_sku,
    p.brand_key,
    'SKU_ALIAS' AS resolution_method,
    'R2_APPROVED_SKU_ALIAS' AS rule_id,
    2 AS resolution_priority,
    95 AS product_confidence_score,
    100 AS brand_confidence_score,
    IF(p.asin_product_count = 1, 90, 0) AS asin_confidence_score,
    p.asin_resolution_status,
    'APPROVED' AS resolution_status,
    TRUE AS is_approved,
    p.valid_from,
    p.valid_to,
    p.is_current
  FROM approved_aliases a
  JOIN products p USING (canonical_sku)
), asin_identifiers AS (
  SELECT
    'ASIN' AS identifier_type,
    asin AS identifier_value,
    asin AS identifier_value_normalized,
    'US' AS marketplace_code,
    'DEFAULT_ACCOUNT' AS account_scope,
    product_key,
    canonical_sku,
    brand_key,
    IF(asin_product_count = 1, 'ASIN_EXACT', 'ASIN_CONFLICT') AS resolution_method,
    IF(asin_product_count = 1, 'R3_UNIQUE_SCOPED_ASIN', 'R5_CONFLICT') AS rule_id,
    3 AS resolution_priority,
    IF(asin_product_count = 1, 85, 0) AS product_confidence_score,
    IF(asin_product_count = 1, 90, 0) AS brand_confidence_score,
    IF(asin_product_count = 1, 100, 0) AS asin_confidence_score,
    asin_resolution_status,
    IF(asin_product_count = 1, 'PROVISIONAL', 'CONFLICT') AS resolution_status,
    asin_product_count = 1 AS is_approved,
    valid_from,
    valid_to,
    is_current
  FROM products
  WHERE NULLIF(asin, '') IS NOT NULL
), all_identifiers AS (
  SELECT * FROM sku_identifiers
  UNION ALL SELECT * FROM alias_identifiers
  UNION ALL SELECT * FROM asin_identifiers
)
SELECT
  FARM_FINGERPRINT(CONCAT(
    identifier_type, '|', identifier_value_normalized, '|',
    marketplace_code, '|', account_scope, '|', canonical_sku
  )) AS identifier_key,
  *
FROM all_identifiers;

CREATE OR REPLACE VIEW `your_project.finance.int_marketplace_transaction_resolved` AS
WITH sku_candidates AS (
  SELECT t._row_hash, b.*
  FROM `your_project.finance.stg_marketplace_transaction` t
  JOIN `your_project.finance.bridge_product_identifier` b
    ON b.identifier_type = 'SKU'
   AND UPPER(TRIM(t.raw_sku)) = b.identifier_value_normalized
   AND t.posted_date BETWEEN b.valid_from AND b.valid_to
   AND b.is_current
   AND b.is_approved
  WHERE t.raw_sku IS NOT NULL
), asin_candidates AS (
  SELECT t._row_hash, b.*
  FROM `your_project.finance.stg_marketplace_transaction` t
  JOIN `your_project.finance.bridge_product_identifier` b
    ON b.identifier_type = 'ASIN'
   AND UPPER(TRIM(t.raw_asin)) = b.identifier_value_normalized
   AND t.posted_date BETWEEN b.valid_from AND b.valid_to
   AND b.is_current
   AND b.is_approved
  WHERE t.raw_sku IS NULL
    AND t.raw_asin IS NOT NULL
), candidates AS (
  SELECT * FROM sku_candidates
  UNION ALL
  SELECT * FROM asin_candidates
), best_match AS (
  SELECT *
  FROM candidates
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY _row_hash
    ORDER BY resolution_priority, product_confidence_score DESC, identifier_key
  ) = 1
)
SELECT
  t.*,
  b.product_key,
  b.canonical_sku,
  p.brand_key,
  p.brand,
  p.product_name,
  p.asin,
  COALESCE(b.resolution_method, 'UNRESOLVED') AS product_resolution_method,
  COALESCE(b.rule_id, 'R5_MISSING_OR_CONFLICT') AS match_rule_id,
  COALESCE(b.product_confidence_score, 0) AS product_confidence_score,
  CASE
    WHEN COALESCE(b.product_confidence_score, 0) >= 95 THEN 'A'
    WHEN COALESCE(b.product_confidence_score, 0) >= 80 THEN 'B'
    WHEN COALESCE(b.product_confidence_score, 0) >= 50 THEN 'C'
    ELSE 'F'
  END AS product_confidence_grade,
  COALESCE(b.brand_confidence_score, 0) AS brand_confidence_score,
  CASE
    WHEN COALESCE(b.brand_confidence_score, 0) >= 95 THEN 'A'
    WHEN COALESCE(b.brand_confidence_score, 0) >= 80 THEN 'B'
    WHEN COALESCE(b.brand_confidence_score, 0) >= 50 THEN 'C'
    ELSE 'F'
  END AS brand_confidence_grade,
  COALESCE(b.asin_confidence_score, 0) AS asin_confidence_score,
  CASE
    WHEN COALESCE(b.asin_confidence_score, 0) >= 95 THEN 'A'
    WHEN COALESCE(b.asin_confidence_score, 0) >= 80 THEN 'B'
    WHEN COALESCE(b.asin_confidence_score, 0) >= 50 THEN 'C'
    ELSE 'F'
  END AS asin_confidence_grade,
  COALESCE(b.asin_resolution_status, 'NOT_AVAILABLE') AS asin_resolution_status,
  b.resolution_status,
  b.identifier_key,
  t.product_sales + t.promotional_rebates AS net_sales,
  COALESCE(b.product_confidence_score, 0) < 95
    OR COALESCE(b.brand_confidence_score, 0) < 80
    OR COALESCE(b.asin_resolution_status, 'NOT_AVAILABLE') = 'CONFLICT'
      AS identity_needs_review
FROM `your_project.finance.stg_marketplace_transaction` t
LEFT JOIN best_match b USING (_row_hash)
LEFT JOIN `your_project.finance.dim_product` p USING (product_key);

CREATE OR REPLACE VIEW `your_project.finance.int_po_landed_unit_cost` AS
WITH normalized AS (
  SELECT
    po.*,
    b.canonical_sku,
    CASE WHEN b.canonical_sku = 'PH-DENTAL-30CT' THEN 12 ELSE 1 END AS case_pack,
    ordered_qty * CASE WHEN b.canonical_sku = 'PH-DENTAL-30CT' THEN 12 ELSE 1 END
      AS sellable_units
  FROM `your_project.finance.stg_purchase_order_line` po
  LEFT JOIN `your_project.finance.bridge_product_identifier` b
    ON UPPER(TRIM(po.raw_sku)) = b.identifier_value_normalized
   AND b.identifier_type = 'SKU'
   AND b.is_current
   AND b.is_approved
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY po._row_hash
    ORDER BY b.resolution_priority, b.product_confidence_score DESC
  ) = 1
)
SELECT
  canonical_sku,
  SUM(sellable_units) AS purchased_units,
  SUM(total_cost) AS landed_cost_total,
  SAFE_DIVIDE(SUM(total_cost), SUM(sellable_units)) AS unit_landed_cost
FROM normalized
GROUP BY canonical_sku;
