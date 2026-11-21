#!/usr/bin/env bash
# Build and (re)start the whole stack. Safe to re-run after every `git pull`:
# migrations and the template seed are both idempotent.
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "Missing deploy/.env — copy .env.example and fill it in."; exit 1; }

COMPOSE="docker compose -f docker-compose.prod.yml"

echo "==> Building images (first run takes ~10-15 min)"
$COMPOSE --profile tools build

echo "==> Starting Postgres"
$COMPOSE up -d --wait postgres

echo "==> Applying migrations"
$COMPOSE run --rm migrate

echo "==> Seeding system templates (idempotent)"
$COMPOSE exec -T postgres psql -v ON_ERROR_STOP=1 -U legal_ai -d legal_ai_assistant < ../database/seed-templates.sql

echo "==> Starting backend, frontend, Caddy"
$COMPOSE up -d --remove-orphans

$COMPOSE ps
DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2-)
echo
echo "Give Caddy ~30s to obtain the HTTPS certificate, then open: https://${DOMAIN}"
echo "Logs: $COMPOSE logs -f backend"
