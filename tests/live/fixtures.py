#!/usr/bin/env python3
"""
Pytest Fixtures for Splunk Live Integration Tests

Provides session-scoped fixtures for:
- Splunk container/connection management
- SplunkClient instance
- Test index creation/cleanup
- Synthetic test data generation

Usage in tests:
    def test_search(splunk_client, test_data):
        results = splunk_client.post('/search/jobs/oneshot', ...)
        assert len(results) > 0
"""

import json
import logging
import os
import uuid
from typing import Generator, Optional

import pytest

from .splunk_container import (
    ExternalSplunkConnection,
    SplunkContainer,
    get_splunk_connection,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Session-Scoped Fixtures (shared across all tests in session)
# =============================================================================


@pytest.fixture(scope="session")
def splunk_connection():
    """
    Session-scoped Splunk connection.

    Starts a Docker container or connects to external Splunk.
    The connection persists for the entire test session.

    Yields:
        SplunkContainer or ExternalSplunkConnection
    """
    connection = get_splunk_connection()

    # Start container if it's a Docker container
    if isinstance(connection, SplunkContainer):
        connection.start()
        yield connection
        connection.stop()
    else:
        # External connection - no lifecycle management needed
        yield connection


@pytest.fixture(scope="session")
def splunk_client(splunk_connection):
    """
    Session-scoped SplunkClient instance.

    Provides a configured client for making API calls.

    Args:
        splunk_connection: The Splunk connection fixture

    Yields:
        SplunkClient: Configured client instance
    """
    client = splunk_connection.get_client()
    yield client


@pytest.fixture(scope="session")
def splunk_info(splunk_client) -> dict:
    """
    Get Splunk server information.

    Useful for version-specific test logic.

    Returns:
        dict: Server information
    """
    return splunk_client.get_server_info()


# =============================================================================
# Test Index Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_index_name() -> str:
    """Get the test index name."""
    return os.environ.get("SPLUNK_TEST_INDEX", "splunk_as_test")


@pytest.fixture(scope="session")
def test_index(splunk_connection, test_index_name: str) -> Generator[str, None, None]:
    """
    Session-scoped test index.

    Creates a dedicated index for testing and cleans it up after.

    Yields:
        str: The test index name
    """
    # Create the test index
    created = splunk_connection.create_test_index(test_index_name)
    if not created:
        logger.warning(
            f"Could not create test index {test_index_name}, may already exist"
        )

    yield test_index_name

    # Cleanup - delete the test index
    # Note: Only delete if we created it (Docker) or if explicitly requested
    if isinstance(splunk_connection, SplunkContainer):
        splunk_connection.delete_test_index(test_index_name)


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_data(splunk_connection, test_index: str) -> dict:
    """
    Generate synthetic test data using SPL.

    Creates a variety of test events for different test scenarios.

    Returns:
        dict: Information about generated test data
    """
    from .test_utils import generate_test_events, wait_for_indexing

    # Generate various types of test events
    event_types = [
        {
            "name": "web_access",
            "count": 100,
            "fields": {
                "sourcetype": "access_combined",
                "host": ["web01", "web02", "web03"],
                "status": [200, 200, 200, 200, 404, 500],
                "uri": ["/api/users", "/api/orders", "/health", "/login"],
            },
        },
        {
            "name": "application_logs",
            "count": 50,
            "fields": {
                "sourcetype": "app_logs",
                "host": ["app01", "app02"],
                "level": ["INFO", "INFO", "INFO", "WARN", "ERROR"],
                "component": ["auth", "api", "db", "cache"],
            },
        },
        {
            "name": "metrics",
            "count": 200,
            "fields": {
                "sourcetype": "metrics",
                "host": ["server01", "server02", "server03"],
                "metric_name": ["cpu.percent", "mem.percent", "disk.percent"],
            },
        },
    ]

    total_events = 0
    for event_type in event_types:
        count = generate_test_events(
            splunk_connection,
            index=test_index,
            count=event_type["count"],
            fields=event_type["fields"],
        )
        total_events += count
        logger.info(f"Generated {count} {event_type['name']} events")

    # Wait for events to be indexed
    wait_for_indexing(splunk_connection, test_index, min_events=total_events)

    return {
        "index": test_index,
        "total_events": total_events,
        "event_types": event_types,
    }


@pytest.fixture(scope="function")
def fresh_test_data(splunk_connection, test_index: str) -> dict:
    """
    Function-scoped test data (fresh for each test).

    Generates a small set of test events unique to each test.
    Uses a unique marker to isolate from other tests.

    Returns:
        dict: Information about generated test data
    """
    from .test_utils import generate_test_events

    test_marker = str(uuid.uuid4())[:8]

    count = generate_test_events(
        splunk_connection,
        index=test_index,
        count=10,
        fields={
            "sourcetype": "test_events",
            "test_marker": test_marker,
            "host": ["testhost"],
        },
    )

    return {
        "index": test_index,
        "count": count,
        "marker": test_marker,
        "search_filter": f'test_marker="{test_marker}"',
    }


# =============================================================================
# Module-Scoped Fixtures (for isolated test files)
# =============================================================================


@pytest.fixture(scope="module")
def module_splunk_connection():
    """
    Module-scoped Splunk connection.

    Creates a fresh container for each test module.
    Use this for tests that need complete isolation.

    Note: This is slower than session-scoped fixtures.
    """
    connection = get_splunk_connection()

    if isinstance(connection, SplunkContainer):
        connection.start()
        yield connection
        connection.stop()
    else:
        yield connection


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def search_helper(splunk_client):
    """
    Helper for executing searches in tests.

    Provides a simplified interface for common search operations.
    """

    class SearchHelper:
        def __init__(self, client):
            self.client = client

        def oneshot(self, spl: str, **kwargs) -> list:
            """Execute oneshot search and return results."""
            response = self.client.post(
                "/search/jobs/oneshot",
                data={
                    "search": spl,
                    "output_mode": "json",
                    "earliest_time": kwargs.get("earliest_time", "-24h"),
                    "latest_time": kwargs.get("latest_time", "now"),
                    "count": kwargs.get("count", 1000),
                },
                timeout=kwargs.get("timeout", 60),
                operation="test search",
            )
            return response.get("results", [])

        def count(self, spl: str, **kwargs) -> int:
            """Execute search and return result count."""
            results = self.oneshot(f"{spl} | stats count", **kwargs)
            if results:
                return int(results[0].get("count", 0))
            return 0

        def exists(self, spl: str, **kwargs) -> bool:
            """Check if search returns any results."""
            return self.count(spl, **kwargs) > 0

        def cleanup(self):
            """
            Cleanup search helper resources.

            Note: Oneshot searches don't create persistent jobs,
            so no cleanup is needed. This method exists for API
            consistency with JobHelper.
            """
            pass

    return SearchHelper(splunk_client)


@pytest.fixture
def job_helper(splunk_client):
    """
    Helper for managing search jobs in tests.
    """

    class JobHelper:
        def __init__(self, client):
            self.client = client
            self.created_jobs = []

        def create(self, spl: str, **kwargs) -> str:
            """Create a search job and return SID."""
            response = self.client.post(
                "/search/v2/jobs",
                data={
                    "search": spl,
                    "exec_mode": kwargs.get("exec_mode", "normal"),
                    "earliest_time": kwargs.get("earliest_time", "-24h"),
                    "latest_time": kwargs.get("latest_time", "now"),
                },
                operation="create test job",
            )
            sid = response.get("sid")
            if not sid and "entry" in response:
                sid = response["entry"][0].get("name")
            self.created_jobs.append(sid)
            return sid

        def get_status(self, sid: str) -> dict:
            """Get job status."""
            response = self.client.get(
                f"/search/v2/jobs/{sid}",
                operation="get job status",
            )
            if "entry" in response and response["entry"]:
                return response["entry"][0].get("content", {})
            return {}

        def wait_for_done(self, sid: str, timeout: int = 60) -> dict:
            """Wait for job to complete."""
            import time

            start = time.time()
            while time.time() - start < timeout:
                status = self.get_status(sid)
                if status.get("isDone"):
                    return status
                time.sleep(1)
            raise TimeoutError(f"Job {sid} did not complete in {timeout}s")

        def cleanup(self):
            """Cancel and delete all created jobs."""
            failed = []
            for sid in self.created_jobs:
                try:
                    self.client.post(
                        f"/search/v2/jobs/{sid}/control",
                        data={"action": "cancel"},
                    )
                except Exception as e:
                    logger.warning(f"Failed to cancel job {sid}: {e}")
                    failed.append(sid)
            self.created_jobs.clear()
            if failed:
                logger.error(f"Failed to cleanup {len(failed)} job(s): {failed}")

    helper = JobHelper(splunk_client)
    yield helper
    helper.cleanup()


# =============================================================================
# Resource Helper Fixtures
# =============================================================================


@pytest.fixture
def index_helper(splunk_client):
    """Helper for managing indexes in tests."""

    class IndexHelper:
        def __init__(self, client):
            self.client = client
            self.created_indexes = []

        def create(self, name: str, **kwargs) -> bool:
            """Create an index."""
            try:
                self.client.post(
                    "/data/indexes",
                    data={"name": name, **kwargs},
                    operation=f"create index {name}",
                )
                self.created_indexes.append(name)
                return True
            except Exception as e:
                logger.warning(f"Failed to create index {name}: {e}")
                return False

        def delete(self, name: str) -> bool:
            """Delete an index."""
            try:
                self.client.delete(
                    f"/data/indexes/{name}",
                    operation=f"delete index {name}",
                )
                if name in self.created_indexes:
                    self.created_indexes.remove(name)
                return True
            except Exception:
                return False

        def cleanup(self):
            """Clean up all created indexes."""
            for name in self.created_indexes[:]:
                self.delete(name)

    helper = IndexHelper(splunk_client)
    yield helper
    helper.cleanup()


@pytest.fixture
def lookup_helper(splunk_client):
    """Helper for managing lookups in tests."""

    class LookupHelper:
        def __init__(self, client):
            self.client = client
            self.app = "search"
            self.created_lookups = []

        def upload(self, name: str, content: str) -> bool:
            """Upload a lookup file."""
            try:
                self.client.upload_lookup_file(
                    lookup_name=name,
                    csv_content=content,
                    app=self.app,
                )
                self.created_lookups.append(name)
                return True
            except Exception as e:
                logger.warning(f"Failed to upload lookup {name}: {e}")
                return False

        def delete(self, name: str) -> bool:
            """Delete a lookup file."""
            try:
                self.client.delete(
                    f"/servicesNS/nobody/{self.app}/data/lookup-table-files/{name}",
                    operation=f"delete lookup {name}",
                )
                if name in self.created_lookups:
                    self.created_lookups.remove(name)
                return True
            except Exception:
                return False

        def cleanup(self):
            """Clean up all created lookups."""
            for name in self.created_lookups[:]:
                self.delete(name)

    helper = LookupHelper(splunk_client)
    yield helper
    helper.cleanup()


@pytest.fixture
def test_lookup_name() -> str:
    """Generate a unique lookup name for testing."""
    return f"test_lookup_{uuid.uuid4().hex[:8]}.csv"


@pytest.fixture
def kvstore_helper(splunk_client):
    """Helper for managing KV Store collections in tests."""

    class KVStoreHelper:
        def __init__(self, client):
            self.client = client
            self.app = "search"
            self.created_collections = []

        def create_collection(self, name: str, fields: Optional[dict] = None) -> bool:
            """Create a KV Store collection."""
            try:
                data = {"name": name}
                if fields:
                    for field_name, field_type in fields.items():
                        data[f"field.{field_name}"] = field_type
                self.client.post(
                    f"/servicesNS/nobody/{self.app}/storage/collections/config",
                    data=data,
                    operation=f"create collection {name}",
                )
                self.created_collections.append(name)
                return True
            except Exception as e:
                logger.warning(f"Failed to create collection {name}: {e}")
                return False

        def delete_collection(self, name: str) -> bool:
            """Delete a KV Store collection."""
            try:
                self.client.delete(
                    f"/servicesNS/nobody/{self.app}/storage/collections/config/{name}",
                    operation=f"delete collection {name}",
                )
                if name in self.created_collections:
                    self.created_collections.remove(name)
                return True
            except Exception:
                return False

        def insert_record(self, collection: str, record: dict) -> Optional[str]:
            """Insert a record into a collection."""
            try:
                # Use direct POST with JSON for KV Store
                url = f"{self.client.base_url.replace('/services', '')}/servicesNS/nobody/{self.app}/storage/collections/data/{collection}"
                response = self.client.session.post(
                    url,
                    data=json.dumps(record),
                    headers={"Content-Type": "application/json"},
                    verify=self.client.verify_ssl,
                )
                response.raise_for_status()
                return response.json().get("_key")
            except Exception as e:
                logger.warning(f"Failed to insert record: {e}")
                return None

        def get_records(self, collection: str) -> list:
            """Get all records from a collection."""
            try:
                response = self.client.get(
                    f"/servicesNS/nobody/{self.app}/storage/collections/data/{collection}",
                    operation=f"get records from {collection}",
                )
                return response if isinstance(response, list) else []
            except Exception:
                return []

        def cleanup(self):
            """Clean up all created collections."""
            for name in self.created_collections[:]:
                self.delete_collection(name)

    helper = KVStoreHelper(splunk_client)
    yield helper
    helper.cleanup()


@pytest.fixture
def test_collection_name() -> str:
    """Generate a unique KV Store collection name for testing."""
    return f"test_collection_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def savedsearch_helper(splunk_client):
    """Helper for managing saved searches in tests."""

    class SavedSearchHelper:
        def __init__(self, client):
            self.client = client
            self.app = "search"
            self.created_searches = []

        def create(self, name: str, search: str, **kwargs) -> bool:
            """Create a saved search."""
            try:
                data = {"name": name, "search": search, **kwargs}
                self.client.post(
                    f"/servicesNS/nobody/{self.app}/saved/searches",
                    data=data,
                    operation=f"create saved search {name}",
                )
                self.created_searches.append(name)
                return True
            except Exception as e:
                logger.warning(f"Failed to create saved search {name}: {e}")
                return False

        def delete(self, name: str) -> bool:
            """Delete a saved search."""
            try:
                self.client.delete(
                    f"/servicesNS/nobody/{self.app}/saved/searches/{name}",
                    operation=f"delete saved search {name}",
                )
                if name in self.created_searches:
                    self.created_searches.remove(name)
                return True
            except Exception:
                return False

        def dispatch(self, name: str) -> Optional[str]:
            """Dispatch a saved search and return SID."""
            try:
                response = self.client.post(
                    f"/servicesNS/nobody/{self.app}/saved/searches/{name}/dispatch",
                    operation=f"dispatch {name}",
                )
                return response.get("sid")
            except Exception as e:
                logger.warning(f"Failed to dispatch {name}: {e}")
                return None

        def cleanup(self):
            """Clean up all created saved searches."""
            for name in self.created_searches[:]:
                self.delete(name)

    helper = SavedSearchHelper(splunk_client)
    yield helper
    helper.cleanup()


@pytest.fixture
def test_savedsearch_name() -> str:
    """Generate a unique saved search name for testing."""
    return f"test_savedsearch_{uuid.uuid4().hex[:8]}"


# =============================================================================
# Markers and Skip Conditions
# =============================================================================

# Note: pytest_configure for markers is in root conftest.py to avoid duplicates


@pytest.fixture(autouse=True)
def skip_if_no_docker(request):
    """Skip Docker-required tests if no Docker available."""
    if request.node.get_closest_marker("docker_required"):
        if os.environ.get("SPLUNK_TEST_URL"):
            pytest.skip("Test requires Docker but external Splunk configured")


@pytest.fixture(autouse=True)
def skip_if_not_external(request):
    """Skip external-only tests if using Docker."""
    if request.node.get_closest_marker("external_splunk"):
        if not os.environ.get("SPLUNK_TEST_URL"):
            pytest.skip("Test requires external Splunk instance")
