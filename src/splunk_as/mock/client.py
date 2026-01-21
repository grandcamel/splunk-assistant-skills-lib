"""
Mock Splunk Client Implementations

Provides composed mock clients for different testing scenarios:
- MockSplunkClient: Full mock with all capabilities
- Skill-specific mocks: Minimal clients for focused testing
"""

from typing import Any

from .base import MockSplunkClientBase
from .mixins.admin import AdminMixin
from .mixins.export import ExportMixin
from .mixins.job import JobMixin
from .mixins.metadata import MetadataMixin
from .mixins.search import SearchMixin


class MockSplunkClient(
    SearchMixin, JobMixin, MetadataMixin, AdminMixin, ExportMixin, MockSplunkClientBase
):
    """Full mock Splunk client with all mixins.

    Provides complete mock functionality for testing all skill areas:
    - Search operations (oneshot, normal, blocking)
    - Job lifecycle management
    - Metadata discovery
    - Administrative operations
    - Export/streaming

    Example:
        >>> client = MockSplunkClient()
        >>> # Test search
        >>> result = client.oneshot_search("index=main | head 10")
        >>> assert len(result["results"]) > 0
        >>> # Verify API calls
        >>> client.assert_called("POST", "/search/jobs/oneshot")

    For partial mocking, create a custom class with specific mixins:
        >>> class SearchOnlyMock(SearchMixin, MockSplunkClientBase):
        ...     pass
        >>> client = SearchOnlyMock()
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the full mock client.

        Accepts the same parameters as SplunkClient for compatibility.
        """
        super().__init__(*args, **kwargs)

    def reset(self) -> None:
        """Reset all mock state.

        Clears:
        - Recorded API calls
        - Response overrides
        - Error simulations
        - Job state
        - Search results
        - Export data
        """
        self.clear_calls()
        self.clear_overrides()
        self.clear_jobs()
        self._search_results.clear()
        self._oneshot_results.clear()
        self._export_data.clear()

    def __repr__(self) -> str:
        return f"MockSplunkClient(base_url={self.base_url!r})"


# ============================================================================
# Skill-Specific Mock Clients
# ============================================================================
# These provide minimal clients for focused testing of specific functionality.
# Use these when you only need a subset of the mock capabilities.


class MockSearchClient(SearchMixin, MockSplunkClientBase):
    """Mock client for search-only testing.

    Use when testing search execution without job lifecycle or metadata.

    Example:
        >>> client = MockSearchClient()
        >>> result = client.oneshot_search("index=main | head 10")
    """

    pass


class MockJobClient(JobMixin, MockSplunkClientBase):
    """Mock client for job lifecycle testing.

    Use when testing job management without search results or metadata.

    Example:
        >>> client = MockJobClient()
        >>> job = client.create_job("index=main | stats count")
        >>> status = client.get_job_status(job["sid"])
    """

    pass


class MockMetadataClient(MetadataMixin, MockSplunkClientBase):
    """Mock client for metadata discovery testing.

    Use when testing index/sourcetype discovery operations.

    Example:
        >>> client = MockMetadataClient()
        >>> indexes = client.list_indexes()
        >>> sourcetypes = client.list_sourcetypes(index="main")
    """

    pass


class MockAdminClient(AdminMixin, MockSplunkClientBase):
    """Mock client for administrative testing.

    Use when testing server info, user management, or token operations.

    Example:
        >>> client = MockAdminClient()
        >>> info = client.get_server_info()
        >>> user = client.whoami()
    """

    pass


class MockExportClient(ExportMixin, MockSplunkClientBase):
    """Mock client for export/streaming testing.

    Use when testing large data export operations.

    Example:
        >>> client = MockExportClient()
        >>> for chunk in client.export_results(sid, output_mode="csv"):
        ...     process(chunk)
    """

    pass


# ============================================================================
# Combination Mock Clients
# ============================================================================
# These combine related mixins for testing features that span multiple areas.


class MockSearchJobClient(SearchMixin, JobMixin, MockSplunkClientBase):
    """Mock client combining search and job functionality.

    Use when testing search execution with job lifecycle.

    Example:
        >>> client = MockSearchJobClient()
        >>> job = client.search_normal("index=main | stats count")
        >>> client.set_job_state(job["sid"], "DONE")
        >>> results = client.get_search_results(job["sid"])
    """

    pass


class MockSearchExportClient(SearchMixin, ExportMixin, MockSplunkClientBase):
    """Mock client combining search and export functionality.

    Use when testing search with result export.

    Example:
        >>> client = MockSearchExportClient()
        >>> job = client.search_normal("index=main | head 1000")
        >>> for chunk in client.export_results(job["sid"]):
        ...     write_to_file(chunk)
    """

    pass


class MockFullSearchClient(
    SearchMixin, JobMixin, ExportMixin, MetadataMixin, MockSplunkClientBase
):
    """Mock client with all search-related functionality.

    Use when testing comprehensive search workflows including
    job management, export, and metadata discovery.
    """

    pass


# ============================================================================
# Factory Functions
# ============================================================================


def create_mock_client(**kwargs: Any) -> MockSplunkClient:
    """Create a MockSplunkClient with default settings.

    Args:
        **kwargs: Override default settings

    Returns:
        Configured MockSplunkClient
    """
    defaults = {
        "base_url": "https://mock-splunk.example.com",
        "token": "mock-token",
        "port": 8089,
    }
    defaults.update(kwargs)
    return MockSplunkClient(**defaults)


def create_cloud_mock(**kwargs: Any) -> MockSplunkClient:
    """Create a MockSplunkClient configured as Splunk Cloud.

    Args:
        **kwargs: Override default settings

    Returns:
        Cloud-configured MockSplunkClient
    """
    defaults = {
        "base_url": "https://acme.splunkcloud.com",
        "token": "mock-cloud-token",
        "port": 8089,
    }
    defaults.update(kwargs)
    return MockSplunkClient(**defaults)


def create_minimal_mock(
    search: bool = False,
    job: bool = False,
    metadata: bool = False,
    admin: bool = False,
    export: bool = False,
    **kwargs: Any,
) -> MockSplunkClientBase:
    """Create a minimal mock client with only specified capabilities.

    Args:
        search: Include search functionality
        job: Include job functionality
        metadata: Include metadata functionality
        admin: Include admin functionality
        export: Include export functionality
        **kwargs: Client configuration

    Returns:
        Minimal mock client with requested capabilities

    Example:
        >>> # Just search and job
        >>> client = create_minimal_mock(search=True, job=True)
    """
    # Build mixin list dynamically
    mixins: list[type] = []
    if search:
        mixins.append(SearchMixin)
    if job:
        mixins.append(JobMixin)
    if metadata:
        mixins.append(MetadataMixin)
    if admin:
        mixins.append(AdminMixin)
    if export:
        mixins.append(ExportMixin)

    # Always include base class last
    mixins.append(MockSplunkClientBase)

    # Create dynamic class
    client_class = type("CustomMockClient", tuple(mixins), {})

    defaults = {
        "base_url": "https://mock-splunk.example.com",
        "token": "mock-token",
        "port": 8089,
    }
    defaults.update(kwargs)

    return client_class(**defaults)
