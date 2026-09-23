#!/usr/bin/env bash
# Docker が使えない環境（CI コンテナ等）向けの代替。npm でインストールした n8n を同じ設定で起動する。
# Alternative for environments without a Docker daemon: run the npm-installed n8n with the same settings.
# 使い方 / Usage:
#   N8N_RUNTIME_DIR=/path/to/dir-with-node_modules N8N_DATA_DIR=/path/to/data ./infra/run-n8n-local.sh
set -euo pipefail
: "${N8N_RUNTIME_DIR:?set N8N_RUNTIME_DIR (directory where 'npm install n8n' was run)}"
: "${N8N_DATA_DIR:?set N8N_DATA_DIR (writable directory for the .n8n folder)}"
export N8N_USER_FOLDER="$N8N_DATA_DIR"
export N8N_PORT="${N8N_PORT:-5678}"
export N8N_HOST="${N8N_HOST:-localhost}"
export N8N_LISTEN_ADDRESS="${N8N_LISTEN_ADDRESS:-127.0.0.1}"   # IPv6 が無い環境で "::" が使えないため / containers without IPv6 cannot bind "::"
export N8N_PROTOCOL=http
export N8N_WEBHOOK_URL="http://localhost:${N8N_PORT}/"
export GENERIC_TIMEZONE=Asia/Tokyo
export TZ=Asia/Tokyo
export N8N_PUBLIC_API_DISABLED=false
export N8N_SECURE_COOKIE=false              # http://localhost でログインするため / needed for plain-http localhost login
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false
export N8N_TEMPLATES_ENABLED=false
export N8N_PERSONALIZATION_ENABLED=false
export N8N_HIRING_BANNER_ENABLED=false
export N8N_RUNNERS_MODE=internal            # 開発用。本番は external 推奨 / dev only; production should use external
mkdir -p "$N8N_DATA_DIR"
exec "$N8N_RUNTIME_DIR/node_modules/.bin/n8n" start
