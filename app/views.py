"""Views for the one-click web app."""
from django.shortcuts import render


def home(request):
    """Render the home page."""
    return render(request, "home.html", {"title": "One-Click Web App"})
