import csv
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import CorrectionRequest, DailyTimeRecord, Employee, HRReview


# ── helpers ──────────────────────────────────────────────────────────────

def _emp(user):
    return getattr(user, "employee", None)


def _is_hr(user):
    emp = _emp(user)
    return bool(emp and emp.is_hr)


def _parse_int(v, default):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _prev_month(today):
    first = today.replace(day=1)
    prev = first - timedelta(days=1)
    return prev.year, prev.month


def _week_dates(ref):
    mon = ref - timedelta(days=ref.weekday())
    return [mon + timedelta(days=i) for i in range(7)]


def _now():
    return timezone.localtime().time().replace(microsecond=0)


# ── auth / routing ───────────────────────────────────────────────────────

@login_required
def home(request):
    if _is_hr(request.user):
        return redirect("hr_dashboard")
    return redirect("employee_dashboard")


# ── employee punch-clock ─────────────────────────────────────────────────

@login_required
def employee_dashboard(request):
    emp = _emp(request.user)
    if emp is None:
        return redirect("login")
    if emp.is_hr:
        return redirect("hr_dashboard")

    today = timezone.localdate()
    rec = DailyTimeRecord.objects.filter(employee=emp, date=today).first()

    if rec is None:
        state = "NONE"
    elif rec.status == DailyTimeRecord.STATUS_ON_BREAK:
        state = "ON_BREAK"
    elif rec.status == DailyTimeRecord.STATUS_CLOCKED_OUT and rec.clock_out:
        state = "CLOCKED_OUT"
    elif rec.clock_in and not rec.clock_out:
        state = "WORKING"
    else:
        state = "NONE"

    # weekly overview
    week = _week_dates(today)
    recs = {
        r.date: r
        for r in DailyTimeRecord.objects.filter(
            employee=emp, date__gte=week[0], date__lte=week[-1]
        )
    }
    week_rows = []
    week_total = Decimal("0.00")
    for d in week:
        r = recs.get(d)
        incomplete = bool(r and r.clock_in and not r.clock_out and d < today)
        if r:
            week_total += r.net_hours
        week_rows.append(
            {"date": d, "label": d.strftime("%a %d %b"), "record": r,
             "incomplete": incomplete, "is_today": d == today}
        )

    # HR reminders visible to this employee (sync: HR→Employee)
    reminders = HRReview.objects.filter(
        employee=emp, status=HRReview.STATUS_REMINDER_SENT, reminder_seen=False
    ).order_by("-updated_at")

    return render(request, "timetracking/employee.html", {
        "employee": emp, "today": today,
        "today_label": today.strftime("%A, %d %B %Y"),
        "record": rec, "state": state,
        "week_rows": week_rows,
        "week_total": week_total.quantize(Decimal("0.01")),
        "reminders": reminders,
    })


@login_required
@require_POST
def clock_in(request):
    emp = _emp(request.user)
    if not emp or emp.is_hr:
        return redirect("home")
    today = timezone.localdate()
    rec, created = DailyTimeRecord.objects.get_or_create(
        employee=emp, date=today,
        defaults={"clock_in": _now(), "status": DailyTimeRecord.STATUS_WORKING},
    )
    if not created and not rec.clock_in:
        rec.clock_in = _now()
        rec.status = DailyTimeRecord.STATUS_WORKING
        rec.save()
    return redirect("employee_dashboard")


@login_required
@require_POST
def break_start(request):
    emp = _emp(request.user)
    if not emp or emp.is_hr:
        return redirect("home")
    today = timezone.localdate()
    rec = DailyTimeRecord.objects.filter(employee=emp, date=today).first()
    if rec and rec.status == DailyTimeRecord.STATUS_WORKING:
        rec.break_start = _now()
        rec.status = DailyTimeRecord.STATUS_ON_BREAK
        rec.save()
    return redirect("employee_dashboard")


