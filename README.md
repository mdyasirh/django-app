# FitLife Studio — Digital Time Tracking Prototype

Low-fidelity functional prototype for a university HMI course.
Implements a "Stempeluhr" (punch clock) system for a German fitness studio.

## Setup & Run

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver
```

Open http://127.0.0.1:8000/

- Employee login: `lisa` / `1234` (also: tom, klara, max, anna — all PIN 1234)
- HR login: `hr` / `admin123`

Or use the one-click launcher: `./run.sh`

## Must-Have 1: Employee Punch Clock

Employees clock in/out in real time using Start / Break / Resume / Stop buttons.
- State machine: Not clocked in → Working → On break → Resumed → Clocked out
- Weekly overview with hours per day
- Incomplete entries (forgot clock-out) flagged with correction request form
- HR reminders visible on employee dashboard (bidirectional sync)

## Must-Have 2: HR Dashboard

Monthly target vs. actual overview for all employees.
- Color-coded rows: red (deficit > 5h), amber (overtime > 5h)
- Expandable day-by-day breakdown per employee
- Send reminder (with message) — appears on employee's dashboard
- Acknowledge / mark as reviewed
- Export CSV with daily granularity

## Features

- EN/DE language toggle (navbar button, uses `data-en`/`data-de` attributes)
- PIN pad on login page
- GDPR-compliant (session timeout, role-based access, no tracking)
- No JavaScript frameworks, no npm, no build tools
- SQLite database, single `style.css` stylesheet
