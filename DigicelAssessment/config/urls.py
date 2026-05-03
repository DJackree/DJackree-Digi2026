"""Root URL configuration: wires every app's routes into one site.

Order can matter when paths overlap; keep more specific apps before catch-alls.
Each ``include()`` pulls in another app's ``urlpatterns``.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("complaints.urls")),
    path("", include("dashboard.urls")),
    path("", include("chatbot.urls")),
]
