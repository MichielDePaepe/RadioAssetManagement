#!/bin/bash
# ============================================================
# Production deployment script
# ------------------------------------------------------------
# 1. Updates code from origin
# 2. Installs dependencies
# 3. Runs migrations and collects static files
# 4. Restarts Django (Supervisor) and Nginx
# ------------------------------------------------------------
# NOTE:
#   - This script is allowed only in production (ENVIRONMENT=prod)
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

# Fetch latest code and reset to remote
git fetch origin
git reset --hard origin/main

# Install dependencies
pip install -r requirements.txt

# Apply migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput

# Restart services
sudo supervisorctl restart django
sudo systemctl restart nginx

echo "✅ Deployment completed successfully on production."



