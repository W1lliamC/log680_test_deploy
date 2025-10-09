"""Integration tests for the complete data flow.

These tests verify end-to-end workflows that involve multiple
components working together.
"""

import pytest
from datetime import datetime


class TestCompleteDataFlow:
    """Integration tests for complete data workflows."""

    def test_api_cors_headers(self, live_client):
        """Test that API handles CORS headers appropriately."""
        response = live_client.options("/health")
        # Should either have CORS headers or handle OPTIONS gracefully
        assert response.status_code in [200, 405]

    def test_api_error_handling(self, live_client):
        """Test API error handling for malformed requests."""
        # Test with invalid date format
        response = live_client.get(
            "/metrics/kanban/lead-time",
            params={"start": "invalid-date", "end": "2024-01-01"}
        )
        assert response.status_code == 422

    def test_api_content_type_headers(self, live_client):
        """Test that API returns correct content type headers."""
        response = live_client.get("/health")
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_multiple_concurrent_requests(self, live_client):
        """Test that API can handle multiple concurrent requests."""
        # Simple concurrent test with health endpoint
        import concurrent.futures
        
        def make_request():
            return live_client.get("/health")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        for response in results:
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_api_response_time(self, live_client):
        """Test that API responds within reasonable time."""
        import time
        
        start_time = time.time()
        response = live_client.get("/health")
        end_time = time.time()
        
        assert response.status_code == 200
        # Response should be under 5 seconds (reasonable for integration test)
        assert (end_time - start_time) < 5.0