#!/usr/bin/env bash
# Start the ZhouYiFish workbench without requiring a model key or Zep.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -c "import flask, flask_cors, dotenv, sxtwl" 2>/dev/null || python3 -m pip install -q flask flask-cors python-dotenv 'sxtwl==2.0.7'
mkdir -p "$ROOT/backend/data"
export ZHOUYI_DB_PATH="${ZHOUYI_DB_PATH:-$ROOT/backend/data/zhouyi.sqlite}"
python3 "$ROOT/backend/run.py" &
BACK_PID=$!
cleanup() { kill "$BACK_PID" 2>/dev/null || true; }
trap cleanup EXIT
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
npm run dev -- --host 127.0.0.1 --port "${ZHOUYI_WEB_PORT:-3000}"
