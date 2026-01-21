"""
Metadata Mixin for Mock Splunk Client

Provides mock responses for metadata discovery operations:
- Index listing and info
- Sourcetype discovery
- Source discovery
- Field summary
"""

from typing import Any, Dict, List, Optional


class MetadataMixin:
    """Mixin providing metadata discovery mock methods.

    Maintains internal state for indexes, sourcetypes, and sources.

    Example:
        class MyMock(MetadataMixin, MockSplunkClientBase):
            pass

        client = MyMock()
        indexes = client.list_indexes()
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize metadata mixin state."""
        super().__init__(*args, **kwargs)
        self._indexes: Dict[str, Dict[str, Any]] = {
            "main": {
                "name": "main",
                "totalEventCount": 1000000,
                "currentDBSizeMB": 1024,
                "maxDataSizeMB": 500000,
                "disabled": False,
                "minTime": "2024-01-01T00:00:00",
                "maxTime": "2024-01-15T23:59:59",
            },
            "_internal": {
                "name": "_internal",
                "totalEventCount": 500000,
                "currentDBSizeMB": 256,
                "maxDataSizeMB": 500000,
                "disabled": False,
                "minTime": "2024-01-01T00:00:00",
                "maxTime": "2024-01-15T23:59:59",
            },
            "_audit": {
                "name": "_audit",
                "totalEventCount": 100000,
                "currentDBSizeMB": 64,
                "maxDataSizeMB": 500000,
                "disabled": False,
                "minTime": "2024-01-01T00:00:00",
                "maxTime": "2024-01-15T23:59:59",
            },
        }
        self._sourcetypes: Dict[str, List[str]] = {
            "main": ["access_combined", "syslog", "app_logs", "json"],
            "_internal": ["splunk_web_access", "splunkd", "scheduler"],
            "_audit": ["audittrail"],
        }
        self._sources: Dict[str, List[str]] = {
            "main": [
                "/var/log/access.log",
                "/var/log/syslog",
                "/app/logs/app.log",
            ],
            "_internal": [
                "/opt/splunk/var/log/splunk/web_access.log",
                "/opt/splunk/var/log/splunk/splunkd.log",
            ],
        }
        self._fields: Dict[str, List[Dict[str, Any]]] = {}

    def add_index(
        self,
        name: str,
        event_count: int = 0,
        size_mb: int = 0,
        disabled: bool = False,
    ) -> None:
        """Add a mock index.

        Args:
            name: Index name
            event_count: Total event count
            size_mb: Current size in MB
            disabled: Whether index is disabled
        """
        self._indexes[name] = {
            "name": name,
            "totalEventCount": event_count,
            "currentDBSizeMB": size_mb,
            "maxDataSizeMB": 500000,
            "disabled": disabled,
            "minTime": "2024-01-01T00:00:00",
            "maxTime": "2024-01-15T23:59:59",
        }

    def add_sourcetype(self, index: str, sourcetype: str) -> None:
        """Add a sourcetype to an index.

        Args:
            index: Index name
            sourcetype: Sourcetype name
        """
        if index not in self._sourcetypes:
            self._sourcetypes[index] = []
        if sourcetype not in self._sourcetypes[index]:
            self._sourcetypes[index].append(sourcetype)

    def add_source(self, index: str, source: str) -> None:
        """Add a source to an index.

        Args:
            index: Index name
            source: Source path
        """
        if index not in self._sources:
            self._sources[index] = []
        if source not in self._sources[index]:
            self._sources[index].append(source)

    def set_field_summary(
        self,
        index: str,
        sourcetype: Optional[str],
        fields: List[Dict[str, Any]],
    ) -> None:
        """Set field summary for an index/sourcetype combination.

        Args:
            index: Index name
            sourcetype: Sourcetype (or None for all)
            fields: List of field summaries
        """
        key = f"{index}:{sourcetype or '*'}"
        self._fields[key] = fields

    def list_indexes(
        self,
        count: int = 30,
        offset: int = 0,
        search: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List available indexes.

        Args:
            count: Maximum results
            offset: Pagination offset
            search: Filter by name

        Returns:
            Index list response
        """
        self._record_call(
            "GET",
            "/services/data/indexes",
            params={"count": count, "offset": offset, "search": search},
        )

        indexes = list(self._indexes.values())

        if search:
            indexes = [i for i in indexes if search.lower() in i["name"].lower()]

        # Paginate
        paginated = indexes[offset : offset + count]

        return {
            "entry": [{"name": i["name"], "content": i} for i in paginated],
            "paging": {
                "total": len(indexes),
                "offset": offset,
                "count": len(paginated),
            },
        }

    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """Get details for a specific index.

        Args:
            index_name: Index name

        Returns:
            Index information
        """
        endpoint = f"/services/data/indexes/{index_name}"

        self._record_call("GET", endpoint)

        index = self._indexes.get(index_name)
        if not index:
            return {"entry": []}

        return {"entry": [{"name": index_name, "content": index}]}

    def list_sourcetypes(
        self,
        index: Optional[str] = None,
        count: int = 100,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List sourcetypes, optionally filtered by index.

        Args:
            index: Filter by index name
            count: Maximum results

        Returns:
            Sourcetype list with counts
        """
        self._record_call(
            "GET",
            "/services/saved/sourcetypes",
            params={"index": index, "count": count},
        )

        if index:
            sourcetypes = self._sourcetypes.get(index, [])
        else:
            # Merge all sourcetypes
            all_st: set[str] = set()
            for st_list in self._sourcetypes.values():
                all_st.update(st_list)
            sourcetypes = list(all_st)

        # Build response with mock counts
        return {
            "entry": [
                {
                    "name": st,
                    "content": {
                        "sourcetype": st,
                        "totalCount": 10000 + i * 1000,
                        "firstTime": "2024-01-01T00:00:00",
                        "lastTime": "2024-01-15T23:59:59",
                    },
                }
                for i, st in enumerate(sourcetypes[:count])
            ]
        }

    def list_sources(
        self,
        index: Optional[str] = None,
        count: int = 100,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List sources, optionally filtered by index.

        Args:
            index: Filter by index name
            count: Maximum results

        Returns:
            Source list with counts
        """
        self._record_call(
            "GET",
            "/services/data/indexes",  # Sources come from search
            params={"index": index, "count": count},
        )

        if index:
            sources = self._sources.get(index, [])
        else:
            all_src: set[str] = set()
            for src_list in self._sources.values():
                all_src.update(src_list)
            sources = list(all_src)

        return {
            "entry": [
                {
                    "name": src,
                    "content": {
                        "source": src,
                        "totalCount": 5000 + i * 500,
                    },
                }
                for i, src in enumerate(sources[:count])
            ]
        }

    def get_field_summary(
        self,
        index: str = "main",
        sourcetype: Optional[str] = None,
        earliest: str = "-24h",
        latest: str = "now",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get field summary for an index/sourcetype.

        Args:
            index: Index name
            sourcetype: Sourcetype filter
            earliest: Start time
            latest: End time

        Returns:
            Field summary with stats
        """
        self._record_call(
            "POST",
            "/services/search/jobs/oneshot",
            data={
                "search": f"index={index} | fieldsummary",
                "earliest_time": earliest,
                "latest_time": latest,
            },
        )

        key = f"{index}:{sourcetype or '*'}"
        fields = self._fields.get(key)

        if not fields:
            # Return default fields
            fields = [
                {
                    "field": "_time",
                    "count": 1000,
                    "distinct_count": 1000,
                    "is_exact": True,
                    "numeric_count": 0,
                },
                {
                    "field": "host",
                    "count": 1000,
                    "distinct_count": 5,
                    "is_exact": True,
                    "numeric_count": 0,
                    "values": [
                        {"value": "server1", "count": 300},
                        {"value": "server2", "count": 300},
                        {"value": "server3", "count": 200},
                        {"value": "server4", "count": 100},
                        {"value": "server5", "count": 100},
                    ],
                },
                {
                    "field": "source",
                    "count": 1000,
                    "distinct_count": 3,
                    "is_exact": True,
                    "numeric_count": 0,
                },
                {
                    "field": "sourcetype",
                    "count": 1000,
                    "distinct_count": 2,
                    "is_exact": True,
                    "numeric_count": 0,
                },
                {
                    "field": "_raw",
                    "count": 1000,
                    "distinct_count": 1000,
                    "is_exact": False,
                    "numeric_count": 0,
                },
            ]

        return {"results": fields}

    def metadata_search(
        self,
        metadata_type: str = "sourcetypes",
        index: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute metadata command.

        Args:
            metadata_type: Type (sourcetypes, sources, hosts)
            index: Index filter

        Returns:
            Metadata search results
        """
        spl = f"| metadata type={metadata_type}"
        if index:
            spl += f" index={index}"

        self._record_call(
            "POST",
            "/services/search/jobs/oneshot",
            data={"search": spl},
        )

        if metadata_type == "sourcetypes":
            return self.list_sourcetypes(index=index)
        elif metadata_type == "sources":
            return self.list_sources(index=index)
        else:
            return {"entry": []}

    def _record_call(self, *args: Any, **kwargs: Any) -> None:
        """Record call - delegates to base class."""
        if hasattr(super(), "_record_call"):
            super()._record_call(*args, **kwargs)  # type: ignore[misc]
