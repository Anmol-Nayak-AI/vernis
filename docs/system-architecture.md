# System architecture

```mermaid
flowchart LR
  Browser[React web application] -->|JWT / dev principal| API[FastAPI versioned API]
  API --> Auth[Supabase Auth-compatible verifier]
  API --> DB[(PostgreSQL + pgvector + RLS)]
  API --> Store[Private local or S3-compatible storage]
  API --> Redis[(Redis)]
  Redis --> Worker[Celery worker]
  Worker --> CV[Shared CV inference]
  Worker --> Crew[Consent-gated CrewAI]
  CV --> DB
  Crew --> DB
  Metrics[Prometheus text metrics / JSON logs] --- API
```

FastAPI is the primary policy boundary. Every organization query includes `organization_id`; PostgreSQL forced RLS is defense in depth for exposed tables. Assets are private and referenced by immutable IDs and SHA-256 hashes. Long-running agent work is queued in Redis and executed by a Celery worker.

```mermaid
flowchart TD
  Artwork[Canonical artwork] --> Assets[Assets and fingerprints]
  Artwork --> Evidence[Evidence and chunks]
  Artwork --> Cases[Engine cases]
  Cases --> Claims[Claims and citations]
  Cases --> Runs[Agent runs and tool events]
  Cases --> Reviews[Human reviews]
  Claims --> Reports[Versioned reports]
  Assets --> Passport[Versioned passport]
  Evidence --> Passport
  Reviews --> Passport
  Cases --> Passport
```

Local CPU inference is the default. The deployment separates API and worker processes so optional higher-resource queues can be introduced without changing the data model. The original `/legacy` experience remains isolated during migration.
