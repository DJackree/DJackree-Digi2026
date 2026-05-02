from django.contrib import admin

from .models import NetworkOutage


@admin.register(NetworkOutage)
class NetworkOutageAdmin(admin.ModelAdmin):
    list_display = (
        "region",
        "title",
        "is_active",
        "started_at",
        "estimated_resolution_at",
        "created_at",
    )
    list_filter = ("is_active", "region", "started_at")
    search_fields = ("region", "title", "description")
    date_hierarchy = "started_at"
