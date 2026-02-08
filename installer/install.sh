#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:-config/app_config.json}"

cd "$ROOT_DIR"

if [ ! -f "$CONFIG_PATH" ]; then
  cp config/sample_config.json "$CONFIG_PATH"
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

VENV_PY="$ROOT_DIR/.venv/bin/python"

WHEELS_DIR="$ROOT_DIR/vendor/wheels"
HAS_WHEELS=false
if [ -d "$WHEELS_DIR" ] && [ -n "$(ls -A "$WHEELS_DIR"/*.whl 2>/dev/null)" ]; then
  HAS_WHEELS=true
fi

if [ "$HAS_WHEELS" = true ]; then
  echo "Installing from offline wheels..."
  "$VENV_PY" -m pip install --no-index --find-links vendor/wheels -r requirements.txt
else
  echo "Installing from PyPI (requires internet)..."
  "$VENV_PY" -m pip install -r requirements.txt
fi

export AO_CONFIG="$CONFIG_PATH"
"$VENV_PY" installer/launch_services.py "$CONFIG_PATH"
