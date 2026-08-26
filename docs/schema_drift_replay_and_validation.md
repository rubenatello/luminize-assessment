# Schema drift, validation, deduplication, and replay controls

## Control objective

An upstream API or report change should create an auditable event before it becomes a finance-reporting surprise. Every ingestion run records the source schema, data fingerprint, row counts, and validation results. Bronze accepts and preserves evidence; Silver and Gold publish only through explicit contracts.

## Ingestion sequence

~~~mermaid
flowchart LR
    A[Amazon API / report<br/>QuickBooks / REACH / Sheet] --> B[Land immutable payload<br/>with run + source metadata]
    B --> C[Extract field paths<br/>names, types, nullability]
    C --> D[Compare with<br/>last approved contract]
    D --> E{Drift severity}
    E -- Added optional field --> W[Warn: preserve in Bronze<br/>exclude from curated model]
    E -- Removed/renamed/type change --> F[Fail Silver publish<br/>quarantine + alert owner]
    E -- No material change --> V[Validate rows, keys,<br/>amounts, and freshness]
    V --> L[Idempotent Bronze load]
    L --> S[Deterministic Silver merge]
    S --> G[Gold finance marts]
    W --> V
    F --> R[Contract review<br/>mapping/version update]
    R --> V
~~~

## Schema registry and automated diff

Maintain these control tables:

| Table | Grain | Key fields |
|---|---|---|
| schema_contract | One approved field version | source, endpoint/report, field path, expected type, required flag, accepted aliases, effective dates, owner |
| schema_snapshot_header | One source schema per run | run ID, source, endpoint/report, API/report version, extraction time, schema hash |
| schema_snapshot_field | One observed field per snapshot | snapshot ID, field path, type, mode/nullability, ordinal position |
| schema_drift_event | One detected difference | added/removed/type/mode/order, prior/current values, severity, owner, status, first seen |
| pipeline_run | One ingestion attempt | start/end, source object/report ID, status, row count, payload hash, schema hash, code version |

Recommended severity:

- **INFO:** column order changed but name-based parsing is unaffected.
- **WARN:** new optional field. Preserve it in Bronze and notify the owner; do not automatically expose it in Silver/Gold.
- **ERROR:** required field removed, renamed without an approved alias, type or repeated/nested mode changed, duplicate column names, or key semantics changed. Block the curated publish.
- **CRITICAL:** the change creates a financial reconciliation delta, drops identifier coverage below threshold, or changes historical values for a previously closed period.

Example alert:

> Amazon settlement schema drift: 3 new fields detected (tax_collection_model, marketplace_facilitator_tax, promotion_type); 1 required field missing (sku). Bronze payload preserved. Silver/Gold publication blocked. Run 2026-08-25T07:00Z; owner: marketplace_data.

## Validation and deduplication policy

Bronze is append-only evidence and is **never deduplicated**. It records:

- pipeline run ID, API endpoint/report ID and version;
- source object URI or request window/page token;
- extraction timestamp and source modified timestamp;
- source row number or array index;
- raw payload hash and canonical row hash;
- schema hash and ingestion code commit.

The pipeline is idempotent at ingestion: rerunning the same source object/report does not create another Bronze copy unless the payload changed. Use a source record key such as report ID + source row number, or endpoint/account/window/page/index when the API supplies no event ID.

Silver does not use SELECT DISTINCT. It applies a documented rule:

1. If the source supplies a stable transaction/event ID, keep the latest version by source update timestamp.
2. If the same source report/file is replayed, merge on source record key and retain one loaded record.
3. If two rows have identical business content but different source record keys, preserve both and flag them as potential duplicates. They may be legitimate transactions.
4. Record raw rows, merged rows, replay duplicates, possible business duplicates, affected amounts, rule version, and selected survivor in the dedup audit.

Every finance fact also has uniqueness, accepted-value, nullability, date-window, row-count, amount-tie-out, and cross-source reconciliation tests.

## Snapshot and recovery strategy

- Preserve each raw API response/file in a date-partitioned immutable object path and keep the manifest according to finance retention policy.
- Store every schema snapshot and drift event; schema history is small and should not be overwritten.
- Use BigQuery time travel for short-window operational recovery.
- Create scheduled BigQuery table snapshots for close-critical Silver/Gold tables when history must outlive the time-travel window.
- Record the mapping/contract version on every published run so a historical period can be reproduced with the rules then in force.
- At month-end, persist row counts, amount totals, key coverage, schema hashes, code commit, and source manifests as a close evidence package.

## Google Sheets ingestion

Google Sheets is useful for finance-owned reference data, but a live mutable Sheet should not be the system of record.

**Efficient path**

1. Create a BigQuery external table over the governed Sheet for simple access.
2. On a schedule, snapshot the Sheet range into a dated Bronze BigQuery table, or export through the Sheets API to immutable Cloud Storage first.
3. Store Sheet ID, tab/range, modified time, editor when available, schema hash, row hashes, and pipeline run ID.
4. Validate required headers, duplicates, effective dates, and referential integrity before merging to the identifier/UOM mapping tables.

**Premium path**

Use a managed Sheets connector, but still land versioned Bronze snapshots and run the same contract/diff gates. Managed ingestion is not a substitute for history or governance.

For high-risk changes such as SKU aliases, case packs, landed-cost overrides, or brand mappings, require approval fields and effective dates. Do not let a formula edit silently rewrite closed history.

## Implementation references

- [BigQuery INFORMATION_SCHEMA.COLUMNS](https://docs.cloud.google.com/bigquery/docs/information-schema-columns)
- [BigQuery table snapshots](https://docs.cloud.google.com/bigquery/docs/table-snapshots-intro)
- [BigQuery time travel](https://docs.cloud.google.com/bigquery/docs/time-travel)
- [BigQuery external tables over Google Drive and Sheets](https://docs.cloud.google.com/bigquery/docs/external-data-drive)

