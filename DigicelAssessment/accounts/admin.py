from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "region", "updated_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "region")
    autocomplete_fields = ("user",)


# Enable search for User autocomplete on CustomerAccount and UserProfile admins
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    search_fields = ("username", "email", "first_name", "last_name")
