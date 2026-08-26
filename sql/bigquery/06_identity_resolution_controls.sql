-- Identity quality mart and publication gates.
-- Assumes int_marketplace_transaction_resolved exposes the confidence fields
-- created in 02_core_dimensions.sql.

CREATE OR REPLACE VIEW `your_project.finance.mart_identity_resolution_quality` AS
WITH scoped AS (
  SELECT
    product_resolution_method,
    product_confidence_grade,
    product_confidence_score,
    brand_confidence_grade,
    brand_confidence_score,
    asin_confidence_grade,
    asin_confidence_score,
    net_sales
  FROM `your_project.finance.int_marketplace_transaction_resolved`
  WHERE transaction_type IN ('Order', 'Refund')
), totals AS (
  SELECT COUNT(*) AS total_rows, SUM(net_sales) AS total_net_sales FROM scoped
)
SELECT
  product_resolution_method,
  product_confidence_grade,
  product_confidence_score,
  brand_confidence_grade,
  brand_confidence_score,
  asin_confidence_grade,
  asin_confidence_score,
  COUNT(*) AS rows,
  SAFE_DIVIDE(COUNT(*), ANY_VALUE(total_rows)) AS row_pct,
  SUM(net_sales) AS net_sales,
  SAFE_DIVIDE(SUM(net_sales), ANY_VALUE(total_net_sales)) AS net_sales_pct
FROM scoped
CROSS JOIN totals
GROUP BY 1, 2, 3, 4, 5, 6, 7;

CREATE OR REPLACE VIEW `your_project.finance.mart_identity_exceptions` AS
SELECT
  _source_file,
  _row_hash,
  posted_date,
  raw_sku,
  raw_asin,
  product_resolution_method,
  product_confidence_grade,
  product_confidence_score,
  brand_confidence_grade,
  brand_confidence_score,
  asin_confidence_grade,
  asin_confidence_score,
  net_sales,
  CASE
    WHEN product_key IS NULL THEN 'UNRESOLVED_PRODUCT'
    WHEN product_confidence_score < 80 THEN 'LOW_PRODUCT_CONFIDENCE'
    WHEN asin_resolution_status = 'CONFLICT' THEN 'ASIN_CONFLICT'
    WHEN brand_confidence_score < 80 THEN 'LOW_BRAND_CONFIDENCE'
  END AS exception_type,
  CURRENT_DATE() AS observed_date
FROM `your_project.finance.int_marketplace_transaction_resolved`
WHERE product_key IS NULL
   OR product_confidence_score < 80
   OR asin_resolution_status = 'CONFLICT'
   OR brand_confidence_score < 80;

-- Publication gate. Production orchestration should fail if this returns a row.
WITH exposure AS (
  SELECT
    SUM(net_sales) AS total_net_sales,
    SUM(IF(product_confidence_grade = 'F', net_sales, 0)) AS unresolved_net_sales,
    SUM(IF(product_confidence_grade = 'B', net_sales, 0)) AS provisional_net_sales,
    COUNTIF(product_key IS NULL) AS unresolved_rows,
    COUNTIF(asin_resolution_status = 'CONFLICT' AND product_resolution_method = 'ASIN_EXACT')
      AS conflicted_asin_join_rows
  FROM `your_project.finance.int_marketplace_transaction_resolved`
  WHERE transaction_type IN ('Order', 'Refund')
)
SELECT *
FROM exposure
WHERE unresolved_rows > 0
   OR conflicted_asin_join_rows > 0
   OR SAFE_DIVIDE(ABS(unresolved_net_sales), ABS(total_net_sales)) > 0.001
   OR SAFE_DIVIDE(ABS(provisional_net_sales), ABS(total_net_sales)) > 0.005;

