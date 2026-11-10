# Vernis — Art Intelligence Operating System

Vernis is a multi-tenant workspace for evidence-backed artwork intelligence. One canonical artwork record can participate in six independent, human-reviewed workflows: ArtSentinel, ArtShield, ConservaVision, MuseGraph, ArtValuate, and ArtTransit.

The implementation favors truthful evidence states over automated professional conclusions. Visual similarity is not authenticity or infringement; image change is not confirmed damage; a computed range is not a certified appraisal; and an evidence package does not decide liability.

## For recruiters and reviewers

Start with the [architecture](docs/system-architecture.md), [engineering decisions](docs/engineering-decisions.md), and [implementation status](docs/implementation-status.md). The project demonstrates a React/TypeScript client, a FastAPI modular monolith, PostgreSQL tenant isolation, private asset handling, durable jobs, and evidence-grounded AI workflows.

A useful local walkthrough is: open the workspace, create an organization, register an artwork with an image, run visual analysis, attach evidence, open an engine case, and generate a report or passport. The public landing page is at `/`; the workspace is at `/app`; the preserved prototype is at `/legacy`.

This is a portfolio implementation with documented production gates. Review the limitations below before interpreting model outputs. Local setup and verification commands follow.

## Repository access

Public visibility provides read access; it does not grant permission to push or merge changes. Repository write access is reserved for the owner and explicitly authorized collaborators. Copies and forks are outside the owner's repository permissions. No open-source license is granted by this repository; third-party dependencies retain their own licenses.

## Run locally

Prerequisites: Docker Desktop, or Python 3.11–3.13 with `uv`, Node 22+, PostgreSQL 17/pgvector, Redis, and Tesseract.

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Open <http://localhost:8080>. The API is available at <http://localhost:18000>. Local ports deliberately avoid a standard Supabase stack: PostgreSQL `55432`, Redis `56379`, API `18000`, web `8080`.

Compose applies additive Alembic migrations, starts FastAPI, Redis, a Celery worker, and the React frontend. Named volumes retain database, queue, and private asset data. `docker compose down` is safe; do not add `-v` unless you intend to delete local volumes.

## What is implemented

- Organization workspaces, backend RBAC, PostgreSQL RLS, audit events, entitlements, and metering.
- Canonical Artwork Registry with private, validated, single-use uploads and expiring downloads.
- Versioned visual fingerprinting, deterministic CPU embeddings, tenant-scoped retrieval, image registration/comparison, model registry, and synthetic smoke evaluation.
- Evidence ingestion, Tesseract OCR, chunking, private 1536-dimensional feature-hash embeddings, hybrid retrieval, citations, provenance assertions, and sensitivity controls.
- Six engine workspaces with real persisted records and explicit professional decision boundaries.
- Six consent-gated CrewAI configurations with narrow tools, structured outputs, citation validation, execution telemetry, partial-failure status, and human review.
- Versioned reports and versioned JSON/PDF Artwork Intelligence Passports.
- Stripe Checkout/webhook integration, organization entitlements, quotas, security headers, rate limiting, structured logs, metrics, health checks, backups, and restore drills.

The baseline CV and text descriptors are real deterministic inference, but they are not domain-trained OpenCLIP/segmentation/semantic models. No licensed external rights or market-data provider is bundled. Those capabilities remain visibly unavailable rather than returning invented results. See [model evaluation](docs/model-evaluation.md) and [implementation status](docs/implementation-status.md).

## Native development and verification

```bash
make install
docker compose up -d postgres redis
make migrate
make test
make lint
make build
make performance
```

Run the live RLS matrix against the local Compose database:

```bash
cd backend
VERNIS_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:55432/vernis \
  uv run pytest -m postgres tests/test_postgres_rls.py
```

Run the browser onboarding/upload journey with `cd frontend && npm run test:e2e`. CI repeats migrations, backend tests, RLS isolation, frontend tests/build, dependency audit, and the Playwright journey.

## External services

Local development works without hosted services. External AI is disabled unless `CREW_ENABLED`, `EXTERNAL_AI_TEXT_ENABLED`, an API key, and per-run user consent are all present. Images are never included in the current external agent payload. Stripe Checkout and webhooks remain unavailable until Stripe secrets and plan price IDs are configured. Production startup rejects development authentication, local storage, and the default signing secret.

Alembic is the application-schema authority. Supabase supplies Auth/Postgres/RLS compatibility, but its migration directory is not a second copy of application DDL. Reconcile and back up a hosted project before applying migrations.

## Operations

```bash
./scripts/backup.sh
make restore-drill BACKUP=backups/<timestamp>
```

The restore drill replaces only the dedicated `vernis_restore_drill` scratch database and never modifies the active `vernis` database. Production configuration, rollout, rollback, monitoring, and incident steps are in [deployment](docs/deployment.md) and [operations runbook](docs/operations-runbook.md).

## Documentation

- [Product vision](docs/product-vision.md)
- [System architecture](docs/system-architecture.md)
- [Database design](docs/database-design.md)
- [API design](docs/api-design.md)
- [Computer vision](docs/computer-vision.md)
- [CrewAI architecture](docs/crewai-architecture.md)
- [Multimodal RAG](docs/multimodal-rag.md) and [evidence graph](docs/evidence-graph.md)
- [Security and AI data handling](docs/security.md)
- [SaaS architecture](docs/saas-architecture.md)
- [Model evaluation](docs/model-evaluation.md)
- [Deployment](docs/deployment.md) and [operations](docs/operations-runbook.md)
- [Engineering decisions](docs/engineering-decisions.md)
- [Implementation status](docs/implementation-status.md)
- [Master rebuild plan](docs/VERNIS_MASTER_REBUILD_PLAN.md) and [UI specification](docs/VERNIS_UI_DESIGN_SPEC.md)
