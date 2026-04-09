from django.contrib import admin

from .models import AuditLog, Employee, MonthLock, MonthReview, TimeEntry


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "role", "target_hours", "gdpr_consent")
    list_filter = ("role", "department")


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "start_time", "end_time", "net_hours")
    list_filter = ("employee", "date")
    date_hierarchy = "date"


@admin.register(MonthLock)
class MonthLockAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "locked_by", "locked_at")


@admin.register(MonthReview)
class MonthReviewAdmin(admin.ModelAdmin):
    list_display = ("employee", "year", "month", "reviewed_by", "reviewed_at")
    list_filter = ("year", "month")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action")
    list_filter = ("user",)
    search_fields = ("action",)
