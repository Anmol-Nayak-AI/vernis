# Database design

Alembic is the application-schema authority. Additive migrations create the `vernis` schema and retain legacy `public` data. UUID primary keys, tenant-qualified foreign keys, explicit grants, indexes, and forced row-level security protect organization data.

```mermaid
erDiagram
  ORGANIZATIONS ||--o{ MEMBERSHIPS : has
  ORGANIZATIONS ||--o{ ARTWORKS : owns
  ARTWORKS ||--o{ ARTWORK_ASSETS : has
  ARTWORKS ||--o{ ENGINE_CASES : examined_by
  ARTWORKS ||--o{ EVIDENCE_DOCUMENTS : documented_by
  EVIDENCE_DOCUMENTS ||--o{ EVIDENCE_CHUNKS : split_into
  ENGINE_CASES ||--o{ EVIDENCE_CLAIMS : contains
  ENGINE_CASES ||--o{ HUMAN_REVIEWS : reviewed_by
  ENGINE_CASES ||--o{ AGENT_RUNS : orchestrates
  AGENT_RUNS ||--o{ TOOL_EXECUTIONS : records
  ENGINE_CASES ||--o{ REPORT_VERSIONS : exports
  ARTWORKS ||--o{ ARTWORK_PASSPORTS : snapshots
  ORGANIZATIONS ||--o| SUBSCRIPTIONS : billed_by
  ORGANIZATIONS ||--o{ USAGE_EVENTS : meters
```

Engine-specific tables keep domain state separate: copyright matches, condition inspections/findings, collection records/relationships, market comparables/valuation reports, and shipments/custody events. `vector(96)` stores the current visual baseline descriptor; `vector(1536)` stores private text feature-hash vectors. HNSW and full-text GIN indexes support retrieval.

Restricted evidence RLS allows owners, administrators, investigators, and reviewers only. Application checks additionally restrict writes by role and internal passport export. Stripe webhook IDs are unique for idempotency. No migration drops legacy tables.
