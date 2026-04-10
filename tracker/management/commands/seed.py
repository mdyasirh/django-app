import datetime
import random

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import DailyTimeRecord, EmployeeProfile


class Command(BaseCommand):
    help = "Seed the database with demo users and time records."

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        # ── Groups ───────────────────────────────────────────────
        hr_group, _ = Group.objects.get_or_create(name="HR")

        # ── Users & Profiles ─────────────────────────────────────
        employees_data = [
            {"username": "lisa", "first": "Lisa", "last": "Müller", "pin": "1111", "dept": "Fitness"},
            {"username": "tom", "first": "Tom", "last": "Fischer", "pin": "2222", "dept": "Fitness"},
            {"username": "klara", "first": "Klara", "last": "Neumann", "pin": "3333", "dept": "Wellness"},
            {"username": "max", "first": "Max", "last": "Bauer", "pin": "4444", "dept": "Reception"},
            {"username": "anna", "first": "Anna", "last": "Schulz", "pin": "5555", "dept": "Fitness"},
        ]

        profiles = []
        for emp in employees_data:
            user, created = User.objects.get_or_create(
                username=emp["username"],
                defaults={
                    "first_name": emp["first"],
                    "last_name": emp["last"],
                },
            )
            user.set_password(emp["pin"])
            user.save()
            profile, _ = EmployeeProfile.objects.get_or_create(
                user=user,
                defaults={
                    "pin": emp["pin"],
                    "department": emp["dept"],
                    "target_hours_per_month": 160.0,
                },
            )
            profiles.append((emp["username"], profile))
            self.stdout.write(f"  Created employee: {user.get_full_name()}")

        # HR user
        hr_user, _ = User.objects.get_or_create(
            username="hr",
            defaults={"first_name": "HR", "last_name": "Manager"},
        )
        hr_user.set_password("9999")
        hr_user.save()
        hr_user.groups.add(hr_group)
        EmployeeProfile.objects.get_or_create(
            user=hr_user,
            defaults={"pin": "9999", "department": "Management", "target_hours_per_month": 160.0},
        )
        self.stdout.write("  Created HR user: hr")

        # ── Time Records ─────────────────────────────────────────
        today = timezone.localdate()
        tz = timezone.get_current_timezone()

        for username, profile in profiles:
            for day_offset in range(20, 0, -1):
                day = today - datetime.timedelta(days=day_offset)
                # Skip weekends
                if day.weekday() >= 5:
                    continue

                # Tom Fischer: skip some days to create a deficit > 5 hours
                if username == "tom" and day_offset in (2, 4, 6, 8, 10):
                    continue

                # Klara Neumann: work longer days to create overtime > 5 hours
                if username == "klara":
                    start_hour = 7
                    end_hour = 18
                    break_min = 30
                else:
                    start_hour = random.randint(7, 9)
                    end_hour = random.randint(16, 18)
                    break_min = random.choice([30, 45, 60])

                clock_in = timezone.make_aware(
                    datetime.datetime(day.year, day.month, day.day, start_hour, random.randint(0, 15)),
                    tz,
                )
                clock_out = timezone.make_aware(
                    datetime.datetime(day.year, day.month, day.day, end_hour, random.randint(0, 30)),
                    tz,
                )

                # Tom: leave one record without clock_out (MISSING_CLOCKOUT)
                if username == "tom" and day_offset == 3:
                    DailyTimeRecord.objects.update_or_create(
                        employee=profile,
                        date=day,
                        defaults={
                            "clock_in": clock_in,
                            "clock_out": None,
                            "total_break_minutes": 0,
                            "status": "MISSING_CLOCKOUT",
                        },
                    )
                    continue

                DailyTimeRecord.objects.update_or_create(
                    employee=profile,
                    date=day,
                    defaults={
                        "clock_in": clock_in,
                        "clock_out": clock_out,
                        "total_break_minutes": break_min,
                        "status": "CLOCKED_OUT",
                    },
                )

        self.stdout.write(self.style.SUCCESS("Seed complete!"))
