"""Chat persistence (Phase 1) and backend behavior (Phase 2)."""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from chatbot.context import (
    OPEN_STATUSES,
    build_chat_context,
    build_complaints_context,
)
from chatbot.groq_client import ChatbotGroqTransientError
from chatbot.intents import detect_intent
from chatbot.models import ChatMessage, ChatSession
from complaints.models import Complaint
from customers.models import AccountUsage, CustomerAccount, Payment, ServicePlan
from network.models import NetworkOutage


class ChatbotModelTests(TestCase):
    """Focus: sessions, transcript rows, cascading deletes, and choice validation."""

    def setUp(self) -> None:
        self.user_one = User.objects.create_user(username="chat_user_one", password="testpass123")
        self.user_two = User.objects.create_user(username="chat_user_two", password="testpass123")

    def test_create_session_and_messages_default_chronological_order(self) -> None:
        session = ChatSession.objects.create(user=self.user_one, title="Support")
        m_user = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content="What plan am I on?",
            intent="current_plan",
        )
        m_asst = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="You are on Premium.",
            intent="current_plan",
        )
        ordered = list(session.messages.all())
        self.assertEqual([m.pk for m in ordered], [m_user.pk, m_asst.pk])

    def test_messages_deleted_when_session_cascades(self) -> None:
        session = ChatSession.objects.create(user=self.user_one)
        ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content="Hi")
        self.assertEqual(ChatMessage.objects.count(), 1)
        session.delete()
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_invalid_role_rejected_on_full_clean(self) -> None:
        session = ChatSession.objects.create(user=self.user_one)
        bad = ChatMessage(session=session, role="bogus", content="test")
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_sessions_default_order_is_most_recently_updated_first(self) -> None:
        older = ChatSession.objects.create(user=self.user_one, title="Older")
        ChatSession.objects.filter(pk=older.pk).update(updated_at=timezone.now() - timedelta(days=5))
        newer = ChatSession.objects.create(user=self.user_one, title="Newer")
        sessions = list(ChatSession.objects.filter(user=self.user_one))
        self.assertEqual(sessions[0].pk, newer.pk)
        self.assertEqual(sessions[-1].pk, older.pk)

    def test_user_sessions_isolated_between_users(self) -> None:
        ChatSession.objects.create(user=self.user_one, title="A")
        ChatSession.objects.create(user=self.user_two, title="B")
        self.assertEqual(ChatSession.objects.filter(user=self.user_one).count(), 1)
        self.assertEqual(ChatSession.objects.filter(user=self.user_two).count(), 1)


class ChatbotPhase2Helpers(TestCase):
    def setUp(self) -> None:
        self.plan = ServicePlan.objects.create(
            name="PlanA",
            monthly_price=Decimal("25.00"),
            data_allowance_gb=Decimal("10.00"),
            call_minutes=100,
            sms_allowance=50,
        )

        self.cust_u1 = User.objects.create_user(username="cb_cust_one", password="pass")
        UserProfile.objects.create(user=self.cust_u1, role=UserProfile.Role.CUSTOMER, region="Kingston")
        self.acct_one = CustomerAccount.objects.create(
            user=self.cust_u1,
            account_number="ACC-CHAT-ONE",
            service_plan=self.plan,
            current_balance=Decimal("12.34"),
            region="Kingston",
        )

        today_first = timezone.now().date().replace(day=1)
        last_dom = monthrange(today_first.year, today_first.month)[1]
        period_end = today_first.replace(day=last_dom)

        AccountUsage.objects.create(
            account=self.acct_one,
            period_start=today_first,
            period_end=period_end,
            data_used_gb=Decimal("5.60"),
            minutes_used=20,
            sms_used=10,
        )
        Payment.objects.create(
            account=self.acct_one,
            amount=Decimal("44.44"),
            paid_at=timezone.now() - timedelta(days=2),
            reference="PAY-CHAT-ONE",
        )
        Complaint.objects.create(
            reference="CMP-CHAT-O1",
            customer_account=self.acct_one,
            category=Complaint.Category.NETWORK,
            description="Visible description but should not leak into chat contexts.",
            status=Complaint.Status.OPEN,
        )

        NetworkOutage.objects.create(
            region="Kingston",
            title="Active outage",
            description="Degraded throughput",
            started_at=timezone.now() - timedelta(hours=1),
            estimated_resolution_at=timezone.now() + timedelta(hours=2),
            is_active=True,
        )

        self.cust_u2 = User.objects.create_user(username="cb_cust_two", password="pass")
        UserProfile.objects.create(user=self.cust_u2, role=UserProfile.Role.CUSTOMER, region="Montego Bay")
        self.acct_two = CustomerAccount.objects.create(
            user=self.cust_u2,
            account_number="ACC-CHAT-TWO",
            service_plan=self.plan,
            current_balance=Decimal("1.11"),
            region="Montego Bay",
        )
        Complaint.objects.create(
            reference="CMP-CHAT-O2",
            customer_account=self.acct_two,
            category=Complaint.Category.BILLING,
            description="Someone else's complaint.",
            status=Complaint.Status.OPEN,
        )

        self.agent = User.objects.create_user(username="cb_agent_one", password="pass")
        UserProfile.objects.create(user=self.agent, role=UserProfile.Role.AGENT, region="HQ")


