"""Integration tests for Pull Request metrics endpoints.

These tests exercise the live API to validate the behaviour of
`/metrics/prs` routes using real data when available.
"""

from __future__ import annotations

from datetime import datetime

import pytest


def _assert_pr_item_shape(item: dict[str, object]) -> None:
    """Validate the minimal shape of a PRLeadTimeItem payload."""
    # "age" is optional: it's only present for open PRs (when include_age_for_open=True)
    # and excluded (response_model_exclude_none) for closed/merged PRs where age is None.
    required_keys = {
        "pr_number",
        "created_at",
        "merged_at",
        "closed_at",
        "lead_time",
    }
    assert required_keys.issubset(item.keys())
    # If age is present, it must either be None or a number (float/int)
    if "age" in item:
        assert item["age"] is None or isinstance(item["age"], (int, float))
    assert isinstance(item["pr_number"], int)
    # created_at must be a valid ISO date string
    datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
    if item["merged_at"] is not None:
        datetime.fromisoformat(str(item["merged_at"]).replace("Z", "+00:00"))
    if item["closed_at"] is not None:
        datetime.fromisoformat(str(item["closed_at"]).replace("Z", "+00:00"))


def _assert_pr_count_shape(item: dict[str, object]) -> None:
    """Validate the shape of PRCount payload."""
    expected_keys = {"pr_number", "title", "count"}
    assert expected_keys.issubset(item.keys())
    assert isinstance(item["pr_number"], int)
    assert isinstance(item["count"], int)


def _assert_pr_stats_shape(item: dict[str, object]) -> None:
    """Validate the shape of PRStats payload."""
    expected_keys = {"pr_number", "title", "additions", "deletions", "changed_files"}
    assert expected_keys.issubset(item.keys())
    assert isinstance(item["pr_number"], int)
    assert isinstance(item["additions"], int)
    assert isinstance(item["deletions"], int)
    assert isinstance(item["changed_files"], int)


def _assert_pr_branches_shape(item: dict[str, object]) -> None:
    """Validate the shape of PRBranches payload."""
    expected_keys = {"pr_number", "title", "head", "base"}
    assert expected_keys.issubset(item.keys())
    assert isinstance(item["pr_number"], int)
    assert isinstance(item["head"], str)
    assert isinstance(item["base"], str)


class TestPRMetrics:
    """Suite regroupant les tests d'intégration pour les métriques Pull Requests."""

    def test_lead_time_collection_available(self, live_client):
        response = live_client.get("/metrics/prs/lead-time")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        for item in payload:
            _assert_pr_item_shape(item)

    def test_lead_time_detail_matches_collection(self, live_client):
        response = live_client.get("/metrics/prs/lead-time")
        assert response.status_code == 200
        items = response.json()
        if not items:
            pytest.skip("Aucune PR fermée disponible pour valider la route détail.")

        reference = items[0]
        detail_response = live_client.get(
            f"/metrics/prs/lead-time/{reference['pr_number']}"
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        _assert_pr_item_shape(detail)
        assert detail["pr_number"] == reference["pr_number"]

    def test_lead_time_detail_not_found(self, live_client):
        response = live_client.get("/metrics/prs/lead-time/999999999")
        assert response.status_code == 404
        body = response.json()
        assert body["detail"].startswith("Non existent PR")

    def test_commits_count_detail(self, live_client):
        # First get a PR number from lead time
        response = live_client.get("/metrics/prs/lead-time")
        assert response.status_code == 200
        items = response.json()
        if not items:
            pytest.skip("Aucune PR disponible pour tester les commits.")

        pr_number = items[0]["pr_number"]
        response = live_client.get(f"/metrics/prs/commits/{pr_number}")
        assert response.status_code == 200
        payload = response.json()
        _assert_pr_count_shape(payload)
        assert payload["pr_number"] == pr_number

    def test_reviews_count_detail(self, live_client):
        # First get a PR number from lead time
        response = live_client.get("/metrics/prs/lead-time")
        assert response.status_code == 200
        items = response.json()
        if not items:
            pytest.skip("Aucune PR disponible pour tester les reviews.")

        pr_number = items[0]["pr_number"]
        response = live_client.get(f"/metrics/prs/reviews/{pr_number}")
        assert response.status_code == 200
        payload = response.json()
        _assert_pr_count_shape(payload)
        assert payload["pr_number"] == pr_number

    def test_stats_detail(self, live_client):
        # First get a PR number from lead time
        response = live_client.get("/metrics/prs/lead-time")
        assert response.status_code == 200
        items = response.json()
        if not items:
            pytest.skip("Aucune PR disponible pour tester les stats.")

        pr_number = items[0]["pr_number"]
        response = live_client.get(f"/metrics/prs/stats/{pr_number}")
        assert response.status_code == 200
        payload = response.json()
        _assert_pr_stats_shape(payload)
        assert payload["pr_number"] == pr_number

    def test_branches_detail(self, live_client):
        # First get a PR number from lead time
        response = live_client.get("/metrics/prs/lead-time")
        assert response.status_code == 200
        items = response.json()
        if not items:
            pytest.skip("Aucune PR disponible pour tester les branches.")

        pr_number = items[0]["pr_number"]
        response = live_client.get(f"/metrics/prs/branches/{pr_number}")
        assert response.status_code == 200
        payload = response.json()
        _assert_pr_branches_shape(payload)
        assert payload["pr_number"] == pr_number

    def test_lead_time_collection_invalid_date_returns_422(self, live_client):
        response = live_client.get(
            "/metrics/prs/lead-time",
            params={"start": "not-a-date"},
        )
        assert response.status_code == 422
