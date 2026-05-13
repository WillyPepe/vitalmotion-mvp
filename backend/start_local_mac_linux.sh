#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export VITALMOTION_DB="$SCRIPT_DIR/VitalMotion_v20_6_MVP_v077_SQLITE_CONNECTED.sqlite"
python3 -m uvicorn app_v077_sqlite_connected:app --host 127.0.0.1 --port 8080
