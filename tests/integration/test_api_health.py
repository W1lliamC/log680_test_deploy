"""Integration tests for API health and basic functionality.

These tests run against a live server instance and verify
end-to-end functionality without mocking.
"""

import pytest


class TestAPIHealth:
    """Test basic API health and startup functionality."""

    def test_health_endpoint(self, live_client):
        """Test that the health endpoint returns correctly."""
        response = live_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_api_docs_available(self, live_client):
        """Test that Swagger documentation is accessible."""
        response = live_client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_openapi_schema_available(self, live_client):
        """Test that OpenAPI schema is accessible."""
        response = live_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert schema["info"]["title"] == "FlowHub API"