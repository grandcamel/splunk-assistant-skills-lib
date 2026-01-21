"""
Live Index Tests

Tests for index operations against a real Splunk instance.
Verifies that the mock factories match real API response types.
"""

import pytest


@pytest.mark.live
class TestIndexesLive:
    """Live tests for index operations."""

    def test_list_indexes(self, splunk_client):
        """Should list available indexes."""
        indexes = splunk_client.list_indexes()

        assert indexes is not None
        assert isinstance(indexes, list)
        # Default Splunk has at least 'main' index
        index_names = [idx.get("name") for idx in indexes]
        assert "main" in index_names or "_internal" in index_names

    def test_index_entry_types_match_mock(self, splunk_client):
        """Real API types should match our mock factories.

        This is the critical test that would have caught the type mismatch bug.
        The real Splunk API returns numeric fields as strings.
        """
        indexes = splunk_client.list_indexes()

        # Find any index with content
        for idx in indexes:
            content = idx.get("content", idx)

            # These fields are strings in the real API
            if "totalEventCount" in content:
                assert isinstance(content["totalEventCount"], str), (
                    f"totalEventCount should be string, got {type(content['totalEventCount'])}"
                )

            if "currentDBSizeMB" in content:
                assert isinstance(content["currentDBSizeMB"], str), (
                    f"currentDBSizeMB should be string, got {type(content['currentDBSizeMB'])}"
                )

            # disabled is "true" or "false" string in some API versions
            if "disabled" in content:
                # Can be bool or string depending on API version
                assert content["disabled"] in (True, False, "true", "false", "0", "1"), (
                    f"disabled has unexpected value: {content['disabled']}"
                )

    def test_get_index_details(self, splunk_client):
        """Should get details for a specific index."""
        # Use _internal which should always exist
        try:
            details = splunk_client.get_index("_internal")
            assert details is not None
        except Exception:
            # Try 'main' if '_internal' doesn't work
            details = splunk_client.get_index("main")
            assert details is not None


@pytest.mark.live
class TestIndexTypeFidelity:
    """Verify mock factory type fidelity against real API."""

    def test_compare_with_index_factory(self, splunk_client):
        """Compare real API response types with IndexFactory output."""
        from splunk_as.mock.factories import IndexFactory

        # Get real index data
        indexes = splunk_client.list_indexes()
        if not indexes:
            pytest.skip("No indexes available for comparison")

        real_index = indexes[0]
        real_content = real_index.get("content", real_index)

        # Get mock index data
        mock_entry = IndexFactory.index_entry("test")

        # Compare types for key numeric fields
        numeric_fields = ["totalEventCount", "currentDBSizeMB", "maxDataSizeMB"]

        for field in numeric_fields:
            if field in real_content and field in mock_entry:
                real_type = type(real_content[field])
                mock_type = type(mock_entry[field])
                assert real_type == mock_type, (
                    f"Type mismatch for {field}: "
                    f"real API returns {real_type.__name__}, "
                    f"mock returns {mock_type.__name__}"
                )
