"""Seed demo data for the FitLife Time Tracker."""
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from timetracking.models import Employee, TimeEntry


DEMO_PASSWORD = "fitlife2026"


EMPLOYEES = [
    {
        "username": "lisa.schmidt",
        "first_name": "Lisa",
        "last_name": "Schmidt",
        "email": "lisa.schmidt@fitlife.de",
        "department": "Training",
        "target_hours": Decimal("80.00"),
        "role": "employee",
    },
    {
        "username": "tom.fischer",
        "first_name": "Tom",
        "last_name": "Fischer",
        "email": "tom.fischer@fitlife.de",
        "department": "Training",
        "target_hours": Decimal("160.00"),
        "role": "employee",
    },
    {
        "username": "klara.neumann",
        "first_name": "Klara",
        "last_name": "Neumann",
        "email": "klara.neumann@fitlife.de",
        "department": "Reception",
        "target_hours": Decimal("160.00"),
        "role": "employee",
    },
    {
        "username": "julia.braun",
        "first_name": "Julia",
        "last_name": "Braun",
        "email": "julia.braun@fitlife.de",
        "department": "HR",
        "target_hours": Decimal("160.00"),
        "role": "hr",
    },
]


class Command(BaseCommand):
    help = "Seed demo employees, HR user and sample time entries."

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data…")

        created_users = 0
        for data in EMPLOYEES:
            user, user_created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "email": data["email"],
                },
            )
            if user_created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                created_users += 1
            else:
                # always reset demo password so it is predictable
                user.set_password(DEMO_PASSWORD)
                user.first_name = data["first_name"]
                user.last_name = data["last_name"]
                user.email = data["email"]
                user.save()

            Employee.objects.update_or_create(
                user=user,
                defaults={
                    "department": data["department"],
                    "target_hours": data["target_hours"],
                    "role": data["role"],
                    "gdpr_consent": True,
                    "consent_date": timezone.now(),
                },
            )

        # Also create a superuser for /admin if one doesn't exist
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                "admin", "admin@fitlife.de", DEMO_PASSWORD
            )

        # Build sample time entries for the last ~5 weeks (covers previous + current month)
        today = timezone.localdate()
        start = today - timedelta(days=35)

        patterns = {
            "lisa.schmidt": {
                "weekdays": [0, 1, 2, 3],  # Mon–Thu, part-time
                "start": time(9, 0),
                "end": time(14, 0),
                "break_min": 30,
            },
            "tom.fischer": {
                # full time but with GAPS to create a deficit
                "weekdays": [0, 2, 4],
                "start": time(8, 0),
                "end": time(16, 0),
                "break_min": 45,
            },
            "klara.neumann": {
                # full schedule with overtime to demonstrate surplus
                "weekdays": [0, 1, 2, 3, 4],
                "start": time(8, 30),
                "end": time(18, 30),
                "break_min": 45,
            },
        }

        # wipe old demo entries to keep the seed idempotent
        TimeEntry.objects.filter(
            employee__user__username__in=list(patterns.keys())
        ).delete()

        total_entries = 0
        for username, cfg in patterns.items():
            emp = Employee.objects.get(user__username=username)
            d = start
            while d <= today:
                if d.weekday() in cfg["weekdays"]:
                    TimeEntry.objects.update_or_create(
                        employee=emp,
                        date=d,
                        defaults={
                            "start_time": cfg["start"],
                            "end_time": cfg["end"],
                            "break_duration": timedelta(minutes=cfg["break_min"]),
                        },
                    )
                    total_entries += 1
                d += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Employees: {len(EMPLOYEES)} (new users: {created_users}), "
            f"time entries seeded: {total_entries}."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"\nDemo logins (password: {DEMO_PASSWORD}):"
        ))
        for data in EMPLOYEES:
            self.stdout.write(f"  {data['role']:>8}  {data['username']}")
        self.stdout.write("     admin  admin")
