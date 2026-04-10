from django.contrib import admin
from .models import EmployeeProfile, DailyTimeRecord, CorrectionRequest, HRReview


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "pin", "department", "target_hours_per_month")


@admin.register(DailyTimeRecord)
class DailyTimeRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "clock_in", "clock_out", "status", "total_break_minutes")
    list_filter = ("status", "date")


@admin.register(CorrectionRequest)
class CorrectionRequestAdmin(admin.ModelAdmin):
    list_display = ("record", "proposed_out_time", "status")


@admin.register(HRReview)
class HRReviewAdmin(admin.ModelAdmin):
    list_display = ("employee", "month", "year", "status")
