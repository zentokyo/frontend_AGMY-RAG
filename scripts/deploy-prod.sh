#!/usr/bin/env bash
set -euo pipefail

DEPLOY_HOST="${DEPLOY_HOST:?Set DEPLOY_HOST, for example 158.160.191.33}"
DEPLOY_USER="${DEPLOY_USER:-asmuadmin}"
DEPLOY_PORT="${DEPLOY_PORT:-22}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/asmu-rag}"
DEPLOY_KEY="${DEPLOY_KEY:-}"

SSH_COMMAND="ssh -p ${DEPLOY_PORT} -o StrictHostKeyChecking=accept-new"
if [ -n "$DEPLOY_KEY" ]; then
  SSH_COMMAND="$SSH_COMMAND -i $DEPLOY_KEY"
fi

$SSH_COMMAND "$DEPLOY_USER@$DEPLOY_HOST" "
  set -euo pipefail
  sudo mkdir -p '$DEPLOY_DIR'
  sudo chown -R '$DEPLOY_USER':'$DEPLOY_USER' '$DEPLOY_DIR'
"

rsync -az --delete \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '.deploy/' \
  --exclude 'node_modules/' \
  --exclude 'apps/*/node_modules/' \
  --exclude 'apps/*/dist/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.idea/' \
  --exclude '.db-backups/' \
  --exclude 'outputs/' \
  --exclude 'screenshots/' \
  -e "$SSH_COMMAND" \
  ./ "$DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_DIR/"

$SSH_COMMAND "$DEPLOY_USER@$DEPLOY_HOST" "
  set -euo pipefail
  cd '$DEPLOY_DIR'
  test -f .env || { echo 'Missing production .env in $DEPLOY_DIR' >&2; exit 1; }
  docker compose -f docker-compose.prod.yml up -d --build --remove-orphans
  docker compose -f docker-compose.prod.yml ps
"
