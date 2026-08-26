CREATE OR REPLACE TABLE `your_project.finance.mart_inventory_health_2026_06_30` AS
WITH resolved AS (
  SELECT i.*, b.canonical_sku
  FROM `your_project.finance.stg_inventory_snapshot` i
  LEFT JOIN `your_project.finance.bridge_product_identifier` b
    ON i.raw_sku = b.identifier_value AND b.identifier_type = 'SKU' AND b.is_current
), demand AS (
  SELECT canonical_sku, net_units / 91.0 AS daily_net_units,
         applied_unit_cost, contribution_margin_pct, cost_imputed
  FROM `your_project.finance.mart_sku_profitability_q2_2026`
)
SELECT
  r.snapshot_date,
  p.brand,
  r.canonical_sku,
  p.product_name,
  r.fulfillable,
  r.reserved,
  r.unfulfillable,
  r.inbound,
  d.daily_net_units,
  SAFE_DIVIDE(r.fulfillable, d.daily_net_units) AS fulfillable_days_cover,
  SAFE_DIVIDE(r.fulfillable + r.inbound, d.daily_net_units) AS incl_inbound_days_cover,
  SAFE_DIVIDE(r.unfulfillable, r.fulfillable + r.reserved + r.unfulfillable) AS unfulfillable_rate,
  r.fulfillable * d.applied_unit_cost AS fulfillable_inventory_value,
  r.inbound * d.applied_unit_cost AS inbound_inventory_value,
  CASE
    WHEN SAFE_DIVIDE(r.fulfillable, d.daily_net_units) < 60 THEN 'EXPEDITE / REORDER'
    WHEN SAFE_DIVIDE(r.fulfillable, d.daily_net_units) > 365 THEN 'SLOW-MOVER REVIEW'
    WHEN SAFE_DIVIDE(r.unfulfillable, r.fulfillable + r.reserved + r.unfulfillable) > 0.05 THEN 'QUALITY REVIEW'
    ELSE 'MONITOR'
  END AS inventory_action
FROM resolved r
LEFT JOIN `your_project.finance.dim_product` p USING (canonical_sku)
LEFT JOIN demand d USING (canonical_sku);

