-- BigQuery Standard SQL. Replace `your_project.finance` with the target dataset.
-- Raw tables are append-only and include _source_file, _loaded_at, and _row_hash.

CREATE OR REPLACE VIEW `your_project.finance.stg_product_mapping` AS
SELECT
  TRIM(sku) AS raw_sku,
  UPPER(TRIM(asin)) AS asin,
  TRIM(brand) AS brand,
  TRIM(product_name) AS product_name,
  TRIM(status) AS status,
  _source_file,
  _loaded_at,
  _row_hash
FROM `your_project.finance.raw_product_mapping`;

CREATE OR REPLACE VIEW `your_project.finance.stg_purchase_order_line` AS
SELECT
  TRIM(po_number) AS po_number,
  SAFE.PARSE_DATE('%Y-%m-%d', po_date) AS po_date_iso,
  COALESCE(
    SAFE.PARSE_DATE('%Y-%m-%d', po_date),
    SAFE.PARSE_DATE('%m/%d/%Y', po_date)
  ) AS po_date,
  TRIM(vendor) AS vendor,
  TRIM(sku) AS raw_sku,
  TRIM(description) AS description,
  SAFE_CAST(qty AS NUMERIC) AS ordered_qty,
  SAFE_CAST(unit_cost AS NUMERIC) AS unit_cost,
  SAFE_CAST(freight_duty_alloc AS NUMERIC) AS freight_duty_alloc,
  SAFE_CAST(total_cost AS NUMERIC) AS total_cost,
  _source_file,
  _loaded_at,
  _row_hash
FROM `your_project.finance.raw_purchase_order_line`;

CREATE OR REPLACE VIEW `your_project.finance.stg_marketplace_transaction` AS
SELECT
  TRIM(settlement_id) AS settlement_id,
  TRIM(transaction_type) AS transaction_type,
  NULLIF(TRIM(order_id), '') AS order_id,
  SAFE.PARSE_DATE('%Y-%m-%d', posted_date) AS posted_date,
  NULLIF(TRIM(sku), '') AS raw_sku,
  SAFE_CAST(quantity AS NUMERIC) AS quantity,
  SAFE_CAST(product_sales AS NUMERIC) AS product_sales,
  SAFE_CAST(shipping_credits AS NUMERIC) AS shipping_credits,
  SAFE_CAST(promotional_rebates AS NUMERIC) AS promotional_rebates,
  SAFE_CAST(selling_fees AS NUMERIC) AS selling_fees,
  SAFE_CAST(fba_fees AS NUMERIC) AS fba_fees,
  SAFE_CAST(other_transaction_fees AS NUMERIC) AS other_transaction_fees,
  SAFE_CAST(other AS NUMERIC) AS other,
  SAFE_CAST(total AS NUMERIC) AS total,
  _source_file,
  _loaded_at,
  _row_hash
FROM `your_project.finance.raw_marketplace_transaction`;

CREATE OR REPLACE VIEW `your_project.finance.stg_inventory_snapshot` AS
SELECT
  SAFE.PARSE_DATE('%Y-%m-%d', snapshot_date) AS snapshot_date,
  TRIM(sku) AS raw_sku,
  UPPER(TRIM(asin)) AS asin,
  SAFE_CAST(fulfillable AS INT64) AS fulfillable,
  SAFE_CAST(reserved AS INT64) AS reserved,
  SAFE_CAST(unfulfillable AS INT64) AS unfulfillable,
  SAFE_CAST(inbound AS INT64) AS inbound,
  _source_file,
  _loaded_at,
  _row_hash
FROM `your_project.finance.raw_inventory_snapshot`;