@login_required
@require_POST
def resume(request):
    emp = _emp(request.user)
    if not emp or emp.is_hr:
        return redirect("home")
    today = timezone.localdate()
    rec = DailyTimeRecord.objects.filter(employee=emp, date=today).first()
    if rec and rec.status == DailyTimeRecord.STATUS_ON_BREAK and rec.break_start:
        rec.break_end = _now()
        rec.status = DailyTimeRecord.STATUS_WORKING
        rec.save()
    return redirect("employee_dashboard")


@login_required
@require_POST
def clock_out(request):
    emp = _emp(request.user)
    if not emp or emp.is_hr:
        return redirect("home")
    today = timezone.localdate()
    rec = DailyTimeRecord.objects.filter(employee=emp, date=today).first()
    if rec and rec.clock_in and not rec.clock_out:
        # auto-close open break
        if rec.status == DailyTimeRecord.STATUS_ON_BREAK and rec.break_start and not rec.break_end:
            rec.break_end = _now()
        rec.clock_out = _now()
        rec.status = DailyTimeRecord.STATUS_CLOCKED_OUT
        rec.save()
        messages.success(request, "Hours saved successfully")
    return redirect("employee_dashboard")


@login_required
@require_POST
def correction(request, record_id):
    emp = _emp(request.user)
    if not emp or emp.is_hr:
        return redirect("home")
    rec = get_object_or_404(DailyTimeRecord, pk=record_id, employee=emp)
    proposed = request.POST.get("proposed_clock_out", "")
    try:
        t = datetime.strptime(proposed, "%H:%M").time()
    except ValueError:
        messages.warning(request, "Invalid time format.")
        return redirect("employee_dashboard")
    CorrectionRequest.objects.create(entry=rec, proposed_clock_out=t)
    messages.success(request, "Correction submitted for HR review.")
    return redirect("employee_dashboard")


@login_required
@require_POST
def dismiss_reminder(request, review_id):
    emp = _emp(request.user)
    if not emp:
        return redirect("home")
    rv = get_object_or_404(HRReview, pk=review_id, employee=emp)
    rv.reminder_seen = True
    rv.save(update_fields=["reminder_seen"])
    return redirect("employee_dashboard")


# ── HR dashboard ─────────────────────────────────────────────────────────

@login_required
def hr_dashboard(request):
    if not _is_hr(request.user):
        return render(request, "timetracking/access_denied.html", status=403)

    today = timezone.localdate()
    dy, dm = _prev_month(today)
    year = _parse_int(request.GET.get("year"), dy)
    month = _parse_int(request.GET.get("month"), dm)
    if not 1 <= month <= 12:
        year, month = dy, dm

    first = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    last = date(year, month, last_day)
    prev_d = first - timedelta(days=1)
    next_d = last + timedelta(days=1)

    employees = Employee.objects.filter(role="employee").select_related("user")
    rows = []
    for emp in employees:
        recs = list(DailyTimeRecord.objects.filter(
            employee=emp, date__gte=first, date__lte=last
        ))
        by_date = {r.date: r for r in recs}
        actual = sum((r.net_hours for r in recs), Decimal("0.00"))
        target = emp.target_hours or Decimal("0.00")
        delta = actual - target

        if delta < Decimal("-5"):
            row_cls, badge, badge_cls = "table-danger", "Deficit", "bg-danger"
        elif delta > Decimal("5"):
            row_cls, badge, badge_cls = "table-warning", "Overtime", "bg-warning text-dark"
        else:
            row_cls, badge, badge_cls = "", "On target", "bg-success"

        review = HRReview.objects.filter(employee=emp, year=year, month=month).first()

        day_rows = []
        for i in range(last_day):
            d = first + timedelta(days=i)
            r = by_date.get(d)
            if r is None:
                st = "none"
            elif r.clock_in and not r.clock_out:
                st = "incomplete"
            else:
                st = "ok"
            day_rows.append({
                "date": d, "label": d.strftime("%a %d %b"),
                "weekend": d.weekday() >= 5, "record": r, "state": st,
            })

        rows.append({
            "id": emp.id, "name": emp.full_name,
            "department": emp.department,
            "target": target.quantize(Decimal("0.01")),
            "actual": actual.quantize(Decimal("0.01")),
            "delta": delta.quantize(Decimal("0.01")),
            "row_cls": row_cls, "badge": badge, "badge_cls": badge_cls,
            "reviewed": bool(review and review.status == HRReview.STATUS_REVIEWED),
            "reminder_sent": bool(review and review.status == HRReview.STATUS_REMINDER_SENT),
            "email": emp.user.email or f"{emp.user.username}@fitlife.de",
            "day_rows": day_rows,
        })

    total_target = sum((r["target"] for r in rows), Decimal("0.00"))
    total_actual = sum((r["actual"] for r in rows), Decimal("0.00"))

    return render(request, "timetracking/hr_dashboard.html", {
        "rows": rows,
        "selected_month": month, "selected_year": year,
        "month_label": first.strftime("%B %Y"),
        "prev_year": prev_d.year, "prev_month": prev_d.month,
        "next_year": next_d.year, "next_month": next_d.month,
        "total_target": total_target.quantize(Decimal("0.01")),
        "total_actual": total_actual.quantize(Decimal("0.01")),
        "total_delta": (total_actual - total_target).quantize(Decimal("0.01")),
        "deficit_count": sum(1 for r in rows if r["delta"] < Decimal("-5")),
        "overtime_count": sum(1 for r in rows if r["delta"] > Decimal("5")),
        "employee_count": len(rows),
    })


