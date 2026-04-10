from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", auth_views.LoginView.as_view(
        template_name="timetracking/login.html",
        redirect_authenticated_user=True,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
    path("employee/", views.employee_dashboard, name="employee_dashboard"),
    path("clock-in/", views.clock_in, name="clock_in"),
    path("break/", views.break_start, name="break_start"),
    path("resume/", views.resume, name="resume"),
    path("clock-out/", views.clock_out, name="clock_out"),
    path("correction/<int:record_id>/", views.correction, name="correction"),
    path("reminder/dismiss/<int:review_id>/", views.dismiss_reminder, name="dismiss_reminder"),
    path("hr/", views.hr_dashboard, name="hr_dashboard"),
    path("hr/acknowledge/<int:employee_id>/", views.hr_acknowledge, name="hr_acknowledge"),
    path("hr/reminder/<int:employee_id>/", views.hr_send_reminder, name="hr_reminder"),
    path("hr/export/", views.hr_export_csv, name="hr_export"),
    path("privacy/", views.privacy, name="privacy"),
]
