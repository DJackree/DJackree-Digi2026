"""Chat session and message persistence for the customer-facing AI chatbot."""

from django.contrib.auth.models import User
from django.db import models


class ChatSession(models.Model):
    """A conversation belonging to exactly one Django user."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    title = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat session"
        verbose_name_plural = "Chat sessions"
        ordering = ("-updated_at",)
        indexes = [
            # Supports filtering by user and ordering recent sessions (newest first).
            models.Index(fields=["user", "-updated_at"], name="chatbot_chatuser_updated_idx"),
        ]

    def __str__(self) -> str:
        label = self.title.strip() if self.title else f"Session {self.pk or 'new'}"
        return f"{label} ({self.user.username})"


class ChatMessage(models.Model):
    """One turn in a chat session transcript."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chat message"
        verbose_name_plural = "Chat messages"
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["session", "created_at"], name="chatbot_msg_sess_created_idx"),
        ]

    def __str__(self) -> str:
        preview = self.content[:50] + "…" if len(self.content) > 50 else self.content
        return f"{self.get_role_display()}: {preview}"
