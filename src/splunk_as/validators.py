#!/usr/bin/env python3
"""
Splunk-Specific Input Validators

Provides validation functions for Splunk-specific formats and values.
All validators return the validated value or raise ValidationError.
"""

import re
from typing import List, Optional, Union, cast

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
    return cast(int, validate_int(port, "port", min_value=1, max_value=65535))


def validate_url(url: str, require_https: bool = False) -> str:
    """Validate URL format using the base validator."""
    return cast(str, base_validate_url(url, "url", require_https))


def validate_output_mode(mode: str) -> str:
    """Validate Splunk output mode."""
    return cast(
        str, validate_choice(mode, ["json", "csv", "xml", "raw"], "output_mode")
    )


def validate_count(count: Union[int, str]) -> int:
    """Validate result count parameter."""
    return cast(int, validate_int(count, "count", min_value=0))


def validate_offset(offset: Union[int, str]) -> int:
    """Validate result offset parameter."""
    return cast(int, validate_int(offset, "offset", min_value=0))


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
    return cast(
        str, validate_choice(mode, ["normal", "blocking", "oneshot"], "exec_mode")
    )


def validate_file_path(file_path: str, param_name: str = "file_path") -> str:
    """
    Validate file path to prevent directory traversal attacks.

    Args:
        file_path: Path to validate
        param_name: Parameter name for error messages

    Returns:
        Validated file path

    Raises:
        ValidationError: If path contains traversal attempts or is a symlink
    """
    from pathlib import Path

    file_path = validate_required(file_path, param_name)

    # Check for explicit path traversal patterns
    if ".." in file_path:
        raise ValidationError(
            f"Path traversal detected in {param_name}: '..' not allowed",
            operation="validation",
            details={"field": param_name},
        )

    path = Path(file_path)

    # Reject symlinks to prevent symlink-based path traversal
    if path.is_symlink():
        raise ValidationError(
            f"Symlinks not allowed in {param_name}",
            operation="validation",
            details={"field": param_name},
        )

    if path.is_absolute():
        # For absolute paths, just check no .. components
        for part in path.parts:
            if part == "..":
                raise ValidationError(
                    f"Path traversal detected in {param_name}",
                    operation="validation",
                    details={"field": param_name},
                )
    else:
        # For relative paths, ensure it doesn't escape current directory
        try:
            # Resolve relative to current working directory
            resolved = path.resolve()
            cwd = Path.cwd().resolve()
            # Check the resolved path is within or at cwd
            resolved.relative_to(cwd)
        except ValueError:
            raise ValidationError(
                f"Path {param_name} would escape current directory",
                operation="validation",
                details={"field": param_name},
            )

    return file_path


def validate_path_component(component: str, param_name: str = "name") -> str:
    """
    Validate and sanitize a path component for use in URLs.

    Prevents path injection by rejecting components with path separators
    or traversal patterns. Returns URL-encoded component.

    Args:
        component: Path component to validate (e.g., app name, lookup name)
        param_name: Parameter name for error messages

    Returns:
        URL-encoded path component

    Raises:
        ValidationError: If component contains disallowed characters
    """
    from urllib.parse import quote

    component = validate_required(component, param_name)

    # Reject path traversal and separator characters
    if ".." in component:
        raise ValidationError(
            f"Path traversal detected in {param_name}: '..' not allowed",
            operation="validation",
            details={"field": param_name},
        )

    if "/" in component or "\\" in component:
        raise ValidationError(
            f"Path separators not allowed in {param_name}",
            operation="validation",
            details={"field": param_name},
        )

    # URL-encode to prevent any special character issues
    return quote(component, safe="")
