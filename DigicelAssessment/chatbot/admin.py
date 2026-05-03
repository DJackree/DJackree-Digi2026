"""Admin list/search for chat sessions (mostly for support debugging)."""

from django.contrib import admin

from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "user__username", "user__email")
    autocomplete_fields = ("user",)
    date_hierarchy = "updated_at"
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "intent", "created_at")
    list_filter = ("role", "intent", "created_at")
    search_fields = ("content", "intent", "session__title", "session__user__username")
    autocomplete_fields = ("session",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
