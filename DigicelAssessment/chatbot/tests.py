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
    build_merged_chat_context,
    merged_context_has_required_data,
)
from chatbot.groq_client import ChatbotGroqTransientError
from chatbot.intents import (
    DialogueState,
    dialogue_state_from_messages,
    detect_intent,
    detect_intents,
)
from chatbot.models import ChatMessage, ChatSession
from chatbot.prompts import strip_leaked_prompt_echo
from chatbot.views import CHATBOT_SUGGESTED_QUESTIONS
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


class DialogueIntentDetectionTests(ChatbotPhase2Helpers):
    def test_detect_intents_multi_balance_and_plan(self) -> None:
        got = detect_intents("What is my balance and what plan am I on?", DialogueState(None))
        self.assertEqual(got, ["current_plan", "account_balance"])

    def test_follow_up_reuses_prior_plan_topic_via_dialogue_state(self) -> None:
        state = DialogueState(last_grounded_intent="current_plan")
        self.assertEqual(
            detect_intents("Can you break that down?", state),
            ["current_plan"],
        )

    def test_data_allowance_utterance_maps_to_plan(self) -> None:
        self.assertEqual(
            detect_intents("What about the data allowance on that?", DialogueState(None)),
            ["current_plan"],
        )

    def test_dialogue_state_skips_prior_unsupported_user_turn(self) -> None:
        sess = ChatSession.objects.create(user=self.cust_u1)
        ChatMessage.objects.create(session=sess, role=ChatMessage.Role.USER, content="nonsense", intent="unsupported")
        ChatMessage.objects.create(session=sess, role=ChatMessage.Role.USER, content="What's my balance?", intent="account_balance")
        ChatMessage.objects.create(session=sess, role=ChatMessage.Role.ASSISTANT, content="...", intent="account_balance")

        msgs = list(sess.messages.order_by("created_at"))
        self.assertEqual(dialogue_state_from_messages(msgs).last_grounded_intent, "account_balance")

    def test_over_data_allowance_includes_usage_intent(self) -> None:
        got = detect_intents("am I over my data allowance", DialogueState(None))
        self.assertIn("data_usage", got)
        self.assertIn("current_plan", got)

    def test_available_plans_maps_to_plan_catalog(self) -> None:
        self.assertEqual(detect_intents("What plans are available?", DialogueState(None)), ["plan_catalog"])

    def test_cheaper_plan_dedupes_current_plan(self) -> None:
        self.assertEqual(
            detect_intents("Is there a cheaper plan than mine?", DialogueState(None)),
            ["plan_catalog"],
        )

    def test_my_plan_and_list_all_keeps_current_and_catalog(self) -> None:
        got = detect_intents("What is my plan and list all plans?", DialogueState(None))
        self.assertIn("plan_catalog", got)
        self.assertIn("current_plan", got)

    def test_catalog_phrase_lists_all_service_intents(self) -> None:
        got = detect_intents(
            "plan, balance, usage, payments, complaints, or outage",
            DialogueState(None),
        )
        self.assertEqual(
            got,
            [
                "current_plan",
                "account_balance",
                "data_usage",
                "open_complaints",
                "last_payment",
                "active_outages",
            ],
        )


class StripLeakedPromptEchoTests(TestCase):
    def test_removes_customer_question_and_json_scaffolding(self) -> None:
        blob = (
            "CUSTOMER_QUESTION: plan, balance\n\n"
            "ACCOUNT_CONTEXT:\n"
            '{"multi":true,"sections":{"current_plan":{"intent":"current_plan","plan":{"name":"Basic"}}}}\n\n'
            "Your plan is Basic."
        )
        self.assertEqual(strip_leaked_prompt_echo(blob).strip(), "Your plan is Basic.")


