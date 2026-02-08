#!/usr/bin/env bash
set -euo pipefail

OUT_DIR=${1:-/opt/automation-orchestrator/certs}

mkdir -p "$OUT_DIR"

openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout "$OUT_DIR/ao.key" -out "$OUT_DIR/ao.crt" \
  -subj "/C=US/ST=NA/L=NA/O=Customer/OU=IT/CN=automation-orchestrator"

echo "Self-signed cert created:"
printf "  %s\n" "$OUT_DIR/ao.crt" "$OUT_DIR/ao.key"
