#!/usr/bin/env bash
# FitLife Studio — one-click launcher
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

python manage.py migrate --noinput
python manage.py seed

echo ""
echo "============================================"
echo " FitLife Studio — Time Tracker"
echo " http://127.0.0.1:8000/"
echo " Employee: lisa / 1234"
echo " HR:       hr / admin123"
echo "============================================"
echo ""

exec python manage.py runserver 0.0.0.0:8000
