"""Model tests for chatbot persistence (Phase 1)."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from chatbot.models import ChatMessage, ChatSession


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
