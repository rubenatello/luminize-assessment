-- BigQuery control-plane objects for schema drift, replay, and deduplication.
-- Replace `project_id` before deployment.

CREATE TABLE IF NOT EXISTS `project_id.control.pipeline_run` (
  pipeline_run_id STRING NOT NULL,
  source_system STRING NOT NULL,
  source_object STRING NOT NULL,
  source_uri STRING,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  status STRING NOT NULL,
  source_row_count INT64,
  bronze_row_count INT64,
  silver_row_count INT64,
  payload_hash STRING,
  schema_hash STRING,
  contract_version STRING,
  code_version STRING,
  error_message STRING
) PARTITION BY DATE(started_at)
  CLUSTER BY source_system, source_object, status;

CREATE TABLE IF NOT EXISTS `project_id.control.schema_contract` (
  source_system STRING NOT NULL,
  source_object STRING NOT NULL,
  contract_version STRING NOT NULL,
  field_path STRING NOT NULL,
  expected_data_type STRING NOT NULL,
  expected_mode STRING,
  is_required BOOL NOT NULL,
  accepted_aliases ARRAY<STRING>,
  effective_from TIMESTAMP NOT NULL,
  effective_to TIMESTAMP,
  approved_by STRING,
  approved_at TIMESTAMP
) CLUSTER BY source_system, source_object, contract_version;

CREATE TABLE IF NOT EXISTS `project_id.control.schema_snapshot_header` (
  schema_snapshot_id STRING NOT NULL,
  pipeline_run_id STRING NOT NULL,
  source_system STRING NOT NULL,
  source_object STRING NOT NULL,
  observed_at TIMESTAMP NOT NULL,
  schema_hash STRING NOT NULL,
  api_or_report_version STRING,
  observed_field_count INT64
) PARTITION BY DATE(observed_at)
  CLUSTER BY source_system, source_object;

CREATE TABLE IF NOT EXISTS `project_id.control.schema_snapshot_field` (
  schema_snapshot_id STRING NOT NULL,
  field_path STRING NOT NULL,
  data_type STRING NOT NULL,
  mode STRING,
  ordinal_position INT64
) CLUSTER BY schema_snapshot_id, field_path;

CREATE TABLE IF NOT EXISTS `project_id.control.schema_drift_event` (
  drift_event_id STRING NOT NULL,
  pipeline_run_id STRING NOT NULL,
  source_system STRING NOT NULL,
  source_object STRING NOT NULL,
  field_path STRING,
  change_type STRING NOT NULL,
  prior_value STRING,
  current_value STRING,
  severity STRING NOT NULL,
  publish_action STRING NOT NULL,
  detected_at TIMESTAMP NOT NULL,
  owner STRING,
  resolution_status STRING NOT NULL,
  resolution_note STRING
) PARTITION BY DATE(detected_at)
  CLUSTER BY source_system, source_object, severity, resolution_status;

CREATE TABLE IF NOT EXISTS `project_id.control.dedup_audit` (
  pipeline_run_id STRING NOT NULL,
  model_name STRING NOT NULL,
  rule_version STRING NOT NULL,
  raw_rows INT64 NOT NULL,
  published_rows INT64 NOT NULL,
  replay_duplicates INT64 NOT NULL,
  potential_business_duplicates INT64 NOT NULL,
  affected_amount NUMERIC,
  audited_at TIMESTAMP NOT NULL
) PARTITION BY DATE(audited_at)
  CLUSTER BY model_name;

-- Run after the raw table is loaded. API JSON field paths should be flattened
-- into the same snapshot tables upstream.
DECLARE v_run_id STRING DEFAULT @pipeline_run_id;
DECLARE v_snapshot_id STRING DEFAULT GENERATE_UUID();

INSERT INTO `project_id.control.schema_snapshot_field`
  (schema_snapshot_id, field_path, data_type, mode, ordinal_position)
SELECT
  v_snapshot_id,
  column_name,
  data_type,
  IF(is_nullable = 'YES', 'NULLABLE', 'REQUIRED'),
  ordinal_position
