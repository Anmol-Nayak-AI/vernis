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
