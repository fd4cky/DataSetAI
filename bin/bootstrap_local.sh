#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements/local.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ".env created from .env.example"
fi

echo
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. Edit .env if your PostgreSQL credentials differ."
echo "  2. Create the PostgreSQL user/database if needed."
echo "  3. Run: python3 manage.py migrate"
echo "  4. Run: python3 manage.py seed_mvp_data"
echo "  5. Run: python3 manage.py runserver"