class DetectIntentKeywordTests(ChatbotPhase2Helpers):
    def test_supporting_phrases(self) -> None:
        self.assertEqual(detect_intent("What plan am I currently on?", None), "current_plan")
        self.assertEqual(detect_intent("What is my current account balance?", None), "account_balance")
        self.assertEqual(detect_intent("How much data have I used this month?", None), "data_usage")
        self.assertEqual(detect_intent("Do I have any open complaints?", None), "open_complaints")
        self.assertEqual(detect_intent("When was my last payment made?", None), "last_payment")
        self.assertEqual(
            detect_intent("Are there any active outages in my area?", None),
            "active_outages",
        )

    def test_unsupported_neighbor_question(self) -> None:
        self.assertEqual(detect_intent("What is my neighbor's balance?", None), "unsupported")


class ContextIsolationTests(ChatbotPhase2Helpers):
    def test_complaints_exclude_other_accounts(self) -> None:
        ctx_one = build_complaints_context(account=self.acct_one)
        ctx_two = build_complaints_context(account=self.acct_two)
        refs_one = {c["reference"] for c in ctx_one["complaints"]}
        refs_two = {c["reference"] for c in ctx_two["complaints"]}
        self.assertEqual(refs_one, {"CMP-CHAT-O1"})
        self.assertEqual(refs_two, {"CMP-CHAT-O2"})
        self.assertGreater(len(OPEN_STATUSES), 0)

    def test_open_complaints_context_has_display_labels_without_description_field(self) -> None:
        row = build_complaints_context(account=self.acct_one)["complaints"][0]
        self.assertNotIn("description", row)
        self.assertIn("category", row)
        self.assertIn("Network", row["category"])

    def test_build_chat_router(self) -> None:
        balance = build_chat_context(user=self.cust_u1, intent="account_balance", account=self.acct_one)
        self.assertEqual(balance["intent"], "account_balance")
        self.assertEqual(balance["current_balance"], "12.34")


class ChatbotAccessAndApiTests(ChatbotPhase2Helpers):
    def test_agent_blocked(self) -> None:
        cli = Client()
        cli.force_login(self.agent)
        resp = cli.get(reverse("chatbot:chat_home"))
        self.assertEqual(resp.status_code, 403)

    @override_settings(GROQ_API_KEY="test-key-placeholder")
    @patch("chatbot.views.ask_groq", return_value="You are covered by PlanA.")
    def test_post_message_calls_groq_and_persists(self, mocked_ask_groq: MagicMock) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        home = cli.get(reverse("chatbot:chat_home"))
        self.assertEqual(home.status_code, 200)
        session_pk = ChatSession.objects.get(user=self.cust_u1).pk

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload({"session_id": session_pk, "message": "What plan am I on?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["intent"], "current_plan")
        self.assertEqual(payload["message"], "You are covered by PlanA.")

        msgs = ChatMessage.objects.filter(session_id=session_pk).order_by("created_at")
        self.assertEqual(msgs.count(), 2)
        self.assertEqual(msgs.filter(role=ChatMessage.Role.ASSISTANT).count(), 1)
        mocked_ask_groq.assert_called_once()

    @override_settings(GROQ_API_KEY=None)
    @patch("chatbot.views.ask_groq")
    def test_missing_api_key_returns_friendly_without_groq(self, mocked_ask_groq: MagicMock) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        session_pk = ChatSession.objects.create(user=self.cust_u1).pk

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload({"session_id": session_pk, "message": "What plan am I on?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mocked_ask_groq.assert_not_called()
        self.assertIn("Groq API key", resp.json()["message"])

    @override_settings(GROQ_API_KEY="test-key-placeholder")
    @patch("chatbot.views.ask_groq", side_effect=ChatbotGroqTransientError("boom"))
    def test_upstream_error_saved_as_assistant_turn(self, _mock_groq: MagicMock) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        session_pk = ChatSession.objects.create(user=self.cust_u1).pk

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload({"session_id": session_pk, "message": "What plan am I on?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("temporarily unavailable", resp.json()["message"].lower())
        self.assertEqual(ChatMessage.objects.filter(session_id=session_pk).count(), 2)

    @override_settings(GROQ_API_KEY="test-key-placeholder")
    @patch("chatbot.views.ask_groq")
    def test_unsupported_question_skips_groq(self, mocked_ask_groq: MagicMock) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        session_pk = ChatSession.objects.create(user=self.cust_u1).pk

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload(
                {
                    "session_id": session_pk,
                    "message": "Guess my cousin's roaming charges.",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mocked_ask_groq.assert_not_called()
        self.assertEqual(resp.json()["intent"], "unsupported")

    def test_other_user_session_not_accessible(self) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        foreign_session = ChatSession.objects.create(user=self.cust_u2)

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload({"session_id": foreign_session.pk, "message": "Hello"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_new_session_creates_blank_transcript_owner(self) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        ChatSession.objects.create(user=self.cust_u1)

        resp = cli.post(reverse("chatbot:new_session"), data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(ChatSession.objects.filter(user=self.cust_u1).count(), 2)


def json_payload(obj: dict) -> str:
    return json.dumps(obj)