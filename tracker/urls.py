from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("", views.login_view, name="login_redirect"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Employee
    path("clock/", views.punch_clock_view, name="punch_clock"),

    # Employee API
    path("api/status/", views.api_status, name="api_status"),
    path("api/punch-in/", views.api_punch_in, name="api_punch_in"),
    path("api/break-start/", views.api_break_start, name="api_break_start"),
    path("api/break-end/", views.api_break_end, name="api_break_end"),
    path("api/punch-out/", views.api_punch_out, name="api_punch_out"),
    path("api/submit-correction/", views.api_submit_correction, name="api_submit_correction"),

    # HR
    path("hr/", views.hr_dashboard_view, name="hr_dashboard"),
    path("api/send-reminder/", views.api_send_reminder, name="api_send_reminder"),
    path("api/acknowledge/", views.api_acknowledge, name="api_acknowledge"),
    path("hr/csv/", views.csv_export, name="csv_export"),

    # Access denied
    path("access-denied/", views.access_denied_view, name="access_denied"),
]