FROM `project_id.raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'amazon_settlements';

INSERT INTO `project_id.control.schema_snapshot_header`
  (schema_snapshot_id, pipeline_run_id, source_system, source_object,
   observed_at, schema_hash, observed_field_count)
SELECT
  v_snapshot_id,
  v_run_id,
  'amazon_selling_partner',
  'settlements',
  CURRENT_TIMESTAMP(),
  TO_HEX(SHA256(STRING_AGG(
    CONCAT(field_path, ':', data_type, ':', COALESCE(mode, '')),
    '|' ORDER BY ordinal_position))),
  COUNT(*)
FROM `project_id.control.schema_snapshot_field`
WHERE schema_snapshot_id = v_snapshot_id;

INSERT INTO `project_id.control.schema_drift_event`
  (drift_event_id, pipeline_run_id, source_system, source_object, field_path,
   change_type, prior_value, current_value, severity, publish_action,
   detected_at, owner, resolution_status)
WITH contract AS (
  SELECT *
  FROM `project_id.control.schema_contract`
  WHERE source_system = 'amazon_selling_partner'
    AND source_object = 'settlements'
    AND CURRENT_TIMESTAMP() >= effective_from
    AND (effective_to IS NULL OR CURRENT_TIMESTAMP() < effective_to)
), observed AS (
  SELECT *
  FROM `project_id.control.schema_snapshot_field`
  WHERE schema_snapshot_id = v_snapshot_id
), diff AS (
  SELECT
    COALESCE(c.field_path, o.field_path) AS field_path,
    CASE
      WHEN c.field_path IS NULL THEN 'ADDED_FIELD'
      WHEN o.field_path IS NULL THEN 'REMOVED_FIELD'
      WHEN c.expected_data_type != o.data_type THEN 'TYPE_CHANGE'
      WHEN COALESCE(c.expected_mode, '') != COALESCE(o.mode, '') THEN 'MODE_CHANGE'
    END AS change_type,
    CONCAT(c.expected_data_type, '/', COALESCE(c.expected_mode, '')) AS prior_value,
    CONCAT(o.data_type, '/', COALESCE(o.mode, '')) AS current_value,
    c.is_required
  FROM contract c
  FULL OUTER JOIN observed o USING (field_path)
)
SELECT
  GENERATE_UUID(), v_run_id, 'amazon_selling_partner', 'settlements', field_path,
  change_type, prior_value, current_value,
  CASE
    WHEN change_type = 'ADDED_FIELD' THEN 'WARN'
    WHEN change_type = 'REMOVED_FIELD' AND NOT COALESCE(is_required, FALSE) THEN 'WARN'
    ELSE 'ERROR'
  END,
  CASE
    WHEN change_type = 'ADDED_FIELD' THEN 'PRESERVE_BRONZE_AND_REVIEW'
    WHEN change_type = 'REMOVED_FIELD' AND NOT COALESCE(is_required, FALSE)
      THEN 'PRESERVE_BRONZE_AND_REVIEW'
    ELSE 'BLOCK_SILVER_GOLD'
  END,
  CURRENT_TIMESTAMP(), 'finance_data', 'OPEN'
FROM diff
WHERE change_type IS NOT NULL;

-- Publication gate: proceed only when this returns zero.
SELECT COUNT(*) AS blocking_drift_events
FROM `project_id.control.schema_drift_event`
WHERE pipeline_run_id = v_run_id
  AND publish_action = 'BLOCK_SILVER_GOLD'
  AND resolution_status = 'OPEN';

-- Dedup contract:
-- 1) Bronze remains append-only evidence; never SELECT DISTINCT.
-- 2) Build `_source_record_key` from report/file ID + row number or API event ID.
--    A replay MERGE matches this key.
-- 3) Identical business content with different source keys remains published and
--    is flagged, because it may represent legitimate separate transactions.

-- Optional month-end recovery point; generate the identifier in orchestration.
-- CREATE SNAPSHOT TABLE `project_id.snapshots.fct_profitability_2026_06_30`
-- CLONE `project_id.mart.fct_profitability`;
