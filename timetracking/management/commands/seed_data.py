"""Seed demo data — 5 employees + 1 HR + previous-month time records."""
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from timetracking.models import DailyTimeRecord, Employee


EMPLOYEES = [
    ("lisa", "Lisa", "Schmidt", "Training", "1234"),
    ("tom", "Tom", "Fischer", "Training", "1234"),
    ("klara", "Klara", "Neumann", "Reception", "1234"),
    ("max", "Max", "Weber", "Training", "1234"),
    ("anna", "Anna", "M\u00fcller", "Reception", "1234"),
]


class Command(BaseCommand):
    help = "Create demo users and previous-month time records."

    def handle(self, *args, **options):
        # HR user
        hr_user, _ = User.objects.get_or_create(
            username="hr",
            defaults={"first_name": "Julia", "last_name": "Braun",
                       "email": "hr@fitlife.de", "is_staff": True},
        )
        hr_user.set_password("admin123")
        hr_user.save()
        Employee.objects.update_or_create(
            user=hr_user,
            defaults={"department": "HR", "role": "hr", "pin": "0000",
                       "target_hours": Decimal("160.00")},
        )

        # Admin
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@fitlife.de", "admin123")

        emps = {}
        for uname, first, last, dept, pin in EMPLOYEES:
            u, _ = User.objects.get_or_create(
                username=uname,
                defaults={"first_name": first, "last_name": last,
                           "email": f"{uname}@fitlife.de"},
            )
            u.set_password(pin)
            u.save()
            emp, _ = Employee.objects.update_or_create(
                user=u,
                defaults={"department": dept, "role": "employee",
                           "pin": pin, "target_hours": Decimal("160.00")},
            )
            emps[uname] = emp

        # Previous month
        today = timezone.localdate()
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)

        DailyTimeRecord.objects.filter(
            date__gte=first_prev, date__lte=last_prev
        ).delete()

        def mk(emp, d, ci, co, bs=None, be=None, status="clocked_out"):
            DailyTimeRecord.objects.create(
                employee=emp, date=d, clock_in=ci, clock_out=co,
                break_start=bs, break_end=be, status=status,
            )

        d = first_prev
        tom_skip = 0
        weekday_n = 0
        while d <= last_prev:
            if d.weekday() < 5:  # weekday
                weekday_n += 1

                # Lisa — on target, one incomplete day (day 8)
                if weekday_n == 8:
                    DailyTimeRecord.objects.create(
                        employee=emps["lisa"], date=d,
                        clock_in=time(9, 0), status="incomplete",
                    )
                else:
                    mk(emps["lisa"], d, time(9, 0), time(17, 0),
                       time(12, 0), time(12, 30))

                # Tom — deficit (2 missing days)
                if weekday_n in (3, 12):
                    tom_skip += 1
                    # no entry at all
                else:
                    mk(emps["tom"], d, time(9, 0), time(16, 0),
                       time(12, 0), time(12, 30))

                # Klara — overtime
                mk(emps["klara"], d, time(8, 0), time(18, 30),
                   time(12, 0), time(12, 30))

                # Max — normal
                mk(emps["max"], d, time(9, 0), time(17, 30),
                   time(12, 0), time(12, 30))

                # Anna — normal
                mk(emps["anna"], d, time(10, 0), time(18, 0),
                   time(13, 0), time(13, 30))

            d += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(emps)} employees + HR + {weekday_n} days of records."
        ))
        self.stdout.write("Employee login: lisa / tom / klara / max / anna  PIN 1234")
        self.stdout.write("HR login: hr / admin123")
