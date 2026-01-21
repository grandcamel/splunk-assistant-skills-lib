#!/usr/bin/env python3
"""
Shared pytest fixtures for splunk-as tests.

Provides common fixtures used across all tests.
This root conftest.py centralizes:
- pytest hooks (addoption, configure, collection_modifyitems)
- Mock client fixtures
- Sample response fixtures
"""

from unittest.mock import Mock

import pytest

# =============================================================================
# PYTEST HOOKS
# =============================================================================


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--live", action="store_true", default=False, help="Run live integration tests"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external calls)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (may require credentials)"
    )
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "live: Tests requiring live credentials")
    config.addinivalue_line("markers", "destructive: Tests that modify data")


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless --live is provided."""
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="Need --live to run")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


# =============================================================================
# CLIENT MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_splunk_client():
    """Create a mock SplunkClient for testing."""
    client = Mock()
    client.base_url = "https://splunk.example.com:8089/services"
    client.auth_method = "bearer"
    client.timeout = 30
    client.DEFAULT_SEARCH_TIMEOUT = 300

    # Default responses
    client.get.return_value = {"entry": []}
    client.post.return_value = {"sid": "1703779200.12345"}
    client.put.return_value = {}
    client.delete.return_value = {}

    return client


# =============================================================================
# CONFIGURATION FIXTURES
# =============================================================================


@pytest.fixture
def mock_config():
    """Create mock configuration matching actual flat structure."""
    return {
        "splunk": {
            "url": "https://splunk.example.com",
            "port": 8089,
            "token": "test-token",
            "auth_method": "bearer",
            "api": {
                "timeout": 30,
                "search_timeout": 300,
            },
            "search_defaults": {
                "earliest_time": "-24h",
                "latest_time": "now",
                "max_count": 50000,
            },
        }
    }


# =============================================================================
# SAMPLE RESPONSE FIXTURES
# =============================================================================


@pytest.fixture
def sample_job_response():
    """Sample search job response."""
    return {
        "sid": "1703779200.12345",
        "entry": [
            {
                "name": "1703779200.12345",
                "content": {
                    "sid": "1703779200.12345",
                    "dispatchState": "DONE",
                    "doneProgress": 1.0,
                    "eventCount": 1000,
                    "resultCount": 100,
                    "scanCount": 5000,
                    "runDuration": 2.5,
                    "isDone": True,
                    "isFailed": False,
                    "isPaused": False,
                },
            }
        ],
    }


@pytest.fixture
def sample_search_results():
    """Sample search results."""
    return {
        "results": [
            {"host": "server1", "status": "200", "count": "100"},
            {"host": "server2", "status": "200", "count": "150"},
            {"host": "server3", "status": "404", "count": "25"},
        ]
    }
