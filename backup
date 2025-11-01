#!/bin/bash
# ============================================================
# Git + virtualenv update script
# ------------------------------------------------------------
# 1. Activates the virtual environment
# 2. Updates requirements.txt
# 3. Commits and pushes code
# ------------------------------------------------------------
# NOTE:
#   - This script is only allowed in development (ENVIRONMENT=dev)
# ============================================================

# Load environment variables from .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Abort if ENVIRONMENT is not 'dev'
if [ "$ENVIRONMENT" != "dev" ]; then
  echo "This script can only be executed in the development environment."
  echo "Current environment: '$ENVIRONMENT'"
  exit 1
fi

# ============================================================
# Update logic
# ============================================================

# Activate virtual environment
source ../bin/activate

# Update requirements.txt
pip freeze > requirements.txt

# Commit and push changes
git add -A
git commit -m "Backup op $(date '+%Y-%m-%d %H:%M:%S')"
git push

echo "Code and requirements successfully committed and pushed."
