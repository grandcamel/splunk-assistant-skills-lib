"""
Live Server Info Tests

Tests for server information retrieval against a real Splunk instance.
"""

import pytest


@pytest.mark.live
class TestServerInfoLive:
    """Live tests for server info API."""

    def test_get_server_info(self, splunk_client):
        """Should retrieve basic server information."""
        info = splunk_client.get_server_info()

        assert info is not None
        assert "version" in info or "serverName" in info

    def test_get_server_health(self, splunk_client):
        """Should retrieve server health status."""
        # This may vary by Splunk version, so we just verify the call succeeds
        try:
            health = splunk_client.get("/services/server/health/splunkd")
            assert health is not None
        except Exception:
            # Some Splunk versions don't have this endpoint
            pytest.skip("Server health endpoint not available")


@pytest.mark.live
class TestAuthenticationLive:
    """Live tests for authentication."""

    def test_valid_credentials(self, splunk_client, splunk_credentials):
        """Valid credentials should authenticate successfully."""
        # The fixture already verifies auth works, but let's be explicit
        info = splunk_client.get_server_info()
        assert info is not None

    def test_session_token_obtained(self, splunk_client):
        """Client should have obtained a session token."""
        # After successful auth, client should have a token
        assert splunk_client.session_key is not None
