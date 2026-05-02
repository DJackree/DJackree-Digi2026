"""Backend tests for complaints Phase 2."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from complaints.models import Complaint, ComplaintNote, ComplaintStatusHistory
from complaints.services import (
    AGENT_FORWARD_TRANSITIONS,
    assign_complaint,
    change_complaint_status,
    escalate_complaint,
    get_sla_breaches,
)
from dashboard.services import get_dashboard_metrics
from customers.models import CustomerAccount, ServicePlan


class ComplaintPhase2Tests(TestCase):
    def setUp(self) -> None:
        self.plan = ServicePlan.objects.create(
            name="TestPlan",
            monthly_price=Decimal("10.00"),
            data_allowance_gb=Decimal("1.00"),
            call_minutes=100,
            sms_allowance=50,
        )

        self.admin = User.objects.create_user(username="t_admin", password="pass")
        UserProfile.objects.create(user=self.admin, role=UserProfile.Role.ADMIN, region="HQ")

        self.agent = User.objects.create_user(username="t_agent", password="pass")
        UserProfile.objects.create(user=self.agent, role=UserProfile.Role.AGENT, region="R1")

        self.customer_a = User.objects.create_user(username="t_cust_a", password="pass")
        UserProfile.objects.create(user=self.customer_a, role=UserProfile.Role.CUSTOMER, region="Kgn")
        self.account_a = CustomerAccount.objects.create(
            user=self.customer_a,
            account_number="ACC-TST-0001",
            service_plan=self.plan,
            current_balance=Decimal("0.00"),
            region="Kingston",
        )

        self.customer_b = User.objects.create_user(username="t_cust_b", password="pass")
        UserProfile.objects.create(user=self.customer_b, role=UserProfile.Role.CUSTOMER, region="Mb")
        self.account_b = CustomerAccount.objects.create(
            user=self.customer_b,
            account_number="ACC-TST-0002",
            service_plan=self.plan,
            current_balance=Decimal("0.00"),
            region="Montego Bay",
        )

        self.comp_a = Complaint.objects.create(
            reference="CMP-TST-A",
            customer_account=self.account_a,
            category=Complaint.Category.NETWORK,
            description="This is a long enough customer-visible description.",
            status=Complaint.Status.OPEN,
            assigned_agent=self.agent,
        )

        self.comp_b = Complaint.objects.create(
            reference="CMP-TST-B",
            customer_account=self.account_b,
            category=Complaint.Category.BILLING,
            description="Another long enough description for isolation tests.",
            status=Complaint.Status.OPEN,
            assigned_agent=None,
        )

    def test_customer_list_scoped(self) -> None:
        c = Client()
        c.force_login(self.customer_a)
        resp = c.get(reverse("complaints:customer_complaint_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "CMP-TST-A")
        self.assertNotContains(resp, "CMP-TST-B")

    def test_customer_cannot_view_other_detail(self) -> None:
        c = Client()
        c.force_login(self.customer_a)
        resp = c.get(
            reverse("complaints:customer_complaint_detail", kwargs={"reference": "CMP-TST-B"})
        )
        self.assertEqual(resp.status_code, 404)

    def test_customer_create_adds_open_history(self) -> None:
        c = Client()
        c.force_login(self.customer_a)
        url = reverse("complaints:customer_complaint_create")
        resp = c.post(
            url,
            {
                "category": Complaint.Category.DEVICE,
                "description": "Device issue description that is definitely long enough.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Complaint.objects.get(customer_account=self.account_a, category=Complaint.Category.DEVICE)
        self.assertEqual(created.status, Complaint.Status.OPEN)
        self.assertTrue(
            ComplaintStatusHistory.objects.filter(
                complaint=created,
                to_status=Complaint.Status.OPEN,
            ).exists()
        )

    def test_agent_queue_scoped(self) -> None:
        c = Client()
        c.force_login(self.agent)
        resp = c.get(reverse("complaints:agent_complaint_queue"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "CMP-TST-A")
        self.assertNotContains(resp, "CMP-TST-B")

    def test_agent_cannot_skip_forward_transition(self) -> None:
        # OPEN cannot jump to RESOLVED for agents.
        with self.assertRaises(ValidationError):
            change_complaint_status(
                complaint=self.comp_a,
                new_status=Complaint.Status.RESOLVED,
                changed_by=self.agent,
                note="invalid jump",
            )

    def test_agent_forward_transition_allowed(self) -> None:
        change_complaint_status(
            complaint=self.comp_a,
            new_status=Complaint.Status.IN_PROGRESS,
            changed_by=self.agent,
            note="start",
        )
        self.comp_a.refresh_from_db()
        self.assertEqual(self.comp_a.status, Complaint.Status.IN_PROGRESS)

    def test_escalation_requires_reason_and_sets_status(self) -> None:
        self.comp_a.status = Complaint.Status.IN_PROGRESS
        self.comp_a.save(update_fields=["status", "updated_at"])

        escalate_complaint(
            complaint=self.comp_a,
            agent=self.agent,
            reason="Regional routing suspected.",
        )
        self.comp_a.refresh_from_db()
        self.assertEqual(self.comp_a.status, Complaint.Status.ESCALATED)
        self.assertIn("Regional routing suspected.", self.comp_a.escalation_reason)

    def test_assign_complaint_requires_agent_role(self) -> None:
        with self.assertRaises(ValidationError):
            assign_complaint(
                complaint=self.comp_b,
                agent=self.customer_a,
                assigned_by=self.admin,
            )

    def test_assign_complaint_updates_assignment_and_note(self) -> None:
        before_notes = ComplaintNote.objects.filter(complaint=self.comp_b).count()
        assign_complaint(
            complaint=self.comp_b,
            agent=self.agent,
            assigned_by=self.admin,
        )
        self.comp_b.refresh_from_db()
        self.assertEqual(self.comp_b.assigned_agent_id, self.agent.id)
        self.assertEqual(
            ComplaintNote.objects.filter(complaint=self.comp_b).count(),
            before_notes + 1,
        )

    def test_sla_breach_query_excludes_resolved(self) -> None:
        old_open = Complaint.objects.create(
            reference="CMP-TST-OLD",
            customer_account=self.account_a,
            category=Complaint.Category.OTHER,
            description="Old complaint description here long enough.",
            status=Complaint.Status.OPEN,
            assigned_agent=self.agent,
        )
        Complaint.objects.filter(pk=old_open.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        qs = get_sla_breaches()
        self.assertTrue(qs.filter(reference="CMP-TST-OLD").exists())

        change_complaint_status(
            complaint=old_open,
            new_status=Complaint.Status.RESOLVED,
            changed_by=self.admin,
            note="resolved",
        )
        qs2 = get_sla_breaches()
        self.assertFalse(qs2.filter(reference="CMP-TST-OLD").exists())

    def test_dashboard_metrics_keys_and_counts(self) -> None:
        metrics = get_dashboard_metrics()
        self.assertIn("by_status", metrics)
        self.assertIn("by_category", metrics)
        self.assertIn("average_resolution_time", metrics)
        self.assertIn("sla_breaches", metrics)

        total_status = sum(metrics["by_status"].values())
        self.assertEqual(total_status, Complaint.objects.count())


class AgentTransitionMatrixSmokeTests(TestCase):
    def test_agent_matrix_matches_plan(self) -> None:
        self.assertEqual(
            AGENT_FORWARD_TRANSITIONS[Complaint.Status.OPEN],
            [Complaint.Status.IN_PROGRESS],
        )
        self.assertEqual(
            set(AGENT_FORWARD_TRANSITIONS[Complaint.Status.IN_PROGRESS]),
            {Complaint.Status.ESCALATED, Complaint.Status.RESOLVED},
        )
