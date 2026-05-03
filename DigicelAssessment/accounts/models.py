"""User profile linked to Django auth users.

Each login has exactly one profile row (when seeded correctly). The profile stores
*which portal role* someone has (customer, agent, or admin) and an optional *region*
string used for things like outage lookups in the chatbot.
"""

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Extra facts about a user account beyond username and password.

    Django's built-in ``User`` model handles authentication. This table adds
    business fields: what kind of portal user they are and where they are located.
    """

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        AGENT = "agent", "Agent"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    region = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
