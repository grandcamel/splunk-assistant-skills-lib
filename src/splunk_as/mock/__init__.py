"""
Mock Splunk Client Module

Provides mixin-based mock clients for testing Splunk skills without
a live Splunk instance. Uses a composable mixin architecture to
allow selective testing of different API areas.

Example usage:
    # Full mock client with all mixins
    from splunk_as.mock import MockSplunkClient

    client = MockSplunkClient()
    result = client.oneshot_search("index=main | head 10")

    # Check if mock mode is enabled via environment variable
    from splunk_as.mock import is_mock_mode

    if is_mock_mode():
        client = MockSplunkClient()
    else:
        client = SplunkClient(...)

    # Skill-specific minimal clients
    from splunk_as.mock import MockSearchClient, MockJobClient

    search_client = MockSearchClient()  # Only search functionality
    job_client = MockJobClient()        # Only job lifecycle

    # Custom mock with specific mixins
    from splunk_as.mock.base import MockSplunkClientBase
    from splunk_as.mock.mixins import SearchMixin, JobMixin

    class CustomMock(SearchMixin, JobMixin, MockSplunkClientBase):
        pass

    client = CustomMock()

    # Use factories for consistent response structures
    from splunk_as.mock.factories import (
        ResponseFactory,
        JobFactory,
        ResultFactory,
    )

    client.set_response("/some/endpoint", ResponseFactory.paginated(items))
"""

# Base class and environment check
from .base import MockSplunkClientBase, is_mock_mode

# Full and composed clients
from .client import (
    MockSplunkClient,
    # Skill-specific clients
    MockSearchClient,
    MockJobClient,
    MockMetadataClient,
    MockAdminClient,
    MockExportClient,
    # Combination clients
    MockSearchJobClient,
    MockSearchExportClient,
    MockFullSearchClient,
    # Factory functions
    create_mock_client,
    create_cloud_mock,
    create_minimal_mock,
)

# Mixins for custom client composition
from .mixins.admin import AdminMixin
from .mixins.export import ExportMixin
from .mixins.job import JobMixin
from .mixins.metadata import MetadataMixin
from .mixins.search import SearchMixin

# Response factories
from .factories import (
    ResponseFactory,
    JobFactory,
    IndexFactory,
    UserFactory,
    TimestampFactory,
    ResultFactory,
)

# Protocols for type checking
from .protocols import (
    MockClientProtocol,
    SearchMixinProtocol,
    JobMixinProtocol,
    MetadataMixinProtocol,
    AdminMixinProtocol,
    ExportMixinProtocol,
)

__all__ = [
    # Core
    "MockSplunkClient",
    "MockSplunkClientBase",
    "is_mock_mode",
    # Skill-specific clients
    "MockSearchClient",
    "MockJobClient",
    "MockMetadataClient",
    "MockAdminClient",
    "MockExportClient",
    # Combination clients
    "MockSearchJobClient",
    "MockSearchExportClient",
    "MockFullSearchClient",
    # Factory functions
    "create_mock_client",
    "create_cloud_mock",
    "create_minimal_mock",
    # Mixins
    "SearchMixin",
    "JobMixin",
    "MetadataMixin",
    "AdminMixin",
    "ExportMixin",
    # Response factories
    "ResponseFactory",
    "JobFactory",
    "IndexFactory",
    "UserFactory",
    "TimestampFactory",
    "ResultFactory",
    # Protocols
    "MockClientProtocol",
    "SearchMixinProtocol",
    "JobMixinProtocol",
    "MetadataMixinProtocol",
    "AdminMixinProtocol",
    "ExportMixinProtocol",
]
