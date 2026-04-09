# FitLife Time Tracker

A clean, low-fidelity Django prototype for the FitLife studio digital
time-tracking project. Covers the two must-have requirements:

1. **REQ-01 — Log daily working hours** (employee weekly calendar view
   with inline edit, real-time validation, auto-calculated net hours,
   and offline support via `localStorage`).
2. **REQ-02 — Review target vs. actual hours** (HR dashboard with
   monthly aggregation, colour-coded deltas, search & filter,
   row-expanded daily breakdown, acknowledge, send reminder, CSV export,
   and audit log).

## Stack

- Django 4.2+
- Bootstrap 5 (CDN)
- Vanilla JavaScript (no build step)
- SQLite (zero config)

## One-click run

```bash
./run.sh
```

`run.sh` creates a virtualenv, installs Django, runs migrations, seeds
demo data, and starts the dev server on <http://127.0.0.1:8000/>.

### Manual run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

## Demo accounts

All passwords: `fitlife2026`

| Role     | Username        |
|----------|-----------------|
| Employee | `lisa.schmidt`  |
| Employee | `tom.fischer`   |
| Employee | `klara.neumann` |
| HR       | `julia.braun`   |
| Admin    | `admin`         |

The seeded data creates ~5 weeks of time entries. Tom Fischer is
deliberately under-booked to demonstrate the *deficit* (red) row in
the HR dashboard; Klara Neumann is deliberately over-booked to
demonstrate the *overtime* (amber) row.

## Project layout

```
django-app/
├── manage.py
├── run.sh
├── requirements.txt
├── project/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── timetracking/
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── apps.py
    ├── management/commands/seed_data.py
    ├── templates/timetracking/
    │   ├── base.html
    │   ├── login.html
    │   ├── weekly_calendar.html
    │   ├── hr_dashboard.html
    │   ├── hr_detail_fragment.html
    │   ├── access_denied.html
    │   └── privacy.html
    └── static/timetracking/
        ├── css/styles.css
        └── js/
            ├── calendar.js
            └── dashboard.js
```

## GDPR notes

- Session timeout after 30 minutes of inactivity.
- Role-based access enforced server-side (employees can only see their
  own data; HR can see all).
- HR actions (view, acknowledge, reminder, CSV export) are written to
  `AuditLog`.
- Employees see a consent flag on their `Employee` record; erasure is
  supported through Django admin (`/admin/`).

## URL map

| URL                           | Purpose                           |
|-------------------------------|-----------------------------------|
| `/login/`                     | Login                             |
| `/calendar/`                  | Employee weekly calendar          |
| `/api/save-entry/`            | AJAX save (upsert) a time entry   |
| `/api/delete-entry/`          | AJAX delete a time entry          |
| `/hr/`                        | HR dashboard                      |
| `/hr/detail/<id>/`            | AJAX row detail fragment          |
| `/hr/acknowledge/<id>/`       | AJAX acknowledge month            |
| `/hr/reminder/<id>/`          | AJAX send reminder                |
| `/hr/export/`                 | CSV export                        |
| `/privacy/`                   | Privacy notice                    |
| `/admin/`                     | Django admin                      |
