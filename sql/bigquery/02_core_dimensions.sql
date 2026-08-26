-- Identifier bridge: add effective dates and source/approval metadata in production.
CREATE OR REPLACE TABLE `your_project.finance.bridge_product_identifier` AS
WITH supplied_mapping AS (
  SELECT raw_sku AS identifier_value, 'SKU' AS identifier_type, raw_sku AS canonical_sku,
         asin, brand, product_name, status, DATE '1900-01-01' AS valid_from,
         DATE '9999-12-31' AS valid_to, TRUE AS is_current, 'supplied_mapping' AS resolution_method
  FROM `your_project.finance.stg_product_mapping`
), explicit_aliases AS (
  SELECT 'PF-ELECTRO-CITRUS', 'SKU', 'PF-ELECTRO-CIT', 'B0PFELECIT',
         'Peak Fuel', 'Peak Fuel Electrolyte Powder Citrus 60srv', 'Active',
         DATE '1900-01-01', DATE '9999-12-31', TRUE, 'approved_alias'
)
SELECT * FROM supplied_mapping
UNION ALL
SELECT * FROM explicit_aliases;

CREATE OR REPLACE TABLE `your_project.finance.dim_product` AS
SELECT
  FARM_FINGERPRINT(canonical_sku) AS product_key,
  canonical_sku,
  ANY_VALUE(asin HAVING MAX is_current) AS asin,
  ANY_VALUE(brand HAVING MAX is_current) AS brand,
  ANY_VALUE(product_name HAVING MAX is_current) AS product_name,
  ANY_VALUE(status HAVING MAX is_current) AS status
FROM `your_project.finance.bridge_product_identifier`
GROUP BY canonical_sku;

CREATE OR REPLACE VIEW `your_project.finance.int_marketplace_transaction_resolved` AS
SELECT
  t.*,
  b.canonical_sku,
  p.product_key,
  p.brand,
  p.product_name,
  b.resolution_method
FROM `your_project.finance.stg_marketplace_transaction` t
LEFT JOIN `your_project.finance.bridge_product_identifier` b
  ON t.raw_sku = b.identifier_value
 AND b.identifier_type = 'SKU'
 AND t.posted_date BETWEEN b.valid_from AND b.valid_to
LEFT JOIN `your_project.finance.dim_product` p USING (canonical_sku);

CREATE OR REPLACE VIEW `your_project.finance.int_po_landed_unit_cost` AS
WITH normalized AS (
  SELECT
    po.*,
    b.canonical_sku,
    CASE WHEN b.canonical_sku = 'PH-DENTAL-30CT' THEN 12 ELSE 1 END AS case_pack,
    ordered_qty * CASE WHEN b.canonical_sku = 'PH-DENTAL-30CT' THEN 12 ELSE 1 END AS sellable_units
  FROM `your_project.finance.stg_purchase_order_line` po
  LEFT JOIN `your_project.finance.bridge_product_identifier` b
    ON po.raw_sku = b.identifier_value AND b.identifier_type = 'SKU' AND b.is_current
)
SELECT
  canonical_sku,
  SUM(sellable_units) AS purchased_units,
  SUM(total_cost) AS landed_cost_total,
  SAFE_DIVIDE(SUM(total_cost), SUM(sellable_units)) AS unit_landed_cost
FROM normalized
GROUP BY canonical_sku;

