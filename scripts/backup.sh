#!/usr/bin/env bash
set -euo pipefail

backup_root="${1:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="${backup_root%/}/${timestamp}"
mkdir -p "$backup_dir"

# Back up the whole database so extension declarations, the private RLS helper
# schema, grants, and the application schema are restored as one consistent unit.
docker compose exec -T postgres pg_dump --username=postgres --dbname=vernis --format=custom > "$backup_dir/vernis.dump"
docker compose exec -T api tar -C /app/storage -czf - . > "$backup_dir/assets.tar.gz"
docker compose exec -T api alembic current > "$backup_dir/alembic-current.txt"

if command -v shasum >/dev/null 2>&1; then
  (cd "$backup_dir" && shasum -a 256 vernis.dump assets.tar.gz alembic-current.txt > SHA256SUMS)
else
  (cd "$backup_dir" && sha256sum vernis.dump assets.tar.gz alembic-current.txt > SHA256SUMS)
fi

echo "Backup written to $backup_dir"
