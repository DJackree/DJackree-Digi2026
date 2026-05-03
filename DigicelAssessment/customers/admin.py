"""Admin screens for service plans, accounts, usage rows, and payments."""

from django.contrib import admin

from .models import AccountUsage, CustomerAccount, Payment, ServicePlan


@admin.register(ServicePlan)
class ServicePlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monthly_price",
        "data_allowance_gb",
        "call_minutes",
        "sms_allowance",
        "created_at",
    )
    search_fields = ("name",)


@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = (
        "account_number",
        "user",
        "service_plan",
        "current_balance",
        "region",
        "updated_at",
    )
    list_filter = ("service_plan", "region")
    search_fields = ("account_number", "user__username")
    autocomplete_fields = ("user", "service_plan")


@admin.register(AccountUsage)
class AccountUsageAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "period_start",
        "period_end",
        "data_used_gb",
        "minutes_used",
        "sms_used",
    )
    list_filter = ("period_start", "period_end")
    search_fields = ("account__account_number",)
    autocomplete_fields = ("account",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "account", "amount", "paid_at", "created_at")
    search_fields = ("reference", "account__account_number")
    autocomplete_fields = ("account",)
