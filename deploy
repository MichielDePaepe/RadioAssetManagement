#!/bin/bash
# ============================================================
# Production deployment script
# ------------------------------------------------------------
# 1. Checks if local code is behind origin/main
# 2. If yes, pulls updates, reinstalls dependencies,
#    runs migrations, collects static files,
#    and restarts Django + Nginx
# 3. If no updates are needed, it exits gracefully.
# ------------------------------------------------------------
# NOTE:
#   - This script may only run in production (ENVIRONMENT=prod)
# ============================================================

# Load environment variables from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Abort if ENVIRONMENT is not 'prod'
if [ "$ENVIRONMENT" != "prod" ]; then
  echo "❌ This script can only be executed in the production environment."
  echo "Current environment: '$ENVIRONMENT'"
  exit 1
fi

# ============================================================
# Deployment logic
# ============================================================

source ../bin/activate

echo "🔍 Checking for updates..."
git fetch origin

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
  echo "✅ Already up to date. No deployment needed."
  exit 0
fi

echo "⬇️  Updates found — deploying latest version..."

# Reset to the latest version from origin
git reset --hard origin/main

# Install updated dependencies
pip install -r requirements.txt

# Apply migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput

# Restart services
sudo supervisorctl restart django
sudo systemctl restart nginx

echo "🚀 Deployment completed successfully."