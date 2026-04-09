from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="timetracking/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
    path("calendar/", views.weekly_calendar_view, name="weekly_calendar"),
    path("api/save-entry/", views.save_time_entry, name="save_entry"),
    path("api/delete-entry/", views.delete_time_entry, name="delete_entry"),
    path("hr/", views.hr_dashboard, name="hr_dashboard"),
    path("hr/detail/<int:employee_id>/", views.hr_employee_detail, name="hr_detail"),
    path(
        "hr/acknowledge/<int:employee_id>/",
        views.hr_acknowledge,
        name="hr_acknowledge",
    ),
    path(
        "hr/reminder/<int:employee_id>/",
        views.hr_send_reminder,
        name="hr_reminder",
    ),
    path("hr/export/", views.hr_export_csv, name="hr_export"),
    path("privacy/", views.privacy, name="privacy"),
]
