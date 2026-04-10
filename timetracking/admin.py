from django.contrib import admin
from .models import CorrectionRequest, DailyTimeRecord, Employee, HRReview


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "role", "target_hours", "pin")
    list_filter = ("role", "department")


@admin.register(DailyTimeRecord)
class DailyTimeRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "clock_in", "clock_out", "status")
    list_filter = ("status", "date")
    date_hierarchy = "date"


@admin.register(CorrectionRequest)
class CorrectionRequestAdmin(admin.ModelAdmin):
    list_display = ("entry", "proposed_clock_out", "reviewed", "submitted_at")
    list_filter = ("reviewed",)


@admin.register(HRReview)
class HRReviewAdmin(admin.ModelAdmin):
    list_display = ("employee", "year", "month", "status", "reminder_seen")
    list_filter = ("status", "year", "month")
