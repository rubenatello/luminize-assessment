-- CM1 keeps only SKU-attributable Order and Refund economics.
-- Missing costs are imputed at brand median and remain explicitly flagged.

CREATE OR REPLACE TABLE `your_project.finance.mart_sku_profitability_q2_2026` AS
WITH brand_cost_median AS (
  SELECT p.brand, APPROX_QUANTILES(c.unit_landed_cost, 2)[OFFSET(1)] AS brand_median_unit_cost
  FROM `your_project.finance.int_po_landed_unit_cost` c
  JOIN `your_project.finance.dim_product` p USING (canonical_sku)
  GROUP BY p.brand
), scoped AS (
  SELECT
    t.brand,
    t.canonical_sku,
    t.product_name,
    t.quantity,
    t.product_sales,
    -t.promotional_rebates AS promo_deduction,
    -t.selling_fees AS referral_fees,
    -t.fba_fees AS fba_fees,
    c.unit_landed_cost,
    m.brand_median_unit_cost,
    c.unit_landed_cost IS NULL AS cost_imputed
  FROM `your_project.finance.int_marketplace_transaction_resolved` t
  LEFT JOIN `your_project.finance.int_po_landed_unit_cost` c USING (canonical_sku)
  LEFT JOIN brand_cost_median m USING (brand)
  WHERE t.transaction_type IN ('Order', 'Refund')
    AND t.posted_date BETWEEN DATE '2026-04-01' AND DATE '2026-06-30'
    AND t.canonical_sku IS NOT NULL
), calculated AS (
  SELECT
    *,
    product_sales - promo_deduction AS net_sales,
    quantity * COALESCE(unit_landed_cost, brand_median_unit_cost) AS landed_cogs
  FROM scoped
)
SELECT
  brand,
  canonical_sku,
  ANY_VALUE(product_name) AS product_name,
  SUM(product_sales) AS gross_sales,
  SUM(promo_deduction) AS promo_deduction,
  SUM(net_sales) AS net_sales,
  SUM(referral_fees) AS referral_fees,
  SUM(fba_fees) AS fba_fees,
  SUM(quantity) AS net_units,
  ANY_VALUE(COALESCE(unit_landed_cost, brand_median_unit_cost)) AS applied_unit_cost,
  LOGICAL_OR(cost_imputed) AS cost_imputed,
  SUM(landed_cogs) AS landed_cogs,
  SUM(net_sales - referral_fees - fba_fees - landed_cogs) AS contribution_margin,
  SAFE_DIVIDE(
    SUM(net_sales - referral_fees - fba_fees - landed_cogs),
    SUM(net_sales)
  ) AS contribution_margin_pct
FROM calculated
GROUP BY brand, canonical_sku;

CREATE OR REPLACE VIEW `your_project.finance.mart_brand_profitability_q2_2026` AS
SELECT
  brand,
  SUM(gross_sales) AS gross_sales,
  SUM(promo_deduction) AS promo_deduction,
  SUM(net_sales) AS net_sales,
  SUM(referral_fees) AS referral_fees,
  SUM(fba_fees) AS fba_fees,
  SUM(net_units) AS net_units,
  SUM(landed_cogs) AS landed_cogs,
  SUM(contribution_margin) AS contribution_margin,
  SAFE_DIVIDE(SUM(contribution_margin), SUM(net_sales)) AS contribution_margin_pct,
  COUNTIF(cost_imputed) AS imputed_skus
FROM `your_project.finance.mart_sku_profitability_q2_2026`
GROUP BY brand;

