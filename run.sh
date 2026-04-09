#!/usr/bin/env bash
# FitLife Time Tracker — one-click launcher.
# Installs dependencies, migrates the database, seeds demo data, and runs
# the Django dev server on http://127.0.0.1:8000/
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

python manage.py migrate --noinput
python manage.py seed_data

echo ""
echo "============================================================"
echo " FitLife Time Tracker is starting at http://127.0.0.1:8000/"
echo " Employee login : lisa.schmidt  / fitlife2026"
echo " HR login       : julia.braun   / fitlife2026"
echo "============================================================"
echo ""

exec python manage.py runserver 0.0.0.0:8000
