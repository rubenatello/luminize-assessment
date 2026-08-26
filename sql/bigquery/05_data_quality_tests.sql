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

-- Surface missing cost rather than silently dropping margin.
SELECT canonical_sku, brand, net_sales
FROM `your_project.finance.mart_sku_profitability_q2_2026`
WHERE cost_imputed;

-- ASIN collisions require marketplace/effective-date review.
SELECT asin, COUNT(DISTINCT canonical_sku) AS sku_count
FROM `your_project.finance.bridge_product_identifier`
WHERE asin IS NOT NULL AND is_current
GROUP BY asin
HAVING sku_count > 1;

-- PO arithmetic must reconcile.
SELECT po_number, raw_sku,
       ordered_qty * unit_cost + freight_duty_alloc - total_cost AS delta
FROM `your_project.finance.stg_purchase_order_line`
WHERE ABS(ordered_qty * unit_cost + freight_duty_alloc - total_cost) > 0.01;

