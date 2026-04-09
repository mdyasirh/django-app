from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models


class Employee(models.Model):
    ROLE_CHOICES = [
        ("employee", "Employee"),
        ("hr", "HR"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee",
    )
    department = models.CharField(max_length=100)
    target_hours = models.DecimalField(max_digits=5, decimal_places=2, default=160)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="employee")
    gdpr_consent = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.department})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_hr(self):
        return self.role == "hr"


class TimeEntry(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="entries"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration = models.DurationField(default=timedelta(0))
    net_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["employee", "date"]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.full_name} — {self.date}"

    def save(self, *args, **kwargs):
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        total = (end_dt - start_dt) - self.break_duration
        hours = max(total.total_seconds() / 3600, 0)
        self.net_hours = Decimal(f"{hours:.2f}")
        super().save(*args, **kwargs)


class MonthLock(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    locked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["year", "month"]

    def __str__(self):
        return f"Lock {self.year}-{self.month:02d}"


class MonthReview(models.Model):
    """HR review/acknowledgement of an employee's month."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="reviews"
    )
    year = models.IntegerField()
    month = models.IntegerField()
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    reviewed_at = models.DateTimeField(auto_now=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ["employee", "year", "month"]

    def __str__(self):
        return f"Review {self.employee.full_name} {self.year}-{self.month:02d}"


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} — {self.action}"
