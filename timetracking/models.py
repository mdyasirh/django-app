from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models


class Employee(models.Model):
    ROLE_CHOICES = [("employee", "Employee"), ("hr", "HR")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee"
    )
    department = models.CharField(max_length=100)
    target_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("160.00")
    )
    pin = models.CharField(max_length=4, default="1234")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="employee")

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return f"{self.full_name} ({self.department})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_hr(self):
        return self.role == "hr"


class DailyTimeRecord(models.Model):
    STATUS_WORKING = "working"
    STATUS_ON_BREAK = "on_break"
    STATUS_CLOCKED_OUT = "clocked_out"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_CHOICES = [
        (STATUS_WORKING, "Working"),
        (STATUS_ON_BREAK, "On break"),
        (STATUS_CLOCKED_OUT, "Clocked out"),
        (STATUS_INCOMPLETE, "Incomplete"),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="records"
    )
    date = models.DateField()
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_WORKING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["employee", "date"]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.full_name} — {self.date} ({self.status})"

    @property
    def break_duration_minutes(self):
        if not self.break_start or not self.break_end:
            return 0
        start = datetime.combine(self.date, self.break_start)
        end = datetime.combine(self.date, self.break_end)
        delta = (end - start).total_seconds() / 60
        return max(int(delta), 0)

    @property
    def net_hours(self):
        if not self.clock_in or not self.clock_out:
            return Decimal("0.00")
        start = datetime.combine(self.date, self.clock_in)
        end = datetime.combine(self.date, self.clock_out)
        minutes = (end - start).total_seconds() / 60 - self.break_duration_minutes
        if minutes < 0:
            minutes = 0
        return (Decimal(str(minutes)) / Decimal("60")).quantize(Decimal("0.01"))


class CorrectionRequest(models.Model):
    entry = models.ForeignKey(
        DailyTimeRecord, on_delete=models.CASCADE, related_name="corrections"
    )
    proposed_clock_out = models.TimeField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Correction for {self.entry} → {self.proposed_clock_out}"


class HRReview(models.Model):
    STATUS_PENDING = "pending"
    STATUS_REMINDER_SENT = "reminder_sent"
    STATUS_REVIEWED = "reviewed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_REMINDER_SENT, "Reminder sent"),
        (STATUS_REVIEWED, "Reviewed"),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="reviews"
    )
    month = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    reminder_message = models.TextField(blank=True)
    reminder_seen = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["employee", "year", "month"]

    def __str__(self):
        return f"{self.employee.full_name} {self.year}-{self.month:02d} ({self.status})"
