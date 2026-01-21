"""
Export Mixin for Mock Splunk Client

Provides mock responses for data export operations:
- Streaming result export
- CSV/JSON export
- Large dataset handling
"""

import json
from typing import Any, Dict, Generator, Iterator, List, Optional


class ExportMixin:
    """Mixin providing export-related mock methods.

    Simulates streaming data export for large result sets.

    Example:
        class MyMock(ExportMixin, MockSplunkClientBase):
            pass

        client = MyMock()
        for chunk in client.export_results(sid, output_mode="csv"):
            print(chunk)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize export mixin state."""
        super().__init__(*args, **kwargs)
        self._export_data: Dict[str, List[Dict[str, Any]]] = {}
        self._export_chunk_size: int = 1000

    def set_export_data(self, sid: str, data: List[Dict[str, Any]]) -> None:
        """Set export data for a job.

        Args:
            sid: Search job ID
            data: List of result dictionaries
        """
        self._export_data[sid] = data

    def set_export_chunk_size(self, size: int) -> None:
        """Set chunk size for export streaming.

        Args:
            size: Number of rows per chunk
        """
        self._export_chunk_size = size

    def export_results(
        self,
        sid: str,
        output_mode: str = "csv",
        count: int = 0,
        offset: int = 0,
        **kwargs: Any,
    ) -> Generator[bytes, None, None]:
        """Stream export results from a job.

        Args:
            sid: Search job ID
            output_mode: Output format (csv, json, xml)
            count: Maximum results (0 = all)
            offset: Starting offset

        Yields:
            Chunks of exported data as bytes
        """
        endpoint = f"/services/search/v2/jobs/{sid}/results"

        self._record_call(
            "STREAM",
            endpoint,
            params={"output_mode": output_mode, "count": count, "offset": offset},
        )

        # Get data from configured export data or search results
        data = self._export_data.get(sid)
        if data is None:
            # Try to get from search results if SearchMixin is available
            if hasattr(self, "_search_results"):
                data = getattr(self, "_search_results").get(sid, [])
            else:
                data = self._generate_default_export_data()

        # Apply count/offset
        if offset:
            data = data[offset:]
        if count > 0:
            data = data[:count]

        # Generate output based on format
        if output_mode == "csv":
            yield from self._export_csv(data)
        elif output_mode == "json":
            yield from self._export_json(data)
        elif output_mode == "json_rows":
            yield from self._export_json_rows(data)
        else:
            # Default to JSON
            yield from self._export_json(data)

    def export_results_to_file(
        self,
        sid: str,
        output_file: str,
        output_mode: str = "csv",
        count: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Export results directly to a file.

        Args:
            sid: Search job ID
            output_file: Output file path
            output_mode: Output format
            count: Maximum results

        Returns:
            Export summary with row count
        """
        self._record_call(
            "EXPORT_FILE",
            f"/services/search/v2/jobs/{sid}/results",
            data={
                "output_file": output_file,
                "output_mode": output_mode,
                "count": count,
            },
        )

        # Get result count
        data = self._export_data.get(sid, [])
        if not data and hasattr(self, "_search_results"):
            data = getattr(self, "_search_results").get(sid, [])

        return {
            "status": "success",
            "output_file": output_file,
            "rows_exported": len(data) if count == 0 else min(count, len(data)),
            "output_mode": output_mode,
        }

    def stream_export(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        output_mode: str = "csv",
        **kwargs: Any,
    ) -> Generator[bytes, None, None]:
        """Stream export directly from SPL (no job creation).

        Args:
            spl: SPL query
            earliest_time: Search start time
            latest_time: Search end time
            output_mode: Output format

        Yields:
            Chunks of exported data
        """
        self._record_call(
            "POST",
            "/services/search/jobs/export",
            data={
                "search": spl,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "output_mode": output_mode,
            },
        )

        # Generate default data for the SPL
        data = self._generate_default_export_data(spl)

        if output_mode == "csv":
            yield from self._export_csv(data)
        else:
            yield from self._export_json(data)

    def stream_json_lines(
        self,
        sid: str,
        count: int = 0,
        offset: int = 0,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """Stream results as JSON objects (one per line).

        Args:
            sid: Search job ID
            count: Maximum results
            offset: Starting offset

        Yields:
            Individual result dictionaries
        """
        endpoint = f"/services/search/v2/jobs/{sid}/results"

        self._record_call(
            "STREAM_JSON",
            endpoint,
            params={"output_mode": "json", "count": count, "offset": offset},
        )

        data = self._export_data.get(sid)
        if data is None and hasattr(self, "_search_results"):
            data = getattr(self, "_search_results").get(sid, [])
        if data is None:
            data = self._generate_default_export_data()

        # Apply count/offset
        if offset:
            data = data[offset:]
        if count > 0:
            data = data[:count]

        for row in data:
            yield row

    def _export_csv(
        self, data: List[Dict[str, Any]]
    ) -> Generator[bytes, None, None]:
        """Generate CSV export chunks.

        Args:
            data: Result data

        Yields:
            CSV data as bytes
        """
        if not data:
            yield b""
            return

        # Header row
        fields = list(data[0].keys())
        header = ",".join(f'"{f}"' for f in fields)
        yield (header + "\n").encode("utf-8")

        # Data rows in chunks
        chunk_rows = []
        for row in data:
            values = [str(row.get(f, "")) for f in fields]
            csv_row = ",".join(f'"{v}"' for v in values)
            chunk_rows.append(csv_row)

            if len(chunk_rows) >= self._export_chunk_size:
                yield ("\n".join(chunk_rows) + "\n").encode("utf-8")
                chunk_rows = []

        if chunk_rows:
            yield ("\n".join(chunk_rows) + "\n").encode("utf-8")

    def _export_json(
        self, data: List[Dict[str, Any]]
    ) -> Generator[bytes, None, None]:
        """Generate JSON export chunks.

        Args:
            data: Result data

        Yields:
            JSON data as bytes
        """
        response = {
            "preview": False,
            "init_offset": 0,
            "results": data,
        }
        yield json.dumps(response).encode("utf-8")

    def _export_json_rows(
        self, data: List[Dict[str, Any]]
    ) -> Generator[bytes, None, None]:
        """Generate JSON rows (one per line) export.

        Args:
            data: Result data

        Yields:
            JSON lines as bytes
        """
        for row in data:
            yield (json.dumps(row) + "\n").encode("utf-8")

    def _generate_default_export_data(
        self, spl: str = ""
    ) -> List[Dict[str, Any]]:
        """Generate default export data.

        Args:
            spl: Optional SPL to influence data generation

        Returns:
            List of mock result dictionaries
        """
        # Generate 100 rows of sample data
        results = []
        for i in range(100):
            results.append({
                "_time": f"2024-01-01T{12 + (i // 60):02d}:{i % 60:02d}:00",
                "_raw": f"Sample log event {i}",
                "host": f"server{(i % 5) + 1}",
                "source": "/var/log/app.log",
                "sourcetype": "app_logs",
                "index": "main",
                "linecount": "1",
                "splunk_server": "mock-splunk",
            })
        return results

    def _record_call(self, *args: Any, **kwargs: Any) -> None:
        """Record call - delegates to base class."""
        if hasattr(super(), "_record_call"):
            super()._record_call(*args, **kwargs)  # type: ignore[misc]
