# Vernis — Art Intelligence Operating System

Vernis is an organization-scoped foundation for evidence-backed artwork intelligence. Phase 1 provides the production-oriented SaaS base: authenticated workspaces, role enforcement, a canonical Artwork Registry, private validated asset intake, durable audit/job records, and a live Command Center. The six intelligence engines are presented as planned workflows and do not emit simulated findings.

The original AgentCanvas prototype remains available at `/legacy`. No legacy tables, generated files, or source modules are deleted by this phase.

## Phase 1 architecture

```text
React 18 + Vite + React Router + TanStack Query
                       │
                       ▼
              FastAPI /api/v1
          auth + organization RBAC
               │       │
               │       └── private local/S3-compatible asset storage
               ▼
      PostgreSQL 17 + RLS + pgvector
               │
               └── Redis + Celery worker foundation
```

FastAPI is the application authorization boundary. Every business query is scoped by `organization_id`; PostgreSQL RLS and explicit Data API grants provide defense in depth. Uploaded images are size checked, decoded with Pillow, matched against their declared MIME type, SHA-256 fingerprinted, kept private, and served through expiring links. A fingerprint identifies file bytes—it is not evidence of authenticity.

## Fastest local start

Docker Desktop or another Docker daemon is required:

```bash
docker compose up --build
```

Open `http://localhost:8080`. The Compose profile starts PostgreSQL/pgvector, Redis, applies Alembic migrations, starts the API and Celery worker, and serves the frontend. Development authentication is intentionally fixed and local while `AUTH_REQUIRED=false`.

Persistent named volumes hold PostgreSQL, Redis, and private uploaded assets. `docker compose down` stops services without deleting those volumes. Do not use `docker compose down -v` if you need the local records.

## Native development

Prerequisites: Python 3.10–3.13, [uv](https://docs.astral.sh/uv/), Node 22.12+, PostgreSQL 17 with pgvector, and Redis.

```bash
make install
docker compose up -d postgres redis
make migrate
make dev-api
```

In a second terminal:

```bash
make dev-web
```

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env.local` when enabling external providers. `backend/pyproject.toml` and `backend/uv.lock` are authoritative; the requirements files are compatibility entry points only.

## Authentication and production storage

For Supabase Auth, configure `SUPABASE_URL`, set `AUTH_REQUIRED=true`, and set the browser-safe `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`. Never expose a service-role key to the frontend.

Production startup rejects disabled authentication, local storage, and the default signing secret. Configure an S3-compatible private bucket with:

```text
STORAGE_BACKEND=s3
STORAGE_BUCKET=...
STORAGE_ENDPOINT_URL=...       # optional for AWS S3
STORAGE_REGION=...
STORAGE_ACCESS_KEY_ID=...
STORAGE_SECRET_ACCESS_KEY=...
STORAGE_SIGNING_SECRET=...     # at least 32 random characters
```

The additive Alembic migration creates the separate `vernis` schema and does not rename or drop legacy `public` tables. Supabase RLS checks live in `supabase/tests/vernis_phase1_rls.sql`. Before applying to any existing hosted project, take a backup and reconcile its live schema:

```bash
make migration-check   # renders SQL without mutating a database
make migrate
make db-inspect        # read-only table/revision/RLS summary
```

## Current API

- `GET /api/v1/health/live` and `GET /api/v1/health/ready`
- `GET|POST /api/v1/organizations`
- `GET /api/v1/organizations/{organization_id}/command-center`
- `GET|POST /api/v1/organizations/{organization_id}/artworks`
- `GET /api/v1/organizations/{organization_id}/artworks/{artwork_id}`
- `POST /api/v1/organizations/{organization_id}/assets/upload-intents`
- `PUT /api/v1/assets/uploads/{single_use_token}`
- `GET /api/v1/organizations/{organization_id}/assets/{asset_id}/download`

The legacy `/api/studio`, billing, advisory, and architecture-demo endpoints remain available for `/legacy`; they are not part of the new Phase 1 authority model.

## Verification

```bash
make lint
make test
make build
docker compose config --quiet
```

With migrated PostgreSQL available, set `VERNIS_TEST_DATABASE_URL` to run the live RLS integration test. With the API and frontend running, install Chromium once and run the real onboarding/upload browser flow:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

CI repeats linting, unit/API tests, a PostgreSQL migration plus cross-tenant RLS test, the frontend production build/audit, and the Playwright onboarding/upload journey.

## Product and rebuild documentation

- [Master rebuild plan](docs/VERNIS_MASTER_REBUILD_PLAN.md)
- [UI design specification](docs/VERNIS_UI_DESIGN_SPEC.md)

Phase 2 begins shared computer-vision infrastructure only after this foundation is reviewed. ArtSentinel and the other engines are not represented as complete in Phase 1.
