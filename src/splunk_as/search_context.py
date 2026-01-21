#!/usr/bin/env python3
"""
Search context loader for Splunk Assistant Skills.

Provides lazy loading and caching of index-specific context including
metadata, search patterns, and defaults. Context is loaded from:
1. Environment variables (highest priority)
2. settings.local.json (personal overrides)
3. Skill directories (.claude/skills/splunk-index-{INDEX}/)
4. Hardcoded defaults (fallback)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Module-level cache for session persistence
_context_cache: dict[str, "SearchContext"] = {}


@dataclass
class SearchContext:
    """Structured search context data for an index."""

    index: str
    earliest_time: str = "-24h"
    latest_time: str = "now"
    app: str | None = None
    owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    patterns: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    source: str = "none"  # 'skill', 'settings', 'merged', 'none'
    discovered_at: str | None = None

    def has_context(self) -> bool:
        """Check if any context data is available."""
        return bool(self.metadata or self.patterns or self.defaults)

    def get_sourcetypes(self) -> list[str]:
        """Get available sourcetypes for this index."""
        return self.metadata.get("sourcetypes", [])

    def get_hosts(self) -> list[str]:
        """Get available hosts for this index."""
        return self.metadata.get("hosts", [])

    def get_sources(self) -> list[str]:
        """Get available sources for this index."""
        return self.metadata.get("sources", [])

    def get_fields(self) -> list[dict[str, Any]]:
        """Get commonly used fields for this index."""
        return self.metadata.get("fields", [])

    def get_event_count(self) -> int | None:
        """Get approximate event count if discovered."""
        return self.metadata.get("event_count")


def get_skills_root() -> Path:
    """Get the root path of the skills directory."""
    # Look for .claude directory in current working directory or parents
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        claude_dir = parent / ".claude"
        if claude_dir.exists():
            return claude_dir
    return cwd / ".claude"


def get_index_skill_path(index_name: str) -> Path:
    """Get the path to an index-specific skill directory."""
    return get_skills_root() / "skills" / f"splunk-index-{index_name}"


def load_json_file(path: Path) -> dict[str, Any] | None:
    """Load a JSON file if it exists."""
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def load_skill_context(index_name: str) -> dict[str, Any] | None:
    """
    Load context from an index skill directory.

    Looks for .claude/skills/splunk-index-{INDEX}/context/

    Returns:
        Dict with 'metadata', 'patterns', 'defaults' keys
        or None if skill directory doesn't exist
    """
    skill_path = get_index_skill_path(index_name)

    if not skill_path.exists():
        return None

    context: dict[str, Any] = {}

    # Load context files
    context_dir = skill_path / "context"
    if context_dir.exists():
        metadata = load_json_file(context_dir / "metadata.json")
        if metadata:
            context["metadata"] = metadata

        patterns = load_json_file(context_dir / "patterns.json")
        if patterns:
            context["patterns"] = patterns

    # Load defaults from skill root
    defaults = load_json_file(skill_path / "defaults.json")
    if defaults:
        context["defaults"] = defaults

    return context if context else None


def load_settings_context(index_name: str) -> dict[str, Any] | None:
    """
    Load context overrides from settings.local.json.

    Looks for:
    {
      "splunk": {
        "indexes": {
          "{INDEX_NAME}": {
            "defaults": { ... },
            "metadata": { ... }  # optional overrides
          }
        }
      }
    }

    Returns:
        Dict with context overrides or None if not configured
    """
    # Find settings.local.json
    settings_path = get_skills_root().parent / "settings.local.json"

    if not settings_path.exists():
        settings_path = get_skills_root() / "settings.local.json"

    if not settings_path.exists():
        return None

    settings = load_json_file(settings_path)
    if not settings:
        return None

    # Navigate to index config
    splunk_config = settings.get("splunk", {})
    indexes = splunk_config.get("indexes", {})
    index_config = indexes.get(index_name, {})

    if not index_config:
        return None

    return index_config


def merge_contexts(
    skill_ctx: dict[str, Any] | None, settings_ctx: dict[str, Any] | None
) -> tuple[dict[str, Any], str]:
    """
    Merge settings overrides on top of skill context.

    Returns:
        Tuple of (merged_context, source_string)
    """
    if not skill_ctx and not settings_ctx:
        return {}, "none"

    if not skill_ctx:
        assert settings_ctx is not None
        return settings_ctx, "settings"

    if not settings_ctx:
        return skill_ctx, "skill"

    # Deep merge settings on top of skill context
    merged: dict[str, Any] = {}

    for key in ["metadata", "patterns", "defaults"]:
        skill_data = skill_ctx.get(key, {})
        settings_data = settings_ctx.get(key, {})

        if skill_data and settings_data:
            merged[key] = _deep_merge(skill_data, settings_data)
        elif settings_data:
            merged[key] = settings_data
        elif skill_data:
            merged[key] = skill_data

    return merged, "merged"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override dict into base dict."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def get_search_context(
    index_name: str, force_refresh: bool = False
) -> SearchContext:
    """
    Lazy-load search context with caching.

    Priority:
    1. Check memory cache (unless force_refresh)
    2. Load from skill directory
    3. Merge with settings.local.json overrides
    4. Cache in memory

    Args:
        index_name: Splunk index name (e.g., 'main', 'security')
        force_refresh: If True, bypass cache and reload

    Returns:
        SearchContext with merged data from all sources
    """
    global _context_cache

    cache_key = index_name

    # Check cache unless force refresh
    if not force_refresh and cache_key in _context_cache:
        return _context_cache[cache_key]

    # Load from sources
    skill_ctx = load_skill_context(index_name)
    settings_ctx = load_settings_context(index_name)

    # Merge contexts
    merged, source = merge_contexts(skill_ctx, settings_ctx)

    # Extract discovered_at timestamp
    discovered_at = None
    if merged.get("metadata", {}).get("discovered_at"):
        discovered_at = merged["metadata"]["discovered_at"]

    # Extract time range defaults
    defaults = merged.get("defaults", {})
    earliest_time = defaults.get("earliest_time", "-24h")
    latest_time = defaults.get("latest_time", "now")
    app = defaults.get("app")
    owner = defaults.get("owner")

    # Create context object
    context = SearchContext(
        index=index_name,
        earliest_time=earliest_time,
        latest_time=latest_time,
        app=app,
        owner=owner,
        metadata=merged.get("metadata", {}),
        patterns=merged.get("patterns", {}),
        defaults=defaults,
        source=source,
        discovered_at=discovered_at,
    )

    # Cache and return
    _context_cache[cache_key] = context
    return context


def clear_context_cache(index_name: str | None = None) -> None:
    """
    Clear the context cache.

    Args:
        index_name: If specified, only clear cache for this index.
                    If None, clear all cached contexts.
    """
    global _context_cache

    if index_name is None:
        _context_cache.clear()
    elif index_name in _context_cache:
        del _context_cache[index_name]


def get_search_defaults(context: SearchContext) -> dict[str, Any]:
    """
    Get search defaults from context.

    Args:
        context: SearchContext object

    Returns:
        Dict with default values: earliest_time, latest_time, app, owner, etc.
    """
    return {
        "earliest_time": context.earliest_time,
        "latest_time": context.latest_time,
        "app": context.app,
        "owner": context.owner,
        **context.defaults,
    }


def get_common_sourcetypes(context: SearchContext, limit: int = 10) -> list[str]:
    """
    Get the most commonly used sourcetypes.

    Args:
        context: SearchContext object
        limit: Maximum number of sourcetypes to return

    Returns:
        List of sourcetype strings, sorted by frequency
    """
    patterns = context.patterns
    sourcetypes = patterns.get("sourcetypes", {})

    # Sort by count and return top N
    sorted_sourcetypes = sorted(sourcetypes.items(), key=lambda x: x[1], reverse=True)
    return [st for st, _ in sorted_sourcetypes[:limit]]


def get_common_fields(context: SearchContext, limit: int = 20) -> list[str]:
    """
    Get the most commonly used fields.

    Args:
        context: SearchContext object
        limit: Maximum number of fields to return

    Returns:
        List of field names, sorted by frequency
    """
    patterns = context.patterns
    fields = patterns.get("fields", {})

    # Sort by count and return top N
    sorted_fields = sorted(fields.items(), key=lambda x: x[1], reverse=True)
    return [f for f, _ in sorted_fields[:limit]]


def suggest_spl_prefix(context: SearchContext) -> str:
    """
    Suggest an SPL search prefix based on context.

    Args:
        context: SearchContext object

    Returns:
        SPL prefix string (e.g., 'index=main sourcetype=syslog')
    """
    parts = [f"index={context.index}"]

    # Add most common sourcetype if available
    common_sourcetypes = get_common_sourcetypes(context, limit=1)
    if common_sourcetypes:
        parts.append(f"sourcetype={common_sourcetypes[0]}")

    return " ".join(parts)


def format_context_summary(context: SearchContext) -> str:
    """
    Format a human-readable summary of the search context.

    Args:
        context: SearchContext object

    Returns:
        Formatted string summary
    """
    lines = []
    lines.append(f"Index: {context.index}")
    lines.append(f"Source: {context.source}")
    lines.append(f"Time Range: {context.earliest_time} to {context.latest_time}")

    if context.discovered_at:
        lines.append(f"Discovered: {context.discovered_at}")

    if context.app:
        lines.append(f"App: {context.app}")

    # Sourcetypes
    sourcetypes = context.get_sourcetypes()
    if sourcetypes:
        lines.append(f"Sourcetypes: {', '.join(sourcetypes[:5])}")

    # Hosts
    hosts = context.get_hosts()
    if hosts:
        lines.append(f"Hosts: {', '.join(hosts[:5])}")

    # Event count
    event_count = context.get_event_count()
    if event_count:
        lines.append(f"Event Count: ~{event_count:,}")

    # Common fields
    common_fields = get_common_fields(context, limit=5)
    if common_fields:
        lines.append(f"Common Fields: {', '.join(common_fields)}")

    return "\n".join(lines)


def has_search_context(index_name: str) -> bool:
    """
    Check if search context exists without fully loading it.

    Args:
        index_name: Splunk index name

    Returns:
        True if skill directory or settings config exists
    """
    # Check skill directory
    skill_path = get_index_skill_path(index_name)
    if skill_path.exists():
        return True

    # Check settings.local.json
    settings_ctx = load_settings_context(index_name)
    return settings_ctx is not None
