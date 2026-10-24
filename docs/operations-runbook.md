# Operations runbook

## Routine checks

Run `docker compose ps`, query `/api/v1/health/ready`, inspect `/api/v1/metrics`, verify `alembic current`, monitor failed jobs/agent runs, PostgreSQL capacity, Redis queue depth, object-storage failures, webhook failures, 429 rate, and 5xx latency.

## Backup and restore

`./scripts/backup.sh` writes a timestamped custom-format full database dump, asset archive, migration revision, and checksums. The full dump intentionally includes extension declarations, grants, and the private RLS helper schema. Copy the directory to encrypted off-host storage with retention controls. `make restore-drill BACKUP=...` recreates only `vernis_restore_drill`, restores with fail-fast behavior, and verifies the table count, pgvector, RLS helper, visual embeddings, and evidence chunks. Validate sampled artwork/evidence counts and asset hashes before declaring a production drill successful.

## Incident response

1. Record time, affected organizations, request IDs, and symptoms.
2. Disable the narrow provider or worker path if it is causing harm; keep read access where safe.
3. Preserve logs, audit events, webhook IDs, and relevant immutable artifacts.
4. Rotate exposed credentials and invalidate signed access where needed.
5. Restore into a scratch database before any production recovery.
6. Communicate scope and limitations; never erase evidence to make metrics appear healthy.

For suspected cross-tenant exposure, stop external access, preserve evidence, rotate credentials, run the RLS matrix, and involve the security/privacy owner. For agent hallucination, halt the affected crew/model version, mark outputs unreviewed, retain run/tool telemetry, and re-evaluate citations.

## Alerts

Alert on readiness failure, elevated 5xx/429 rates, p95 latency regression, failed migrations, repeated worker failures, queue backlog, failed Stripe signatures, storage errors, database saturation, backup failure, and restore-drill failure. Thresholds must be calibrated from observed traffic; no universal production thresholds are claimed here.
