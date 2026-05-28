#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/tmp/dev_pids"
LOG_DIR="$ROOT_DIR/logs"

mkdir -p "$PID_DIR" "$LOG_DIR" "$ROOT_DIR/tmp"

"$ROOT_DIR/scripts/dev_down.sh" >/dev/null 2>&1 || true
rm -f "$ROOT_DIR/tmp/integration_server_demo.db"
python "$ROOT_DIR/scripts/generate_demo_sql.py" >"$LOG_DIR/generate_demo_sql.log"

start_service() {
  local name="$1"
  shift
  (
    cd "$ROOT_DIR"
    nohup "$@" >"$LOG_DIR/$name.log" 2>&1 </dev/null &
    echo "$!" >"$PID_DIR/$name.pid"
  )
  echo "Started $name (pid $(cat "$PID_DIR/$name.pid"))"
}

start_frontend() {
  if [ "${SKIP_FRONTEND_BUILD:-0}" != "1" ] || [ ! -f "$ROOT_DIR/frontend/dist/index.html" ]; then
    if command -v zsh >/dev/null 2>&1; then
      FRONTEND_DIR="$ROOT_DIR/frontend" zsh -lc '
        cd "$FRONTEND_DIR" &&
        VITE_USE_MOCK=false \
        VITE_API_URL_A=http://localhost:8000 \
        VITE_API_URL_B=http://localhost:8001 \
        VITE_API_URL_C=http://localhost:8002 \
        VITE_API_URL_INTEGRATION=http://localhost:8081 \
        VITE_INTEGRATION_API_KEY=integration-server-api-key-2026 \
        npm exec vite -- build
      ' >"$LOG_DIR/frontend_build.log" 2>&1
    elif command -v npm >/dev/null 2>&1; then
      (
        cd "$ROOT_DIR/frontend"
        VITE_USE_MOCK=false \
        VITE_API_URL_A=http://localhost:8000 \
        VITE_API_URL_B=http://localhost:8001 \
        VITE_API_URL_C=http://localhost:8002 \
        VITE_API_URL_INTEGRATION=http://localhost:8081 \
        VITE_INTEGRATION_API_KEY=integration-server-api-key-2026 \
        npm exec vite -- build
      ) >"$LOG_DIR/frontend_build.log" 2>&1
    else
      echo "Cannot build frontend: npm was not found and frontend/dist is missing." >&2
      return 1
    fi
  fi
  (
    cd "$ROOT_DIR"
    nohup python scripts/serve_frontend.py --host 0.0.0.0 --port 5173 --directory "$ROOT_DIR/frontend/dist" >"$LOG_DIR/frontend.log" 2>&1 </dev/null &
    echo "$!" >"$PID_DIR/frontend.pid"
  )
  echo "Started frontend (pid $(cat "$PID_DIR/frontend.pid"))"
}

start_service college_a env COLLEGE_A_STORAGE=mock COLLEGE_ID=A APP_PORT=8000 python -m uvicorn college_a.app.main:create_app --factory --host 0.0.0.0 --port 8000
start_service college_b env COLLEGE_B_STORAGE=mock COLLEGE_B_ID=B APP_PORT=8001 python -m uvicorn college_b.app.main:create_app --factory --host 0.0.0.0 --port 8001
start_service college_c env COLLEGE_C_STORAGE=mock COLLEGE_C_ID=C COLLEGE_C_PORT=8002 python -m uvicorn college_c.app.main:create_app --factory --host 0.0.0.0 --port 8002
start_service integration_server env DB_PATH="$ROOT_DIR/tmp/integration_server_demo.db" COLLEGE_A_URL=http://localhost:8000 COLLEGE_B_URL=http://localhost:8001 COLLEGE_C_URL=http://localhost:8002 API_KEY=integration-server-api-key-2026 python -m uvicorn integration_server.app:create_app --factory --host 0.0.0.0 --port 8081
start_frontend

echo
echo "Demo services are starting. Logs are in $LOG_DIR."
echo "Frontend: http://localhost:5173"
echo "Run scripts/smoke_test.sh after a few seconds to verify the loop."
