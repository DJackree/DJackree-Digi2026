"""Foundation seed data for Phase 1 (users, profiles, plans, accounts, usage, payments)."""

from __future__ import annotations

import calendar
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from customers.models import AccountUsage, CustomerAccount, Payment, ServicePlan


PLANS = [
    {
        "name": "Basic",
        "monthly_price": Decimal("25.00"),
        "data_allowance_gb": Decimal("5.00"),
        "call_minutes": 300,
        "sms_allowance": 100,
    },
    {
        "name": "Standard",
        "monthly_price": Decimal("40.00"),
        "data_allowance_gb": Decimal("20.00"),
        "call_minutes": 1000,
        "sms_allowance": 500,
    },
    {
        "name": "Premium",
        "monthly_price": Decimal("55.00"),
        "data_allowance_gb": Decimal("50.00"),
        "call_minutes": 2000,
        "sms_allowance": 1000,
    },
]

CUSTOMER_SEED = [
    ("customer1", "Kingston"),
    ("customer2", "Montego Bay"),
    ("customer3", "Spanish Town"),
    ("customer4", "Portmore"),
    ("customer5", "Ocho Rios"),
]

DEFAULT_PASSWORD_ADMIN = "AdminPass123!"
DEFAULT_PASSWORD_AGENT = "AgentPass123!"
DEFAULT_PASSWORD_CUSTOMER = "CustomerPass123!"


class Command(BaseCommand):
    help = "Seed demo users and customer foundation data (--if-empty skips when DB has users)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="If any user exists, skip seeding (idempotent Docker startup behavior).",
        )

    def handle(self, *args, **options) -> None:
        if_empty: bool = options["if_empty"]

        if User.objects.exists():
            if if_empty:
                self.stdout.write(self.style.WARNING("Skipping seed_data: database not empty."))
                return
            raise CommandError(
                "Database not empty. Re-run with --if-empty after reset, "
                "or clear users before seeding."
            )

        today = timezone.now().date()
        period_start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        period_end = today.replace(day=last_day)

        with transaction.atomic():
            plans = []
            for p in PLANS:
                plan, _ = ServicePlan.objects.get_or_create(
                    name=p["name"],
                    defaults={
                        "monthly_price": p["monthly_price"],
                        "data_allowance_gb": p["data_allowance_gb"],
                        "call_minutes": p["call_minutes"],
                        "sms_allowance": p["sms_allowance"],
                    },
                )
                plans.append(plan)

            admin_user = User.objects.create_user(
                username="admin",
                email="admin@example.com",
                password=DEFAULT_PASSWORD_ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            UserProfile.objects.create(
                user=admin_user,
                role=UserProfile.Role.ADMIN,
                region="HQ",
            )

            for i in range(1, 4):
                u = User.objects.create_user(
                    username=f"agent{i}",
                    email=f"agent{i}@example.com",
                    password=DEFAULT_PASSWORD_AGENT,
                )
                UserProfile.objects.create(
                    user=u,
                    role=UserProfile.Role.AGENT,
                    region="Regional",
                )

            customers_users: list[tuple[User, str]] = []
            for username, region in CUSTOMER_SEED:
                u = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password=DEFAULT_PASSWORD_CUSTOMER,
                )
                UserProfile.objects.create(
                    user=u,
                    role=UserProfile.Role.CUSTOMER,
                    region=region,
                )
                customers_users.append((u, region))

            for idx, (user, region) in enumerate(customers_users):
                acct_no = f"ACC-2026-{idx + 1:04d}"
                plan = plans[idx % len(plans)]
                balance = Decimal("10.00") + Decimal(idx * 5)
                account = CustomerAccount.objects.create(
                    user=user,
                    account_number=acct_no,
                    service_plan=plan,
                    current_balance=balance,
                    region=region,
                )
                AccountUsage.objects.create(
                    account=account,
                    period_start=period_start,
                    period_end=period_end,
                    data_used_gb=Decimal("8.40") + Decimal(idx),
                    minutes_used=120 + idx * 10,
                    sms_used=30 + idx * 5,
                )
                Payment.objects.create(
                    account=account,
                    amount=Decimal("55.00") - Decimal(idx % 3),
                    paid_at=timezone.now() - timedelta(days=7 + idx),
                    reference=f"PAY-{acct_no}-{idx}",
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded foundation: admin + 3 agents + 5 customers, plans, accounts, usage, payments."
            )
        )
