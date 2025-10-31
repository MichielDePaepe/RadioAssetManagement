#!/bin/bash
# ============================================================
# Django + PostgreSQL backup script
# ------------------------------------------------------------
# 1. Dumps the full PostgreSQL database to .sql
# 2. Exports Django data to JSON (for SQLite/dev import)
# 3. Saves current Git commit info to a text file
# ------------------------------------------------------------
# NOTE:
#   - The model `taqto.Permissions` is excluded because it is
#     defined with `managed = False`, meaning Django does not
#     create a physical table for it.
#   - Any other unmanaged models should also be excluded here,
#     otherwise `dumpdata` will fail with "relation does not exist".
# ============================================================

# Load environment variables from .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Abort if ENVIRONMENT is not 'prod'
if [ "$ENVIRONMENT" != "prod" ]; then
  echo "This script cannot be executed in the '$ENVIRONMENT' environment."
  echo "Only allowed on production servers (ENVIRONMENT=prod)."
  exit 1
fi

timestamp=$(date +%Y%d%m_%H%M%S)
dump_dir="../db_dumps"

mkdir -p "$dump_dir"

# --- PostgreSQL full dump ---
pg_dump -U taqto RadioAssetManagement > "${dump_dir}/${timestamp}_postgres_dump.sql"

# --- Django JSON export ---
python manage.py dumpdata \
  --natural-foreign --natural-primary \
  -e contenttypes -e auth.Permission -e taqto.Permissions \
  --indent 2 > "${dump_dir}/${timestamp}_django_dump.json"

# --- Git version info ---
git log -1 --oneline > "${dump_dir}/${timestamp}_git_info.txt"

echo "Backup completed at ${timestamp}"
echo "Files stored in: ${dump_dir}/"