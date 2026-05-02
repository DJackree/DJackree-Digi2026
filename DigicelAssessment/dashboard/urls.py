from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path(
        "admin-portal/dashboard/",
        views.admin_dashboard,
        name="admin_dashboard",
    ),
]
