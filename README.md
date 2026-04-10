# FitLife Studio – Digital Time Tracking (Stempeluhr)

A Django-based punch-clock web application for a German fitness studio.

## Features

- PIN-based employee login with visual numeric keypad
- Real-time punch clock (Clock In / Break / Clock Out) via AJAX
- HR dashboard with monthly hour aggregation and conditional formatting
- CSV export of time records
- Correction requests for missing clock-outs
- Dark-mode UI with Bootstrap 5
- Custom EN/DE language toggle (no Django i18n)

## Quick Start

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed       # creates demo users & data
python manage.py runserver
```

### Demo Credentials

| User  | PIN  | Role     |
|-------|------|----------|
| hr    | 9999 | HR       |
| lisa  | 1111 | Employee |
| tom   | 2222 | Employee |
| klara | 3333 | Employee |
| max   | 4444 | Employee |
| anna  | 5555 | Employee |

## Tech Stack

- Python 3 / Django 5.x
- SQLite (default)
- Bootstrap 5 (CDN)
- Vanilla HTML / JS (no frameworks, no npm)
