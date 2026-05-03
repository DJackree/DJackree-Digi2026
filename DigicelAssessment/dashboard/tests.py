"""Smoke tests that dashboard metric keys exist (empty DB is fine for structure checks)."""

from django.test import TestCase

from dashboard.services import get_dashboard_metrics


class DashboardMetricsTests(TestCase):
    def test_metrics_has_expected_sections(self) -> None:
        metrics = get_dashboard_metrics()
        self.assertIn("by_status", metrics)
        self.assertIn("by_category", metrics)
        self.assertIn("average_resolution_time", metrics)
        self.assertIn("sla_breaches", metrics)
