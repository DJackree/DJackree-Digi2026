"""Fill the database with demo people, accounts, tickets, and outages.

Intended for first-time setup: Docker calls ``seed_data --if-empty`` so reviewers
see a realistic portal without manual SQL. Re-running on a non-empty database is
skipped on purpose to avoid duplicate accounts.
"""

from __future__ import annotations

import calendar
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from complaints.models import Complaint, ComplaintNote, ComplaintStatusHistory
from customers.models import AccountUsage, CustomerAccount, Payment, ServicePlan
from network.models import NetworkOutage


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


def _seed_complaints_and_outages(
    *,
    admin_user: User,
    agent_users: dict[str, User],
    accounts_by_username: dict[str, CustomerAccount],
) -> None:
    """Create demo complaints, history, notes, and outages (single-shot seed)."""
    year = timezone.now().year
    now = timezone.now()

    def chain_to_statuses(final: str) -> list[str]:
        """Minimal forward chains ending at final status."""
        if final == Complaint.Status.OPEN:
            return [Complaint.Status.OPEN]
        if final == Complaint.Status.IN_PROGRESS:
            return [Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS]
        if final == Complaint.Status.ESCALATED:
            return [
                Complaint.Status.OPEN,
                Complaint.Status.IN_PROGRESS,
                Complaint.Status.ESCALATED,
            ]
        if final == Complaint.Status.RESOLVED:
            return [
                Complaint.Status.OPEN,
                Complaint.Status.IN_PROGRESS,
                Complaint.Status.RESOLVED,
            ]
        if final == Complaint.Status.CLOSED:
            return [
                Complaint.Status.OPEN,
                Complaint.Status.IN_PROGRESS,
                Complaint.Status.ESCALATED,
                Complaint.Status.RESOLVED,
                Complaint.Status.CLOSED,
            ]
        raise ValueError(f"Unknown final status: {final}")

    specs: list[dict] = [
        {
            "ref": f"CMP-{year}-0001",
            "customer": "customer1",
            "category": Complaint.Category.BILLING,
            "status": Complaint.Status.OPEN,
            "agent": None,
            "days_ago": 2,
            "description": "Incorrect charge on last month's bill.",
            "escalation_reason": "",
            "add_note": False,
        },
        {
            "ref": f"CMP-{year}-0002",
            "customer": "customer2",
            "category": Complaint.Category.NETWORK,
            "status": Complaint.Status.OPEN,
            "agent": "agent1",
            "days_ago": 8,
            "description": "Mobile data unavailable intermittently for several days.",
            "escalation_reason": "",
            "add_note": True,
        },
        {
            "ref": f"CMP-{year}-0003",
            "customer": "customer3",
            "category": Complaint.Category.DEVICE,
            "status": Complaint.Status.IN_PROGRESS,
            "agent": "agent2",
            "days_ago": 10,
            "description": "SIM not detected after replacement handset.",
            "escalation_reason": "",
            "add_note": True,
        },
        {
            "ref": f"CMP-{year}-0004",
            "customer": "customer4",
            "category": Complaint.Category.ROAMING,
            "status": Complaint.Status.IN_PROGRESS,
            "agent": "agent3",
            "days_ago": 1,
            "description": "Roaming package not activating abroad.",
            "escalation_reason": "",
            "add_note": False,
        },
        {
            "ref": f"CMP-{year}-0005",
            "customer": "customer5",
            "category": Complaint.Category.NETWORK,
            "status": Complaint.Status.ESCALATED,
            "agent": "agent1",
            "days_ago": 3,
            "description": "Tower outage suspected near home address.",
            "escalation_reason": "Correlated with wider regional routing issue.",
            "add_note": True,
        },
        {
            "ref": f"CMP-{year}-0006",
            "customer": "customer1",
            "category": Complaint.Category.OTHER,
            "status": Complaint.Status.ESCALATED,
            "agent": None,
            "days_ago": 4,
            "description": "General account enquiry escalated for specialist review.",
            "escalation_reason": "Requires billing policy exception.",
            "add_note": False,
        },
        {
            "ref": f"CMP-{year}-0007",
            "customer": "customer2",
            "category": Complaint.Category.BILLING,
            "status": Complaint.Status.RESOLVED,
            "agent": "agent2",
            "days_ago": 14,
            "description": "Duplicate payment showing on statement.",
            "escalation_reason": "",
            "add_note": True,
        },
        {
            "ref": f"CMP-{year}-0008",
            "customer": "customer3",
            "category": Complaint.Category.DEVICE,
            "status": Complaint.Status.RESOLVED,
            "agent": "agent3",
            "days_ago": 5,
            "description": "VoLTE toggle missing after OS update.",
            "escalation_reason": "",
            "add_note": False,
        },
        {
            "ref": f"CMP-{year}-0009",
            "customer": "customer4",
            "category": Complaint.Category.NETWORK,
            "status": Complaint.Status.CLOSED,
            "agent": "agent1",
            "days_ago": 20,
            "description": "Dropped calls on highway corridor.",
            "escalation_reason": "",
            "add_note": True,
        },
        {
            "ref": f"CMP-{year}-0010",
            "customer": "customer5",
            "category": Complaint.Category.ROAMING,
            "status": Complaint.Status.CLOSED,
            "agent": "agent2",
            "days_ago": 25,
            "description": "Incorrect roaming rates applied while traveling.",
            "escalation_reason": "",
            "add_note": False,
        },
        {
            "ref": f"CMP-{year}-0011",
            "customer": "customer1",
            "category": Complaint.Category.OTHER,
            "status": Complaint.Status.OPEN,
            "agent": "agent3",
            "days_ago": 1,
            "description": "Request callback about plan upgrade options.",
            "escalation_reason": "",
            "add_note": True,
        },
        {
            "ref": f"CMP-{year}-0012",
            "customer": "customer2",
            "category": Complaint.Category.BILLING,
            "status": Complaint.Status.IN_PROGRESS,
            "agent": None,
            "days_ago": 2,
            "description": "Auto-pay failed twice this month.",
            "escalation_reason": "",
            "add_note": False,
        },
        {
            "ref": f"CMP-{year}-0013",
            "customer": "customer3",
            "category": Complaint.Category.DEVICE,
            "status": Complaint.Status.ESCALATED,
            "agent": "agent2",
            "days_ago": 6,
            "description": "Device replacement delayed beyond SLA.",
            "escalation_reason": "Warehouse stock discrepancy.",
            "add_note": True,
        },
        {
            "ref": f"CMP-{year}-0014",
            "customer": "customer4",
            "category": Complaint.Category.ROAMING,
            "status": Complaint.Status.RESOLVED,
            "agent": None,
            "days_ago": 12,
            "description": "Data roaming cap hit unexpectedly.",
            "escalation_reason": "",
            "add_note": False,
        },
        {
            "ref": f"CMP-{year}-0015",
            "customer": "customer5",
            "category": Complaint.Category.OTHER,
            "status": Complaint.Status.CLOSED,
            "agent": "agent3",
            "days_ago": 18,
            "description": "Port-out request completed with delays.",
            "escalation_reason": "",
            "add_note": False,
        },
    ]

    for spec in specs:
        account = accounts_by_username[spec["customer"]]
        agent_user = agent_users[spec["agent"]] if spec["agent"] else None
        created_at = now - timedelta(days=int(spec["days_ago"]))
        status_chain = chain_to_statuses(spec["status"])

        complaint = Complaint(
            reference=spec["ref"],
            customer_account=account,
            category=spec["category"],
            description=spec["description"],
            status=spec["status"],
            assigned_agent=agent_user,
            escalation_reason=spec.get("escalation_reason", ""),
        )
        if spec["status"] in (Complaint.Status.RESOLVED, Complaint.Status.CLOSED):
            complaint.resolved_at = created_at + timedelta(days=2)
        complaint.save()
        Complaint.objects.filter(pk=complaint.pk).update(created_at=created_at)

        prev = ""
        for step_i, to_status in enumerate(status_chain):
            actor = agent_user or admin_user
            hist = ComplaintStatusHistory.objects.create(
                complaint=complaint,
                changed_by=actor,
                from_status=prev,
                to_status=to_status,
                note="Seeded transition." if step_i else "Complaint opened.",
            )
            ComplaintStatusHistory.objects.filter(pk=hist.pk).update(
                created_at=created_at + timedelta(minutes=step_i + 1)
            )
            prev = to_status

        if spec.get("add_note") and agent_user:
            note = ComplaintNote.objects.create(
                complaint=complaint,
                author=agent_user,
                body="Internal note: customer contacted; troubleshooting in progress.",
                is_internal=True,
            )
            ComplaintNote.objects.filter(pk=note.pk).update(
                created_at=created_at + timedelta(hours=2)
            )

    NetworkOutage.objects.create(
        region="Kingston",
        title="Backbone maintenance — Kingston metro",
        description="Fiber splice work affecting peak-hour throughput in Kingston.",
        started_at=now - timedelta(hours=3),
        estimated_resolution_at=now + timedelta(hours=5),
        is_active=True,
    )
    NetworkOutage.objects.create(
        region="Montego Bay",
        title="Resolved: cable damage near airport",
        description="Third-party construction damaged a feeder cable; traffic rerouted.",
        started_at=now - timedelta(days=3),
        estimated_resolution_at=now - timedelta(days=2),
        is_active=False,
    )


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

            agent_users = {f"agent{i}": User.objects.get(username=f"agent{i}") for i in range(1, 4)}
            accounts_by_username: dict[str, CustomerAccount] = {}

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
                accounts_by_username[user.username] = account
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

            _seed_complaints_and_outages(
                admin_user=admin_user,
                agent_users=agent_users,
                accounts_by_username=accounts_by_username,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded foundation: admin + 3 agents + 5 customers, plans, accounts, usage, payments, "
                "complaints module demo (15 complaints, history, notes, outages)."
            )
        )
