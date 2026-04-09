import csv
import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import AuditLog, Employee, MonthLock, MonthReview, TimeEntry


# ---------- Helpers ----------

def _get_employee(user):
    return getattr(user, "employee", None)


def _is_hr(user):
    emp = _get_employee(user)
    return bool(emp and emp.is_hr)


def _iso_week_dates(year: int, week: int):
    """Return the 7 dates (Mon–Sun) for the given ISO year/week."""
    monday = date.fromisocalendar(year, week, 1)
    return [monday + timedelta(days=i) for i in range(7)]


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------- Employee views ----------

@login_required
def home(request):
    emp = _get_employee(request.user)
    if emp and emp.is_hr:
        return redirect("hr_dashboard")
    return redirect("weekly_calendar")


@login_required
def weekly_calendar_view(request):
    emp = _get_employee(request.user)
    if emp is None:
        return redirect("login")
    if emp.is_hr:
        return redirect("hr_dashboard")

    today = timezone.localdate()
    iso = today.isocalendar()
    year = _parse_int(request.GET.get("year"), iso.year)
    week = _parse_int(request.GET.get("week"), iso.week)

    try:
        week_dates = _iso_week_dates(year, week)
    except ValueError:
        week_dates = _iso_week_dates(iso.year, iso.week)
        year, week = iso.year, iso.week

    entries_qs = TimeEntry.objects.filter(
        employee=emp, date__in=week_dates
    )
    entries_by_date = {e.date: e for e in entries_qs}

    days = []
    for d in week_dates:
        entry = entries_by_date.get(d)
        days.append(
            {
                "date": d,
                "iso": d.isoformat(),
                "label": d.strftime("%a"),
                "day_num": d.day,
                "month_name": d.strftime("%b"),
                "is_today": d == today,
                "entry": entry,
                "start": entry.start_time.strftime("%H:%M") if entry else "",
                "end": entry.end_time.strftime("%H:%M") if entry else "",
                "break_minutes": int(entry.break_duration.total_seconds() // 60) if entry else 0,
                "net": f"{entry.net_hours}" if entry else "",
            }
        )

    # Previous / next week for navigation
    monday = week_dates[0]
    prev_monday = monday - timedelta(days=7)
    next_monday = monday + timedelta(days=7)
    prev_iso = prev_monday.isocalendar()
    next_iso = next_monday.isocalendar()

    week_total = sum((d["entry"].net_hours for d in days if d["entry"]), Decimal("0"))

    context = {
        "days": days,
        "week_num": week,
        "year": year,
        "range_label": f"{week_dates[0].strftime('%d %b')} – {week_dates[-1].strftime('%d %b %Y')}",
        "prev_year": prev_iso.year,
        "prev_week": prev_iso.week,
        "next_year": next_iso.year,
        "next_week": next_iso.week,
        "employee": emp,
        "week_total": week_total,
    }
    return render(request, "timetracking/weekly_calendar.html", context)


@login_required
@require_POST
def save_time_entry(request):
    emp = _get_employee(request.user)
    if emp is None or emp.is_hr:
        return JsonResponse({"error": "Not allowed."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    date_str = payload.get("date")
    start_str = payload.get("start_time")
    end_str = payload.get("end_time")
    break_minutes = payload.get("break_minutes", 0)

    try:
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        break_minutes = int(break_minutes)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Please enter valid values (HH:MM, minutes)."}, status=400
        )

    if end_time <= start_time:
        return JsonResponse(
            {"error": "End time cannot be before or equal to start time."}, status=400
        )

    shift_minutes = (
        datetime.combine(entry_date, end_time)
        - datetime.combine(entry_date, start_time)
    ).total_seconds() / 60

    if break_minutes < 0 or break_minutes >= shift_minutes:
        return JsonResponse(
            {"error": "Break duration exceeds total shift length."}, status=400
        )

    if MonthLock.objects.filter(year=entry_date.year, month=entry_date.month).exists():
        return JsonResponse({"error": "Month has been finalised."}, status=403)

    entry, created = TimeEntry.objects.update_or_create(
        employee=emp,
        date=entry_date,
        defaults={
            "start_time": start_time,
            "end_time": end_time,
            "break_duration": timedelta(minutes=break_minutes),
        },
    )

    return JsonResponse(
        {
            "net_hours": str(entry.net_hours),
            "message": "Hours saved successfully.",
            "created": created,
        }
    )


@login_required
@require_POST
def delete_time_entry(request):
    emp = _get_employee(request.user)
    if emp is None or emp.is_hr:
        return JsonResponse({"error": "Not allowed."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        entry_date = datetime.strptime(payload.get("date"), "%Y-%m-%d").date()
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if MonthLock.objects.filter(year=entry_date.year, month=entry_date.month).exists():
        return JsonResponse({"error": "Month has been finalised."}, status=403)

    TimeEntry.objects.filter(employee=emp, date=entry_date).delete()
    return JsonResponse({"message": "Entry deleted."})


# ---------- HR views ----------

def _previous_month(today):
    first_of_month = today.replace(day=1)
    prev = first_of_month - timedelta(days=1)
    return prev.year, prev.month


def _hr_guard(request):
    emp = _get_employee(request.user)
    if emp is None or not emp.is_hr:
        return False
    return True


@login_required
def hr_dashboard(request):
    if not _hr_guard(request):
        return render(
            request,
            "timetracking/access_denied.html",
            status=403,
        )

    today = timezone.localdate()
    default_year, default_month = _previous_month(today)
    year = _parse_int(request.GET.get("year"), default_year)
    month = _parse_int(request.GET.get("month"), default_month)

    if not (1 <= month <= 12):
        month = default_month
        year = default_year

    start_of_month = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_of_month = date(year, month, last_day)

    employees = Employee.objects.filter(role="employee").select_related("user")
    rows = []
    departments = set()
    for emp in employees:
        actual = (
            TimeEntry.objects.filter(
                employee=emp, date__gte=start_of_month, date__lte=end_of_month
            ).aggregate(total=Sum("net_hours"))["total"]
            or Decimal("0")
        )
        target = emp.target_hours or Decimal("0")
        delta = actual - target

        if delta < Decimal("-5"):
            color = "table-danger"
            badge = "Deficit"
            badge_cls = "bg-danger"
        elif delta > Decimal("5"):
            color = "table-warning"
            badge = "Overtime"
            badge_cls = "bg-warning text-dark"
        else:
            color = ""
            badge = "On target"
            badge_cls = "bg-success"

        review = MonthReview.objects.filter(
            employee=emp, year=year, month=month
        ).first()

        rows.append(
            {
                "id": emp.id,
                "name": emp.full_name,
                "department": emp.department,
                "target": target,
                "actual": actual,
                "delta": delta,
                "color": color,
                "badge": badge,
                "badge_cls": badge_cls,
                "reviewed": bool(review and review.reviewed_by_id),
                "reminder_sent": bool(review and review.reminder_sent),
                "email": emp.user.email,
            }
        )
        departments.add(emp.department)

    # Summary for top cards
    total_target = sum((r["target"] for r in rows), Decimal("0"))
    total_actual = sum((r["actual"] for r in rows), Decimal("0"))
    total_delta = total_actual - total_target
    deficit_count = sum(1 for r in rows if r["delta"] < Decimal("-5"))
    overtime_count = sum(1 for r in rows if r["delta"] > Decimal("5"))

    months = [
        (i, date(2000, i, 1).strftime("%B")) for i in range(1, 13)
    ]
    years = sorted({year, today.year, today.year - 1})

    context = {
        "rows": rows,
        "selected_month": month,
        "selected_year": year,
        "month_label": start_of_month.strftime("%B %Y"),
        "months": months,
        "years": years,
        "departments": sorted(departments),
        "total_target": total_target,
        "total_actual": total_actual,
        "total_delta": total_delta,
        "deficit_count": deficit_count,
        "overtime_count": overtime_count,
        "employee_count": len(rows),
    }
    return render(request, "timetracking/hr_dashboard.html", context)


@login_required
@require_GET
def hr_employee_detail(request, employee_id):
    if not _hr_guard(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    employee = get_object_or_404(Employee, pk=employee_id)
    today = timezone.localdate()
    default_year, default_month = _previous_month(today)
    year = _parse_int(request.GET.get("year"), default_year)
    month = _parse_int(request.GET.get("month"), default_month)

    last_day = monthrange(year, month)[1]
    start_of_month = date(year, month, 1)
    end_of_month = date(year, month, last_day)

    entries = {
        e.date: e
        for e in TimeEntry.objects.filter(
            employee=employee, date__gte=start_of_month, date__lte=end_of_month
        )
    }

    rows = []
    total = Decimal("0")
    for day_num in range(1, last_day + 1):
        d = date(year, month, day_num)
        entry = entries.get(d)
        if entry:
            total += entry.net_hours
        rows.append(
            {
                "date": d,
                "label": d.strftime("%a %d %b"),
                "entry": entry,
                "weekend": d.weekday() >= 5,
            }
        )

    review = MonthReview.objects.filter(
        employee=employee, year=year, month=month
    ).first()

    # Log view action
    AuditLog.objects.create(
        user=request.user,
        action=f"Viewed detail: {employee.full_name} — {start_of_month:%B %Y}",
    )

    context = {
        "employee": employee,
        "rows": rows,
        "year": year,
        "month": month,
        "month_label": start_of_month.strftime("%B %Y"),
        "total": total,
        "target": employee.target_hours,
        "delta": total - employee.target_hours,
        "review": review,
    }
    return render(request, "timetracking/hr_detail_fragment.html", context)


@login_required
@require_POST
def hr_acknowledge(request, employee_id):
    if not _hr_guard(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    employee = get_object_or_404(Employee, pk=employee_id)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    today = timezone.localdate()
    default_year, default_month = _previous_month(today)
    year = _parse_int(payload.get("year"), default_year)
    month = _parse_int(payload.get("month"), default_month)

    review, _ = MonthReview.objects.update_or_create(
        employee=employee,
        year=year,
        month=month,
        defaults={"reviewed_by": request.user},
    )

    AuditLog.objects.create(
        user=request.user,
        action=f"Acknowledged {employee.full_name} — {year}-{month:02d}",
    )

    return JsonResponse(
        {
            "status": "reviewed",
            "reviewed_by": request.user.get_full_name() or request.user.username,
        }
    )


@login_required
@require_POST
def hr_send_reminder(request, employee_id):
    if not _hr_guard(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    employee = get_object_or_404(Employee, pk=employee_id)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    today = timezone.localdate()
    default_year, default_month = _previous_month(today)
    year = _parse_int(payload.get("year"), default_year)
    month = _parse_int(payload.get("month"), default_month)

    review, _ = MonthReview.objects.update_or_create(
        employee=employee,
        year=year,
        month=month,
        defaults={"reminder_sent": True},
    )

    AuditLog.objects.create(
        user=request.user,
        action=f"Sent reminder to {employee.full_name} — {year}-{month:02d}",
    )

    return JsonResponse(
        {
            "status": "reminder_sent",
            "message": f"Reminder sent to {employee.full_name}.",
        }
    )


@login_required
def hr_export_csv(request):
    if not _hr_guard(request):
        return HttpResponse("Forbidden", status=403)

    today = timezone.localdate()
    default_year, default_month = _previous_month(today)
    year = _parse_int(request.GET.get("year"), default_year)
    month = _parse_int(request.GET.get("month"), default_month)

    last_day = monthrange(year, month)[1]
    start_of_month = date(year, month, 1)
    end_of_month = date(year, month, last_day)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="timetracking_{year}_{month:02d}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(
        ["Employee", "Department", "Target Hours", "Actual Hours", "Delta", "Status"]
    )

    employees = Employee.objects.filter(role="employee").select_related("user")
    for emp in employees:
        actual = (
            TimeEntry.objects.filter(
                employee=emp, date__gte=start_of_month, date__lte=end_of_month
            ).aggregate(total=Sum("net_hours"))["total"]
            or Decimal("0")
        )
        delta = actual - emp.target_hours
        if delta < Decimal("-5"):
            status = "Deficit"
        elif delta > Decimal("5"):
            status = "Overtime"
        else:
            status = "On target"
        writer.writerow(
            [emp.full_name, emp.department, emp.target_hours, actual, delta, status]
        )

    AuditLog.objects.create(
        user=request.user,
        action=f"Exported CSV — {year}-{month:02d}",
    )
    return response


@login_required
def privacy(request):
    return render(request, "timetracking/privacy.html")
