"""Django admin registrations for complaints and audit tables.

Lets operations staff browse tickets without writing SQL.
"""

from django.contrib import admin

from .models import Complaint, ComplaintNote, ComplaintStatusHistory


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "customer_account",
        "category",
        "status",
        "assigned_agent",
        "resolved_at",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = (
        "reference",
        "description",
        "customer_account__account_number",
        "customer_account__user__username",
        "assigned_agent__username",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("customer_account", "assigned_agent")
    readonly_fields = ("reference", "created_at", "updated_at")


@admin.register(ComplaintNote)
class ComplaintNoteAdmin(admin.ModelAdmin):
    list_display = ("complaint", "author", "is_internal", "created_at")
    list_filter = ("is_internal", "created_at")
    search_fields = ("body", "complaint__reference", "author__username")
    autocomplete_fields = ("complaint", "author")
    date_hierarchy = "created_at"


@admin.register(ComplaintStatusHistory)
class ComplaintStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("complaint", "from_status", "to_status", "changed_by", "created_at")
    list_filter = ("to_status", "created_at")
    search_fields = ("complaint__reference", "note", "changed_by__username")
    autocomplete_fields = ("complaint", "changed_by")
    date_hierarchy = "created_at"
