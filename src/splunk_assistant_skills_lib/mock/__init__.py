"""
Mock Splunk Client Module

Provides mixin-based mock clients for testing Splunk skills without
a live Splunk instance. Uses a composable mixin architecture to
allow selective testing of different API areas.

Example usage:
    from splunk_assistant_skills_lib.mock import MockSplunkClient

    # Full mock client with all mixins
    client = MockSplunkClient()

    # Custom mock with specific mixins
    from splunk_assistant_skills_lib.mock.base import MockSplunkClientBase
    from splunk_assistant_skills_lib.mock.mixins import SearchMixin, JobMixin

    class CustomMock(SearchMixin, JobMixin, MockSplunkClientBase):
        pass

    client = CustomMock()
"""

from .base import MockSplunkClientBase, is_mock_mode
from .client import MockSplunkClient
from .mixins.admin import AdminMixin
from .mixins.job import JobMixin
from .mixins.metadata import MetadataMixin
from .mixins.search import SearchMixin

__all__ = [
    "MockSplunkClient",
    "MockSplunkClientBase",
    "is_mock_mode",
    "SearchMixin",
    "JobMixin",
    "MetadataMixin",
    "AdminMixin",
]
