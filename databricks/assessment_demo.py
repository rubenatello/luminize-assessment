# Databricks notebook source
# MAGIC %md
# MAGIC # Amazon Q2 2026 profitability demo
# MAGIC This notebook mirrors the production model: Bronze raw files, Silver typed/resolved facts, and Gold finance marts. Configure the four widget paths, then run all.

# COMMAND ----------
dbutils.widgets.text("mapping_path", "/Volumes/finance/assessment/raw/sku_asin_brand_mapping.csv")
dbutils.widgets.text("po_path", "/Volumes/finance/assessment/raw/purchase_orders_landed_cost.csv")
dbutils.widgets.text("inventory_path", "/Volumes/finance/assessment/raw/inventory_snapshot_2026-06-30.csv")
dbutils.widgets.text("settlements_path", "/Volumes/finance/assessment/raw/amazon_settlements_apr-jun_2026.csv")

# COMMAND ----------
from pyspark.sql import functions as F

mapping = spark.read.option("header", True).option("inferSchema", True).csv(dbutils.widgets.get("mapping_path"))
po = spark.read.option("header", True).option("inferSchema", True).csv(dbutils.widgets.get("po_path"))
inventory = spark.read.option("header", True).option("inferSchema", True).csv(dbutils.widgets.get("inventory_path"))
settlements = spark.read.option("header", True).option("inferSchema", True).csv(dbutils.widgets.get("settlements_path"))

for name, frame in {"mapping": mapping, "po": po, "inventory": inventory, "settlements": settlements}.items():
    frame.createOrReplaceTempView(f"bronze_{name}")

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMP VIEW silver_identifier_bridge AS
# MAGIC SELECT sku AS raw_sku, sku AS canonical_sku, asin, brand, `product-name` AS product_name, 'mapping' AS method
# MAGIC FROM bronze_mapping
# MAGIC UNION ALL
# MAGIC SELECT 'PF-ELECTRO-CITRUS', 'PF-ELECTRO-CIT', 'B0PFELECIT', 'Peak Fuel',
# MAGIC        'Peak Fuel Electrolyte Powder Citrus 60srv', 'approved_alias';

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMP VIEW silver_po_cost AS
# MAGIC WITH normalized AS (
# MAGIC   SELECT b.canonical_sku,
# MAGIC          CAST(p.qty AS DOUBLE) * CASE WHEN b.canonical_sku='PH-DENTAL-30CT' THEN 12 ELSE 1 END AS sellable_units,
# MAGIC          CAST(p.`total-cost` AS DOUBLE) AS total_cost
# MAGIC   FROM bronze_po p LEFT JOIN silver_identifier_bridge b ON p.sku=b.raw_sku
# MAGIC )
# MAGIC SELECT canonical_sku, SUM(total_cost)/SUM(sellable_units) AS unit_landed_cost
# MAGIC FROM normalized GROUP BY canonical_sku;

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMP VIEW gold_sku_profitability AS
# MAGIC WITH resolved AS (
# MAGIC   SELECT s.*, b.canonical_sku, b.brand, b.product_name, c.unit_landed_cost
# MAGIC   FROM bronze_settlements s
# MAGIC   LEFT JOIN silver_identifier_bridge b ON s.sku=b.raw_sku
# MAGIC   LEFT JOIN silver_po_cost c ON b.canonical_sku=c.canonical_sku
# MAGIC   WHERE s.`transaction-type` IN ('Order','Refund')
# MAGIC     AND TO_DATE(s.`posted-date`) BETWEEN DATE'2026-04-01' AND DATE'2026-06-30'
# MAGIC ), medians AS (
# MAGIC   SELECT brand, percentile_approx(unit_landed_cost, 0.5) AS brand_median_cost
# MAGIC   FROM resolved WHERE unit_landed_cost IS NOT NULL GROUP BY brand
# MAGIC )
# MAGIC SELECT r.brand, r.canonical_sku, MAX(r.product_name) AS product_name,
# MAGIC        SUM(CAST(r.`product-sales` AS DOUBLE)) AS gross_sales,
# MAGIC        SUM(-CAST(r.`promotional-rebates` AS DOUBLE)) AS promo_deduction,
# MAGIC        SUM(CAST(r.`product-sales` AS DOUBLE)+CAST(r.`promotional-rebates` AS DOUBLE)) AS net_sales,
# MAGIC        SUM(-CAST(r.`selling-fees` AS DOUBLE)) AS referral_fees,
# MAGIC        SUM(-CAST(r.`fba-fees` AS DOUBLE)) AS fba_fees,
# MAGIC        SUM(CAST(r.quantity AS DOUBLE)) AS net_units,
# MAGIC        MAX(COALESCE(r.unit_landed_cost,m.brand_median_cost)) AS applied_unit_cost,
# MAGIC        MAX(r.unit_landed_cost IS NULL) AS cost_imputed,
# MAGIC        SUM(CAST(r.quantity AS DOUBLE)*COALESCE(r.unit_landed_cost,m.brand_median_cost)) AS landed_cogs,
# MAGIC        SUM(CAST(r.`product-sales` AS DOUBLE)+CAST(r.`promotional-rebates` AS DOUBLE)
# MAGIC            +CAST(r.`selling-fees` AS DOUBLE)+CAST(r.`fba-fees` AS DOUBLE)
# MAGIC            -CAST(r.quantity AS DOUBLE)*COALESCE(r.unit_landed_cost,m.brand_median_cost)) AS contribution_margin
# MAGIC FROM resolved r LEFT JOIN medians m USING (brand)
# MAGIC GROUP BY r.brand, r.canonical_sku;

# COMMAND ----------
display(spark.sql("""
SELECT brand,
       ROUND(SUM(net_sales),2) AS net_sales,
       ROUND(SUM(contribution_margin),2) AS contribution_margin,
       ROUND(SUM(contribution_margin)/SUM(net_sales),4) AS cm_pct,
       SUM(CASE WHEN cost_imputed THEN 1 ELSE 0 END) AS imputed_skus
FROM gold_sku_profitability
GROUP BY brand
ORDER BY contribution_margin DESC
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC **Demo guidance:** show the brand table, drill into the two imputed SKUs, then open the data-quality checks. The point is governed traceability—not the notebook UI itself.

