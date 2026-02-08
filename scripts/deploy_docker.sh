#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=${1:-/opt/automation-orchestrator/secrets/.env}
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE"
  echo "Copy .env.docker.example to a secure location and fill in values."
  exit 1
fi

cd "$ROOT_DIR"

mkdir -p logs data

if command -v docker >/dev/null 2>&1; then
  :
else
  echo "Docker is required but not found in PATH."
  exit 1
fi

if command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE_CMD="docker-compose"
else
  DOCKER_COMPOSE_CMD="docker compose"
fi

$DOCKER_COMPOSE_CMD --env-file "$ENV_FILE" up -d --build

echo "Deployment started. Health check: http://localhost:8000/health"
