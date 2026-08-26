-- Each query should return zero rows (or a documented tolerated exception).

-- Settlement components must reconcile to total.
SELECT _source_file, _row_hash,
       product_sales + shipping_credits + promotional_rebates + selling_fees
       + fba_fees + other_transaction_fees + other - total AS delta
FROM `your_project.finance.stg_marketplace_transaction`
WHERE ABS(product_sales + shipping_credits + promotional_rebates + selling_fees
          + fba_fees + other_transaction_fees + other - total) > 0.01;

-- Every sold SKU must resolve to exactly one canonical SKU.
SELECT raw_sku, COUNT(DISTINCT canonical_sku) AS canonical_count
FROM `your_project.finance.int_marketplace_transaction_resolved`
WHERE transaction_type IN ('Order', 'Refund')
GROUP BY raw_sku
HAVING canonical_count != 1;

-- No finance fact may publish with F-grade product or brand identity.
SELECT _source_file, _row_hash, raw_sku, raw_asin, net_sales,
       product_confidence_grade, brand_confidence_grade
FROM `your_project.finance.int_marketplace_transaction_resolved`
WHERE transaction_type IN ('Order', 'Refund')
  AND (product_confidence_grade = 'F' OR brand_confidence_grade = 'F');

-- One source row must never have multiple approved candidates at the same priority.
SELECT
  t._row_hash,
  b.resolution_priority,
  COUNT(DISTINCT b.product_key) AS candidate_products
FROM `your_project.finance.stg_marketplace_transaction` t
JOIN `your_project.finance.bridge_product_identifier` b
  ON (
       (b.identifier_type = 'SKU'
        AND UPPER(TRIM(t.raw_sku)) = b.identifier_value_normalized)
    OR (b.identifier_type = 'ASIN'
        AND UPPER(TRIM(t.raw_asin)) = b.identifier_value_normalized)
  )
 AND t.posted_date BETWEEN b.valid_from AND b.valid_to
 AND b.is_current
 AND b.is_approved
GROUP BY 1, 2
HAVING candidate_products > 1;

-- Surface missing cost rather than silently dropping margin.
SELECT canonical_sku, brand, net_sales
FROM `your_project.finance.mart_sku_profitability_q2_2026`
WHERE cost_imputed;

-- ASIN collisions require marketplace/effective-date review.
SELECT identifier_value_normalized AS asin,
       marketplace_code,
       account_scope,
       COUNT(DISTINCT canonical_sku) AS sku_count
FROM `your_project.finance.bridge_product_identifier`
WHERE identifier_type = 'ASIN' AND is_current
GROUP BY 1, 2, 3
HAVING sku_count > 1;

-- Prefix inference is allowed for a brand-only exception, never product identity.
SELECT *
FROM `your_project.finance.int_marketplace_transaction_resolved`
WHERE product_resolution_method = 'BRAND_PREFIX'
  AND product_key IS NOT NULL;

-- Warning threshold: provisional product matches may not exceed 0.5% of net sales.
SELECT
  SAFE_DIVIDE(
    SUM(IF(product_confidence_grade = 'B', ABS(net_sales), 0)),
    SUM(ABS(net_sales))
  ) AS provisional_sales_pct
FROM `your_project.finance.int_marketplace_transaction_resolved`
WHERE transaction_type IN ('Order', 'Refund')
HAVING provisional_sales_pct > 0.005;

-- PO arithmetic must reconcile.
SELECT po_number, raw_sku,
       ordered_qty * unit_cost + freight_duty_alloc - total_cost AS delta
FROM `your_project.finance.stg_purchase_order_line`
WHERE ABS(ordered_qty * unit_cost + freight_duty_alloc - total_cost) > 0.01;
