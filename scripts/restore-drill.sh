#!/usr/bin/env bash
set -euo pipefail

backup_dir="${1:-}"
confirmation="${2:-}"
drill_database="vernis_restore_drill"

if [[ -z "$backup_dir" || "$confirmation" != "--confirm-scratch-reset" ]]; then
  echo "Usage: scripts/restore-drill.sh BACKUP_DIRECTORY --confirm-scratch-reset" >&2
  exit 2
fi
if [[ ! -f "$backup_dir/vernis.dump" ]]; then
  echo "Missing $backup_dir/vernis.dump" >&2
  exit 2
fi

docker compose exec -T postgres dropdb --username=postgres --if-exists "$drill_database"
docker compose exec -T postgres createdb --username=postgres "$drill_database"
docker compose exec -T postgres pg_restore --username=postgres --dbname="$drill_database" --no-owner --no-privileges --exit-on-error < "$backup_dir/vernis.dump"
docker compose exec -T postgres psql --username=postgres --dbname="$drill_database" --tuples-only --command="
select json_build_object(
  'tables', (select count(*) from information_schema.tables where table_schema = 'vernis'),
  'vector_extension', exists(select 1 from pg_extension where extname = 'vector'),
  'rls_helper', to_regprocedure('vernis_private.current_user_id()') is not null,
  'visual_embeddings', to_regclass('vernis.visual_embeddings') is not null,
  'evidence_chunks', to_regclass('vernis.evidence_chunks') is not null
);"

echo "Restore drill succeeded in scratch database $drill_database; the active vernis database was not modified."
