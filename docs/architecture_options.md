# Premium and cost-aware architecture options

Both options implement the same business model and data contracts. The difference is how much connector, orchestration, observability, and semantic-layer work the company buys versus owns.

## Option A — efficient / cost-aware BigQuery architecture

~~~mermaid
flowchart LR
    S[Amazon SP-API<br/>QuickBooks API<br/>REACH API/export<br/>Google Sheets] --> I[Cloud Scheduler + Cloud Run]
    I --> B[GCS + BigQuery Bronze<br/>immutable raw]
    B --> DF[Dataform]
    DF --> SV[BigQuery Silver<br/>staging + identity + core facts]
    SV --> T[Assertions + reconciliation gates]
    T --> G[BigQuery Gold<br/>finance marts]
    G --> CS[Connected Sheets]
    G --> LS[Looker Studio]
    T --> A[Cloud Monitoring<br/>email/Slack exceptions]
~~~

**Best fit:** small finance/data team, moderate volumes, Google-centric workflow, strong cost sensitivity.

**Strengths:** serverless, small recurring software footprint, native Git/Dataform lineage and assertions, familiar Sheets consumption.

**Risks:** the team owns API changes, backfills, rate limits, and custom REACH ingestion. Mitigate with shared connector contracts, replayable raw objects, and monitoring.

## Option B — premium / managed medallion architecture

~~~mermaid
flowchart LR
    S[Amazon Selling Partner<br/>QuickBooks<br/>REACH<br/>Google Sheets] --> ELT[Managed ELT connectors<br/>+ custom REACH connector]
    ELT --> B[BigQuery Bronze<br/>source replicas + history]
    B --> DBT[dbt Cloud jobs + CI]
    DBT --> SV[BigQuery Silver<br/>conformed dimensions + facts]
    SV --> OBS[Managed observability<br/>+ dbt tests]
    OBS --> G[BigQuery Gold<br/>finance marts + semantic models]
    G --> L[Looker]
    G --> CS[Connected Sheets]
    OBS --> INC[Owned incidents + SLAs]
~~~

**Best fit:** leadership prioritizes speed, service levels, lineage, and low connector maintenance over software cost.

**Strengths:** managed connectors for Amazon and QuickBooks, faster backfills, stronger CI/lineage/observability, enterprise semantic governance.

**Risks:** higher recurring vendor spend and lock-in. Control this by keeping raw data in BigQuery, transformations in version control, and business definitions independent of the ingestion vendor.

## Common medallion contracts

| Layer | Contract | Examples |
|---|---|---|
| **Bronze / raw** | Immutable source evidence with load time, source object, row hash, schema version, and replay support | Amazon settlement rows, QuickBooks journal lines, REACH PO events, Sheet mapping snapshots |
| **Silver / core** | Typed, deduplicated, effective-dated, identity-resolved dimensions and atomic facts | dim_product, dim_brand, identifier bridge, marketplace transactions, PO lines, receipts, inventory snapshots |
| **Gold / reporting** | Reconciled finance and operating metrics with certified definitions | SKU/brand contribution margin, settlement-to-GL reconciliation, inventory health, 13-week cash outlook |
| **Control plane** | Freshness, completeness, uniqueness, financial tie-outs, identity coverage, ownership, and publication gates | Unresolved revenue, ASIN collisions, missing landed cost, late source, GL delta |

Both paths use the same [schema-drift, validation, deduplication, and replay controls](schema_drift_replay_and_validation.md). Google Sheets remains a governed input: query it as an external table when useful, but snapshot each scheduled version to Bronze so live edits cannot rewrite closed history.

## Selection recommendation

Start with Option A when the core team can support a small number of APIs and daily/batch latency is acceptable. Choose Option B immediately if connector reliability, auditability, and implementation speed are worth a materially higher subscription commitment. A sensible hybrid is managed Amazon/QuickBooks ingestion with native BigQuery + Dataform transformations.

## Current implementation references

- [Google Cloud Dataform overview](https://docs.cloud.google.com/dataform/docs/overview): Git-based BigQuery transformations, dependency management, assertions, documentation, and scheduling.
- [Google Cloud Connected Sheets](https://docs.cloud.google.com/bigquery/docs/connected-sheets): governed BigQuery analysis through the familiar Sheets interface.
- [Fivetran Amazon Selling Partner setup](https://fivetran.com/docs/connectors/applications/amazon-selling-partner/setup-guide): managed Amazon SP-API ingestion.
- [Fivetran QuickBooks connector](https://fivetran.com/docs/connectors/applications/quickbooks): managed QuickBooks ingestion.
