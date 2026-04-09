"""URL configuration for the one-click web app."""
from django.urls import path

from app import views

urlpatterns = [
    path("", views.home, name="home"),
]
