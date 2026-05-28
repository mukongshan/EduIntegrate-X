#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
python -m pip install -r requirements-demo.txt

if command -v zsh >/dev/null 2>&1; then
  FRONTEND_DIR="$ROOT_DIR/frontend" zsh -lc 'cd "$FRONTEND_DIR" && npm install'
else
  cd "$ROOT_DIR/frontend"
  npm install
fi

echo "Demo dependencies installed."
