#!/usr/bin/env python3
"""
Splunk Output Formatters

Provides formatting utilities for Splunk data and command output.
"""

from typing import Any, Dict, List, Optional, Union

# Import generic formatters and color utilities from the base library
from assistant_skills_lib.formatters import (
    Colors,
    _colorize,
    _supports_color,
    export_csv,
    format_count,
    format_file_size,
    format_json,
    format_large_number,
    format_list,
    format_table,
    format_timestamp,
)
from assistant_skills_lib.formatters import get_csv_string as export_csv_string
from assistant_skills_lib.formatters import (
    print_error,
    print_info,
    print_success,
    print_warning,
)

# Re-export with public names expected by __init__.py
colorize = _colorize
supports_color = _supports_color
format_bytes = format_file_size


def format_search_results(
    results: Union[Dict[str, Any], List[Dict[str, Any]]],
    fields: Optional[List[str]] = None,
    max_results: int = 50,
    output_format: str = "table",
) -> str:
    """
    Format search results for display.
    """
    if isinstance(results, dict):
        result_list = results.get("results", results.get("rows", []))
        if not result_list and "entry" in results:
            result_list = [e.get("content", {}) for e in results["entry"]]
    else:
        result_list = results

    if not result_list:
        return "No results found."

    truncated = False
    if len(result_list) > max_results:
        result_list = result_list[:max_results]
        truncated = True

    if fields is None and result_list:
        fields = [k for k in result_list[0].keys() if not k.startswith("_")][:10]

    if output_format == "json":
        output = format_json(result_list)
    elif output_format == "csv":
        output = export_csv_string(result_list, fields)
    else:
        output = format_table(result_list, columns=fields)

    if truncated:
        output += f"\n\n... (showing first {max_results} of more results)"

    return output


def format_job_status(job: Dict[str, Any]) -> str:
    """
    Format search job status for display.
    """
    content = job.get("content", job)
    sid = content.get("sid", "Unknown")
    state = content.get("dispatchState", "Unknown")
    state_colors = {
        "QUEUED": Colors.YELLOW,
        "PARSING": Colors.YELLOW,
        "RUNNING": Colors.BLUE,
        "FINALIZING": Colors.CYAN,
        "DONE": Colors.GREEN,
        "FAILED": Colors.RED,
        "PAUSED": Colors.MAGENTA,
    }
    state_color = state_colors.get(state, Colors.RESET)

    lines = [
        f"Job ID:     {sid}",
        f"State:      {_colorize(state, state_color)}",
        f"Progress:   {content.get('doneProgress', 0) * 100:.1f}%",
        f"Events:     {content.get('eventCount', 0):,}",
        f"Results:    {content.get('resultCount', 0):,}",
        f"Scanned:    {content.get('scanCount', 0):,}",
        f"Duration:   {content.get('runDuration', 0):.2f}s",
    ]

    if state == "FAILED" and (messages := content.get("messages", [])):
        lines.append(f"Error:      {messages[0].get('text', 'Unknown error')}")

    return "\n".join(lines)


def format_metadata(meta: Dict[str, Any]) -> str:
    """
    Format metadata information for display.
    """
    lines = []
    if "totalEventCount" in meta:
        lines.extend(
            [
                f"Index:           {meta.get('title', meta.get('name', 'Unknown'))}",
                f"Total Events:    {meta.get('totalEventCount', 0):,}",
                f"Total Size:      {format_file_size(meta.get('currentDBSizeMB', 0) * 1024 * 1024)}",
                f"Earliest Event:  {format_splunk_time(meta.get('minTime', ''))}",
                f"Latest Event:    {format_splunk_time(meta.get('maxTime', ''))}",
            ]
        )
    elif "values" in meta:
        lines.append(f"Field:    {meta.get('field', 'Unknown')}")
        lines.append(f"Values:   {len(meta.get('values', []))}")
        for v in meta.get("values", [])[:10]:
            lines.append(f"  - {v.get('value', v)}: {v.get('count', 0):,}")
    else:
        for key, value in meta.items():
            if not key.startswith("_"):
                lines.append(f"{key}: {value}")
    return "\n".join(lines)


def format_saved_search(search: Dict[str, Any]) -> str:
    """
    Format saved search details for display.
    """
    content = search.get("content", search)
    lines = [
        f"Name:           {search.get('name', content.get('name', 'Unknown'))}",
        f"App:            {content.get('eai:acl', {}).get('app', 'Unknown')}",
        f"Owner:          {content.get('eai:acl', {}).get('owner', 'Unknown')}",
        f"Search:         {content.get('search', 'N/A')[:80]}...",
        f"Disabled:       {content.get('disabled', False)}",
        f"Scheduled:      {content.get('is_scheduled', False)}",
    ]
    if content.get("is_scheduled"):
        lines.extend(
            [
                f"Cron:           {content.get('cron_schedule', 'N/A')}",
                f"Next Run:       {content.get('next_scheduled_time', 'N/A')}",
            ]
        )
    return "\n".join(lines)


def format_splunk_time(time_str: str) -> str:
    """
    Format Splunk timestamp for display.
    """
    return format_timestamp(time_str, "%Y-%m-%d %H:%M:%S")


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"
