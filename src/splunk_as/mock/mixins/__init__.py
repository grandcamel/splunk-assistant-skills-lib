"""
Mock Client Mixins

Each mixin provides realistic mock responses for a specific API area.
Combine mixins with MockSplunkClientBase to create custom mock clients.
"""

from .admin import AdminMixin
from .export import ExportMixin
from .job import JobMixin
from .metadata import MetadataMixin
from .search import SearchMixin

__all__ = [
    "SearchMixin",
    "JobMixin",
    "MetadataMixin",
    "AdminMixin",
    "ExportMixin",
]
