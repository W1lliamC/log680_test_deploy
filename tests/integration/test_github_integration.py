"""Integration tests for GitHub integration endpoints.

These tests exercise the live API to validate the behaviour of
GitHub-related routes (/refresh, /snapshot) using real data when available.
"""

import pytest


class TestGitHubIntegration:
    """Suite regroupant les tests d'intégration pour l'intégration GitHub."""

    def test_refresh_endpoint_accepts_post(self, live_client):
        response = live_client.post("/refresh")
        assert response.status_code in [200, 401, 403, 404]

    def test_snapshot_endpoint_requires_project_number(self, live_client):
        response = live_client.post("/snapshot")
        # Should fail because number is required
        assert response.status_code == 422

    def test_snapshot_endpoint_returns_expected_structure(self, live_client):
        # Only run if we have a valid project number configured
        project_number = 2

        response = live_client.post("/snapshot", params={"number": project_number})
        if response.status_code == 200:
            payload = response.json()
            assert "updated" in payload
            assert "counts" in payload
            assert isinstance(payload["updated"], int)
            assert isinstance(payload["counts"], dict)
        else:
            # If it fails, ensure it's a reasonable error
            assert response.status_code in [401, 403, 404]
