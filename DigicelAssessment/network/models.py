"""Records of network problems in a geographic region.

These rows power "are there outages in my area?" in the chatbot and can be shown
in admin. ``is_active`` marks problems that are still ongoing.
"""

from django.db import models


class NetworkOutage(models.Model):
    """One outage event: where it is, headline text, details, and time window."""

    region = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    started_at = models.DateTimeField()
    estimated_resolution_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "region"]),
        ]

    def __str__(self):
        return f"{self.region}: {self.title}"
