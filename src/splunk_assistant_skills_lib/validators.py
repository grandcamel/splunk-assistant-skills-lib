#!/usr/bin/env python3
"""
Splunk-Specific Input Validators

Provides validation functions for Splunk-specific formats and values.
All validators return the validated value or raise ValidationError.
"""

import re
from typing import List, Optional, Union

from assistant_skills_lib.error_handler import ValidationError
from assistant_skills_lib.validators import (
    validate_choice,
    validate_int,
    validate_list,
    validate_required,
)
from assistant_skills_lib.validators import validate_url as base_validate_url


def validate_sid(sid: str) -> str:
    """
    Validate Splunk Search ID (SID) format.
    """
    sid = validate_required(sid, "sid")
    sid_pattern = r"^(\d+\.\d+(_\w+)?|scheduler__\w+__\w+__\w+__\w+__\w+)$"
    if not re.match(sid_pattern, sid):
        raise ValidationError(
            f"Invalid SID format: {sid}",
            operation="validation",
            details={"field": "sid"},
        )
    return sid


def validate_spl(spl: str) -> str:
    """
    Validate SPL (Search Processing Language) query.
    """
    spl = validate_required(spl, "spl")
    if (
        spl.count('"') % 2 != 0
        or spl.count("'") % 2 != 0
        or spl.count("(") != spl.count(")")
    ):
        raise ValidationError(
            "SPL has unbalanced quotes or parentheses",
            operation="validation",
            details={"field": "spl"},
        )
    if "||" in spl.replace(" ", ""):
        raise ValidationError(
            "Empty pipe segment (||)", operation="validation", details={"field": "spl"}
        )
    if spl.rstrip().endswith("|"):
        raise ValidationError(
            "SPL cannot end with a pipe",
            operation="validation",
            details={"field": "spl"},
        )
    return spl


def validate_time_modifier(time_str: str) -> str:
    """
    Validate Splunk time modifier format.
    """
    time_str = validate_required(time_str, "time").lower()
    if time_str in ("now", "now()", "earliest", "latest", "0") or time_str.isdigit():
        return time_str

    patterns = [
        r"^[+-]?\d+[smhdwMy](@[smhdwMy]?\d*)?$",
        r"^@[smhdwMy]\d*$",
        r"^@w[0-6]$",
        r"^@(mon|q\d?|y)$",
        r"^[+-]?\d+[smhdwMy]@[smhdwMy0-6]?\d*$",
    ]
    if any(re.match(p, time_str, re.IGNORECASE) for p in patterns):
        return time_str

    raise ValidationError(
        f"Invalid time modifier format: {time_str}",
        operation="validation",
        details={"field": "time"},
    )


def validate_index_name(index: str) -> str:
    """
    Validate Splunk index name.
    """
    index = validate_required(index, "index")
    if len(index) > 80:
        raise ValidationError(
            "Index name cannot exceed 80 characters",
            operation="validation",
            details={"field": "index"},
        )
    pattern = r"^[a-zA-Z_][a-zA-Z0-9_-]*$"
    if not re.match(pattern, index):
        raise ValidationError(
            f"Invalid index name: {index}",
            operation="validation",
            details={"field": "index"},
        )
    return index


def validate_app_name(app: str) -> str:
    """
    Validate Splunk app name.
    """
    app = validate_required(app, "app")
    if len(app) > 80:
        raise ValidationError(
            "App name cannot exceed 80 characters",
            operation="validation",
            details={"field": "app"},
        )
    pattern = r"^[a-zA-Z][a-zA-Z0-9_]*$"
    if not re.match(pattern, app):
        raise ValidationError(
            f"Invalid app name: {app}",
            operation="validation",
            details={"field": "app"},
        )
    return app


def validate_port(port: Union[int, str]) -> int:
    """Validate port number."""
    return validate_int(port, "port", min_value=1, max_value=65535)


def validate_url(url: str, require_https: bool = False) -> str:
    """Validate URL format using the base validator."""
    return base_validate_url(url, "url", require_https)


def validate_output_mode(mode: str) -> str:
    """Validate Splunk output mode."""
    return validate_choice(mode, ["json", "csv", "xml", "raw"], "output_mode")


def validate_count(count: Union[int, str]) -> int:
    """Validate result count parameter."""
    return validate_int(count, "count", min_value=0)


def validate_offset(offset: Union[int, str]) -> int:
    """Validate result offset parameter."""
    return validate_int(offset, "offset", min_value=0)


def validate_field_list(fields: Union[str, List[str]]) -> List[str]:
    """Validate and normalize field list."""
    items = (
        validate_list(fields, "fields", min_items=1)
        if isinstance(fields, str)
        else fields
    )
    for field in items:
        if not re.match(r"^[\w.:]+$", field):
            raise ValidationError(
                f"Invalid field name: {field}",
                operation="validation",
                details={"field": "fields"},
            )
    return items


def validate_search_mode(mode: str) -> str:
    """Validate search execution mode."""
    return validate_choice(mode, ["normal", "blocking", "oneshot"], "exec_mode")