class ChatbotMergedContextTests(ChatbotPhase2Helpers):
    def test_merged_plan_catalog_includes_your_plan_and_rows(self) -> None:
        ServicePlan.objects.create(
            name="CatalogExtraZ",
            monthly_price=Decimal("99.00"),
            data_allowance_gb=Decimal("50.00"),
            call_minutes=500,
            sms_allowance=200,
        )
        merged = build_merged_chat_context(
            user=self.cust_u1,
            intents=["plan_catalog"],
            account=self.acct_one,
        )
        sec = merged["sections"]["plan_catalog"]
        self.assertGreaterEqual(len(sec["plans"]), 2)
        self.assertEqual(sec["your_plan"]["name"], "PlanA")
        self.assertTrue(sec["by_price_low_to_high"])
        self.assertTrue(merged_context_has_required_data(["plan_catalog"], merged))

    def test_plan_catalog_comparison_no_cheaper_when_on_lowest_tier(self) -> None:
        ServicePlan.objects.create(
            name="UpmarketZZ",
            monthly_price=Decimal("60.00"),
            data_allowance_gb=Decimal("100.00"),
            call_minutes=999,
            sms_allowance=999,
        )
        merged = build_merged_chat_context(
            user=self.cust_u1,
            intents=["plan_catalog"],
            account=self.acct_one,
        )
        comp = merged["sections"]["plan_catalog"]["comparison"]
        self.assertEqual(comp["cheapest_plan_name"], "PlanA")
        self.assertEqual(comp["plans_with_lower_monthly_price_than_yours"], [])

    def test_plan_catalog_comparison_lists_lower_priced_plans(self) -> None:
        plan_std = ServicePlan.objects.create(
            name="StandardMid",
            monthly_price=Decimal("40.00"),
            data_allowance_gb=Decimal("20.00"),
            call_minutes=400,
            sms_allowance=200,
        )
        self.acct_two.service_plan = plan_std
        self.acct_two.save(update_fields=["service_plan"])

        merged = build_merged_chat_context(
            user=self.cust_u2,
            intents=["plan_catalog"],
            account=self.acct_two,
        )
        comp = merged["sections"]["plan_catalog"]["comparison"]
        lower = comp["plans_with_lower_monthly_price_than_yours"]
        self.assertTrue(any(r["name"] == "PlanA" for r in lower))

    def test_merged_context_shapes_and_validation(self) -> None:
        merged = build_merged_chat_context(
            user=self.cust_u1,
            intents=["account_balance", "current_plan"],
            account=self.acct_one,
        )
        self.assertTrue(merged.get("multi"))
        self.assertEqual(
            merged.get("intents"),
            ["current_plan", "account_balance"],
        )
        secs = merged["sections"]
        self.assertEqual(secs["account_balance"]["current_balance"], "12.34")
        self.assertEqual(secs["current_plan"]["plan"]["name"], "PlanA")

        self.assertTrue(merged_context_has_required_data(["current_plan", "account_balance"], merged))

    def test_merged_context_excludes_duplicate_intents(self) -> None:
        merged = build_merged_chat_context(
            user=self.cust_u1,
            intents=["current_plan", "current_plan"],
            account=self.acct_one,
        )
        self.assertFalse(merged.get("multi"))
        self.assertEqual(merged["intents"], ["current_plan"])


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
        self.assertEqual(payload["intents"], ["current_plan"])
        self.assertEqual(payload["message"], "You are covered by PlanA.")

        msgs = ChatMessage.objects.filter(session_id=session_pk).order_by("created_at")
        self.assertEqual(msgs.count(), 2)
        self.assertEqual(msgs.filter(role=ChatMessage.Role.ASSISTANT).count(), 1)
        mocked_ask_groq.assert_called_once()
        ctx_kw = mocked_ask_groq.call_args.kwargs["context"]
        self.assertFalse(ctx_kw.get("multi"))
        self.assertIn("sections", ctx_kw)
        self.assertIn("current_plan", ctx_kw["sections"])

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
        payload = resp.json()
        self.assertIn("Groq API key", payload["message"])
        self.assertEqual(payload["intents"], ["current_plan"])

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
        self.assertEqual(resp.json().get("intents"), ["current_plan"])
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
        payload = resp.json()
        self.assertEqual(payload["intent"], "unsupported")
        self.assertEqual(payload.get("intents"), [])

    @override_settings(GROQ_API_KEY="test-key-placeholder")
    @patch("chatbot.views.ask_groq")
    def test_cheaper_plan_on_lowest_tier_skips_llm(self, mocked_ask_groq: MagicMock) -> None:
        ServicePlan.objects.create(
            name="PremiumX",
            monthly_price=Decimal("60.00"),
            data_allowance_gb=Decimal("100.00"),
            call_minutes=999,
            sms_allowance=999,
        )
        cli = Client()
        cli.force_login(self.cust_u1)
        cli.get(reverse("chatbot:chat_home"))
        session_pk = ChatSession.objects.get(user=self.cust_u1).pk

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload(
                {
                    "session_id": session_pk,
                    "message": "Is there a cheaper plan than what I have?",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mocked_ask_groq.assert_not_called()
        msg = resp.json()["message"].lower()
        self.assertIn("lowest", msg)
        self.assertIn("cheaper", msg)

    @override_settings(GROQ_API_KEY="test-key-placeholder")
    @patch("chatbot.views.ask_groq")
    def test_cheaper_plan_mid_tier_lists_lower_tiers_without_llm(self, mocked_ask_groq: MagicMock) -> None:
        plan_std = ServicePlan.objects.create(
            name="StandardTier",
            monthly_price=Decimal("40.00"),
            data_allowance_gb=Decimal("20.00"),
            call_minutes=400,
            sms_allowance=200,
        )
        self.acct_two.service_plan = plan_std
        self.acct_two.save(update_fields=["service_plan"])
        cli = Client()
        cli.force_login(self.cust_u2)
        cli.get(reverse("chatbot:chat_home"))
        session_pk = ChatSession.objects.get(user=self.cust_u2).pk

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload({"session_id": session_pk, "message": "Is there a cheaper plan?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mocked_ask_groq.assert_not_called()
        self.assertIn("PlanA", resp.json()["message"])

    @override_settings(GROQ_API_KEY="test-key-placeholder")
    @patch("chatbot.views.ask_groq")
    def test_follow_up_after_plan_uses_plan_context_when_keywords_absent(
        self, mocked_ask_groq: MagicMock
    ) -> None:
        mocked_ask_groq.side_effect = ["You are on PlanA.", "Here is extra plan detail."]
        cli = Client()
        cli.force_login(self.cust_u1)
        cli.get(reverse("chatbot:chat_home"))
        session_pk = ChatSession.objects.get(user=self.cust_u1).pk

        r1 = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload({"session_id": session_pk, "message": "What plan am I on?"}),
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)

        r2 = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload({"session_id": session_pk, "message": "Can you break that down?"}),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(mocked_ask_groq.call_count, 2)
        ctx_follow = mocked_ask_groq.call_args_list[1].kwargs["context"]
        self.assertIn("current_plan", ctx_follow["sections"])
        payload = r2.json()
        self.assertEqual(payload["intent"], "current_plan")
        self.assertEqual(payload["intents"], ["current_plan"])

    @override_settings(GROQ_API_KEY="test-key-placeholder")
    @patch("chatbot.views.ask_groq", return_value="Plan plus balance.")
    def test_balance_and_plan_merged_sections(self, mocked_ask_groq: MagicMock) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        cli.get(reverse("chatbot:chat_home"))
        session_pk = ChatSession.objects.get(user=self.cust_u1).pk

        resp = cli.post(
            reverse("chatbot:post_message"),
            data=json_payload(
                {
                    "session_id": session_pk,
                    "message": "What is my account balance and what plan am I on?",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mocked_ask_groq.assert_called_once()
        ctx = mocked_ask_groq.call_args.kwargs["context"]
        self.assertTrue(ctx.get("multi"))
        self.assertEqual(ctx["intents"], ["current_plan", "account_balance"])
        self.assertEqual(set(ctx["sections"].keys()), {"current_plan", "account_balance"})
        payload = resp.json()
        self.assertEqual(payload["intent"], "current_plan")
        self.assertEqual(payload["intents"], ["current_plan", "account_balance"])

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


class ChatbotPhase3UITests(ChatbotPhase2Helpers):
    """Polished chat HTML, routing, navbar visibility, ?session support."""

    def setUp(self) -> None:
        super().setUp()
        self.admin_nav_user = User.objects.create_user(username="cb_admin_nav_phase3", password="pass")
        UserProfile.objects.create(user=self.admin_nav_user, role=UserProfile.Role.ADMIN, region="HQ")

    def test_chat_home_contains_suggestions_csrf_viewport_and_assets(self) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        resp = cli.get(reverse("chatbot:chat_home"))
        self.assertEqual(resp.status_code, 200)
        for q in CHATBOT_SUGGESTED_QUESTIONS:
            self.assertContains(resp, q)
        self.assertContains(resp, "csrfmiddlewaretoken")
        self.assertContains(resp, "chatbot/chatbot.js")
        self.assertContains(resp, "chatTranscript")

    def test_transcript_round_trips_ordered_in_markup(self) -> None:
        session = ChatSession.objects.create(user=self.cust_u1)
        ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content="FIRST_MARKER", intent="unsupported")
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="SECOND_MARKER",
            intent="current_plan",
        )
        cli = Client()
        cli.force_login(self.cust_u1)
        url = reverse("chatbot:chat_home") + f"?session={session.pk}"
        resp = cli.get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        pos_first = body.find("FIRST_MARKER")
        pos_second = body.find("SECOND_MARKER")
        self.assertGreater(pos_first, -1)
        self.assertGreater(pos_second, -1)
        self.assertLess(pos_first, pos_second)

    def test_chat_transcript_does_not_shadow_django_messages_framework(self) -> None:
        """Regression: context key ``messages`` is reserved for flash messages in base.html."""
        session = ChatSession.objects.create(user=self.cust_u1)
        marker = "CHAT_RENDER_ONCE_Q9"
        ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content=marker, intent="unsupported")
        cli = Client()
        cli.force_login(self.cust_u1)
        resp = cli.get(reverse("chatbot:chat_home") + f"?session={session.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode().count(marker), 1)

    def test_session_query_param_loads_requested_empty_session_over_default(self) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        s_new = ChatSession.objects.create(user=self.cust_u1, title="empty explicit")
        s_old = ChatSession.objects.create(user=self.cust_u1, title="with transcript")
        ChatMessage.objects.create(
            session=s_old,
            role=ChatMessage.Role.USER,
            content="SECRET_UNIQUE_CHAT_PHASE3_MARKER",
            intent="unsupported",
        )
        ChatSession.objects.filter(pk=s_old.pk).update(updated_at=timezone.now())
        ChatSession.objects.filter(pk=s_new.pk).update(updated_at=timezone.now() - timedelta(days=30))

        resp_default = cli.get(reverse("chatbot:chat_home"))
        self.assertContains(resp_default, "SECRET_UNIQUE_CHAT_PHASE3_MARKER")

        resp_pick = cli.get(reverse("chatbot:chat_home") + f"?session={s_new.pk}")
        self.assertEqual(resp_pick.status_code, 200)
        self.assertNotContains(resp_pick, "SECRET_UNIQUE_CHAT_PHASE3_MARKER")

    def test_customer_home_nav_includes_chatbot_link(self) -> None:
        cli = Client()
        cli.force_login(self.cust_u1)
        resp = cli.get(reverse("accounts:customer_home"))
        chat_url = reverse("chatbot:chat_home")
        self.assertContains(resp, chat_url)

    def test_agent_home_nav_has_no_chatbot_link(self) -> None:
        cli = Client()
        cli.force_login(self.agent)
        resp = cli.get(reverse("accounts:agent_home"))
        chat_url = reverse("chatbot:chat_home")
        self.assertNotContains(resp, chat_url)

    def test_admin_home_nav_has_no_chatbot_link(self) -> None:
        cli = Client()
        cli.force_login(self.admin_nav_user)
        resp = cli.get(reverse("accounts:admin_home"))
        chat_url = reverse("chatbot:chat_home")
        self.assertNotContains(resp, chat_url)

    def test_customer_without_linked_account_warning(self) -> None:
        orphan = User.objects.create_user(username="cb_orphan_customer", password="pass")
        UserProfile.objects.create(user=orphan, role=UserProfile.Role.CUSTOMER, region="Kingston")

        cli = Client()
        cli.force_login(orphan)
        resp = cli.get(reverse("chatbot:chat_home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No customer account is linked")


def json_payload(obj: dict) -> str:
    return json.dumps(obj)