@login_required
@require_POST
def hr_acknowledge(request, employee_id):
    if not _is_hr(request.user):
        return render(request, "timetracking/access_denied.html", status=403)
    emp = get_object_or_404(Employee, pk=employee_id)
    year = _parse_int(request.POST.get("year"), 0)
    month = _parse_int(request.POST.get("month"), 0)
    HRReview.objects.update_or_create(
        employee=emp, year=year, month=month,
        defaults={"status": HRReview.STATUS_REVIEWED},
    )
    messages.success(request, f"{emp.full_name} — Reviewed ✓")
    return redirect(f"/hr/?year={year}&month={month}")


@login_required
@require_POST
def hr_send_reminder(request, employee_id):
    if not _is_hr(request.user):
        return render(request, "timetracking/access_denied.html", status=403)
    emp = get_object_or_404(Employee, pk=employee_id)
    year = _parse_int(request.POST.get("year"), 0)
    month = _parse_int(request.POST.get("month"), 0)
    msg = request.POST.get("message", "").strip()
    HRReview.objects.update_or_create(
        employee=emp, year=year, month=month,
        defaults={"status": HRReview.STATUS_REMINDER_SENT,
                   "reminder_message": msg, "reminder_seen": False},
    )
    messages.success(request, f"Reminder sent to {emp.full_name}.")
    return redirect(f"/hr/?year={year}&month={month}")


@login_required
def hr_export_csv(request):
    if not _is_hr(request.user):
        return HttpResponse("Forbidden", status=403)
    today = timezone.localdate()
    dy, dm = _prev_month(today)
    year = _parse_int(request.GET.get("year"), dy)
    month = _parse_int(request.GET.get("month"), dm)
    last_day = monthrange(year, month)[1]
    first = date(year, month, 1)
    last = date(year, month, last_day)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="fitlife_{year}_{month:02d}.csv"'
    w = csv.writer(resp)
    w.writerow(["Employee Name", "Date", "Clock-in", "Clock-out", "Break (min)", "Net Hours"])
    for emp in Employee.objects.filter(role="employee").select_related("user"):
        for r in DailyTimeRecord.objects.filter(
            employee=emp, date__gte=first, date__lte=last
        ).order_by("date"):
            w.writerow([
                emp.full_name, r.date.isoformat(),
                r.clock_in.strftime("%H:%M") if r.clock_in else "",
                r.clock_out.strftime("%H:%M") if r.clock_out else "",
                r.break_duration_minutes, r.net_hours,
            ])
    return resp


@login_required
def privacy(request):
    return render(request, "timetracking/privacy.html")
