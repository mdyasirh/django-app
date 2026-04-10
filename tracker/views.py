import csv
import datetime
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import CorrectionRequest, DailyTimeRecord, EmployeeProfile, HRReview


# ── Helpers ──────────────────────────────────────────────────────────

def is_hr(user):
    return user.groups.filter(name="HR").exists()


def _today():
    return timezone.localdate()


def _now():
    return timezone.now()


def _get_or_create_record(profile):
    record, _ = DailyTimeRecord.objects.get_or_create(
        employee=profile,
        date=_today(),
        defaults={"status": "WORKING"},
    )
    return record


# ── Authentication ───────────────────────────────────────────────────

def login_view(request):
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        pin = request.POST.get("pin", "")
        # Authenticate using PIN as password
        user = authenticate(request, username=username, password=pin)
        if user is not None:
            login(request, user)
            if is_hr(user):
                return redirect("hr_dashboard")
            return redirect("punch_clock")
        error = "Invalid credentials."
    return render(request, "login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


# ── Employee Punch Clock Page ────────────────────────────────────────

@login_required
def punch_clock_view(request):
    profile = request.user.employeeprofile
    record = _get_or_create_record(profile)

    # Weekly records (last 7 days)
    week_start = _today() - datetime.timedelta(days=6)
    weekly_records = DailyTimeRecord.objects.filter(
        employee=profile, date__gte=week_start
    ).order_by("date")

    return render(request, "punch_clock.html", {
        "record": record,
        "weekly_records": weekly_records,
        "profile": profile,
    })


# ── Employee Status API ─────────────────────────────────────────────

@login_required
def api_status(request):
    profile = request.user.employeeprofile
    record = _get_or_create_record(profile)
    return JsonResponse({
        "status": record.status,
        "clock_in": record.clock_in.isoformat() if record.clock_in else None,
        "clock_out": record.clock_out.isoformat() if record.clock_out else None,
        "break_start": record.break_start.isoformat() if record.break_start else None,
        "total_break_minutes": record.total_break_minutes,
        "net_hours": record.net_hours(),
    })


# ── Employee AJAX Endpoints ─────────────────────────────────────────

@login_required
@require_POST
def api_punch_in(request):
    profile = request.user.employeeprofile
    record = _get_or_create_record(profile)
    if record.clock_in is not None:
        return JsonResponse({"ok": False, "error": "Already clocked in today."})
    record.clock_in = _now()
    record.status = "WORKING"
    record.save()
    return JsonResponse({"ok": True, "status": record.status})


@login_required
@require_POST
def api_break_start(request):
    profile = request.user.employeeprofile
    record = _get_or_create_record(profile)
    if record.status != "WORKING":
        return JsonResponse({"ok": False, "error": "Not currently working."})
    record.break_start = _now()
    record.status = "ON_BREAK"
    record.save()
    return JsonResponse({"ok": True, "status": record.status})


@login_required
@require_POST
def api_break_end(request):
    profile = request.user.employeeprofile
    record = _get_or_create_record(profile)
    if record.status != "ON_BREAK":
        return JsonResponse({"ok": False, "error": "Not on break."})
    if record.break_start:
        elapsed = (_now() - record.break_start).total_seconds() / 60.0
        record.total_break_minutes += int(elapsed)
    record.break_start = None
    record.status = "WORKING"
    record.save()
    return JsonResponse({"ok": True, "status": record.status})


@login_required
@require_POST
def api_punch_out(request):
    profile = request.user.employeeprofile
    record = _get_or_create_record(profile)
    if record.status == "CLOCKED_OUT":
        return JsonResponse({"ok": False, "error": "Already clocked out."})
    # End break if still on break
    if record.status == "ON_BREAK" and record.break_start:
        elapsed = (_now() - record.break_start).total_seconds() / 60.0
        record.total_break_minutes += int(elapsed)
        record.break_start = None
    record.clock_out = _now()
    record.status = "CLOCKED_OUT"
    record.save()
    return JsonResponse({
        "ok": True,
        "status": record.status,
        "net_hours": record.net_hours(),
    })


# ── Correction Request ──────────────────────────────────────────────

@login_required
@require_POST
def api_submit_correction(request):
    profile = request.user.employeeprofile
    record_id = request.POST.get("record_id")
    proposed_time = request.POST.get("proposed_time")
    if not record_id or not proposed_time:
        return JsonResponse({"ok": False, "error": "Missing data."})
    try:
        record = DailyTimeRecord.objects.get(id=record_id, employee=profile)
    except DailyTimeRecord.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Record not found."})
    hour, minute = proposed_time.split(":")
    CorrectionRequest.objects.create(
        record=record,
        proposed_out_time=datetime.time(int(hour), int(minute)),
    )
    return JsonResponse({"ok": True})


# ── HR Dashboard ─────────────────────────────────────────────────────

@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
def hr_dashboard_view(request):
    today = _today()
    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))

    employees = EmployeeProfile.objects.select_related("user").all()
    data = []

    for emp in employees:
        records = DailyTimeRecord.objects.filter(
            employee=emp, date__month=month, date__year=year
        ).order_by("date")

        actual = sum(r.net_hours() for r in records)
        target = float(emp.target_hours_per_month)
        delta = round(actual - target, 2)

        review, _ = HRReview.objects.get_or_create(
            employee=emp, month=month, year=year,
        )

        data.append({
            "employee": emp,
            "target": target,
            "actual": round(actual, 2),
            "delta": delta,
            "records": records,
            "review": review,
        })

    return render(request, "hr_dashboard.html", {
        "data": data,
        "month": month,
        "year": year,
    })


# ── HR Action Endpoints ─────────────────────────────────────────────

@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
@require_POST
def api_send_reminder(request):
    review_id = request.POST.get("review_id")
    if not review_id:
        return JsonResponse({"ok": False, "error": "Missing review_id."})
    try:
        review = HRReview.objects.get(id=review_id)
    except HRReview.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Review not found."})
    review.status = "REMINDER_SENT"
    review.save()
    return JsonResponse({"ok": True, "status": review.status})


@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
@require_POST
def api_acknowledge(request):
    review_id = request.POST.get("review_id")
    if not review_id:
        return JsonResponse({"ok": False, "error": "Missing review_id."})
    try:
        review = HRReview.objects.get(id=review_id)
    except HRReview.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Review not found."})
    review.status = "REVIEWED"
    review.save()
    return JsonResponse({"ok": True, "status": review.status})


# ── CSV Export ───────────────────────────────────────────────────────

@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
def csv_export(request):
    month = int(request.GET.get("month", _today().month))
    year = int(request.GET.get("year", _today().year))

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="time_records_{year}_{month:02d}.csv"'

    writer = csv.writer(response)
    writer.writerow(["Employee", "Date", "Clock-in", "Clock-out", "Break(min)", "Net Hours"])

    records = DailyTimeRecord.objects.filter(
        date__month=month, date__year=year
    ).select_related("employee__user").order_by("employee__user__last_name", "date")

    for r in records:
        writer.writerow([
            r.employee.user.get_full_name() or r.employee.user.username,
            r.date.isoformat(),
            r.clock_in.strftime("%H:%M") if r.clock_in else "",
            r.clock_out.strftime("%H:%M") if r.clock_out else "",
            r.total_break_minutes,
            r.net_hours(),
        ])

    return response


# ── Access Denied ────────────────────────────────────────────────────

def access_denied_view(request):
    return render(request, "access_denied.html", status=403)
