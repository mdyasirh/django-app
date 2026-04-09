#!/usr/bin/env bash
# One-click launcher: installs dependencies and starts the Django dev server.
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

exec python manage.py runserver 0.0.0.0:8000
