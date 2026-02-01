"""
Live Integration Tests

Tests that run against a real Splunk instance (Docker container or external).
These tests verify that the client works correctly with the actual Splunk API.

Usage:
    # With Docker (requires testcontainers and Docker running)
    pytest tests/live/ --live -v

    # With external Splunk
    SPLUNK_TEST_URL=https://splunk:8089 SPLUNK_TEST_TOKEN=xxx pytest tests/live/ --live -v

    # With external Splunk using basic auth
    SPLUNK_TEST_URL=https://splunk:8089 SPLUNK_TEST_USERNAME=admin SPLUNK_TEST_PASSWORD=xxx pytest tests/live/ --live -v
"""
