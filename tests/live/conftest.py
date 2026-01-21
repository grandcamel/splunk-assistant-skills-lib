"""
Live Test Configuration

Fixtures for live integration tests against real Splunk instances.
"""

import os
import pytest
from typing import Generator


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "live: mark test as requiring a live Splunk instance"
    )


@pytest.fixture(scope="session")
def splunk_credentials() -> dict:
    """Get Splunk credentials from environment variables.

    Required environment variables:
    - SPLUNK_URL: Base URL (e.g., https://localhost:8089)
    - SPLUNK_USERNAME: Admin username (default: admin)
    - SPLUNK_PASSWORD: Admin password
    - SPLUNK_VERIFY_SSL: Whether to verify SSL (default: false)
    """
    url = os.getenv("SPLUNK_URL")
    password = os.getenv("SPLUNK_PASSWORD")

    if not url or not password:
        pytest.skip(
            "Live tests require SPLUNK_URL and SPLUNK_PASSWORD environment variables"
        )

    return {
        "url": url,
        "username": os.getenv("SPLUNK_USERNAME", "admin"),
        "password": password,
        "verify_ssl": os.getenv("SPLUNK_VERIFY_SSL", "false").lower() == "true",
    }


@pytest.fixture(scope="session")
def splunk_client(splunk_credentials):
    """Create a Splunk client for live testing.

    Returns a configured SplunkClient instance connected to the test instance.
    """
    from splunk_as import SplunkClient

    client = SplunkClient(
        base_url=splunk_credentials["url"],
        username=splunk_credentials["username"],
        password=splunk_credentials["password"],
        verify_ssl=splunk_credentials["verify_ssl"],
    )

    # Verify connection
    try:
        client.get_server_info()
    except Exception as e:
        pytest.skip(f"Cannot connect to Splunk: {e}")

    return client


@pytest.fixture
def test_index_name() -> str:
    """Generate a unique test index name."""
    import time
    return f"test_live_{int(time.time())}"
