# Deployment

The reference deployment has five units: reverse-proxied frontend, FastAPI API, Celery worker, PostgreSQL 17 with pgvector, and Redis. Run API and workers from the same immutable backend image and apply Alembic once before traffic.

Production requirements:

- `ENVIRONMENT=production`, `AUTH_REQUIRED=true`, Supabase URL/audience/issuer configuration.
- Private S3-compatible storage, HTTPS, managed encryption, versioning, lifecycle policy, and non-default signing secret.
- Managed PostgreSQL backups/PITR, pgvector, tested RLS roles, connection pooling, and migration backup.
- Managed Redis with authentication/TLS where supported.
- Secret-manager injection for OpenAI, Stripe, database, storage, and Supabase secrets.
- Stripe webhook TLS endpoint and configured plan Price IDs.
- Central JSON logs, `/api/v1/metrics` collection, health probes, queue depth, error-rate, latency, storage, and database alerts.

Rollout: back up; run migration SQL review; migrate a staging copy; run RLS/API/E2E/restore checks; deploy worker then API then frontend; verify health and critical workflows; enable traffic progressively. Rollback application images first. Database migrations are additive; do not run downgrade on customer data without a reviewed recovery plan. Restore from a verified backup if schema rollback is required.

The Compose environment is a local demonstrator, not a high-availability production topology.

## Local verification

Native defaults match Compose: PostgreSQL `55432`, Redis `56379`. Compose keeps external AI disabled. To explicitly enable text-only agent runs, set `CREW_ENABLED=true EXTERNAL_AI_TEXT_ENABLED=true` in the shell when starting both API and worker; each run still requires consent.

The Nginx proxy reserves `/api/` and `/generated/` before static-file matching, so paths ending in an image or document extension reach the API rather than returning a static 404.

## Public portfolio repository

Source: <https://github.com/Anmol-Nayak-AI/vernis>. Public visibility permits reading and copying without granting push or merge access. Only explicitly authorized accounts should receive write access. Keep secrets in deployment configuration, never in commits. No open-source license is included.

A public source repository does not itself host this full-stack application. A hosted rollout needs the production services and credentials listed above; local Docker verification does not establish a public production deployment.
