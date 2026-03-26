#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python was not found in PATH. Install Python 3 first." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/local.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ".env created from .env.example"
fi

echo
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. Fill in DB_* values in .env."
echo "  2. Start the SSH tunnel: ssh -N -L 6543:127.0.0.1:5432 <ssh_user>@<server_ip>"
echo "  3. Check the connection: python scripts/check_db.py"
echo "  4. Run: python manage.py migrate"
echo "  5. Run: python manage.py seed_mvp_data"
echo "  6. Run: python manage.py runserver"
