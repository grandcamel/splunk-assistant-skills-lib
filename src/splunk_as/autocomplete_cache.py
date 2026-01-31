"""
Caching layer for Splunk autocomplete data.

Provides efficient caching of index names, sourcetypes, fields, and
other metadata to improve performance of SPL building and validation.

Features:
- Automatic cache warming on first use
- Configurable TTL (default: 1 day for metadata)
- In-memory cache with SQLite persistence
- Thread-safe access
- Invalidation support
"""

from __future__ import annotations

import threading
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from assistant_skills_lib.cache import SkillCache, get_skill_cache

if TYPE_CHECKING:
    from .splunk_client import SplunkClient

# Default TTL for autocomplete suggestions
DEFAULT_SUGGESTION_TTL = timedelta(hours=24)


class AutocompleteCache:
    """
    Caches Splunk autocomplete suggestions to reduce API calls.

    Caches:
    - Index names
    - Sourcetypes
    - Fields (per sourcetype)
    - Apps
    - Saved searches
    """

    # Cache key constants
    KEY_INDEXES_LIST = "splunk:indexes:all"
    KEY_SOURCETYPES_LIST = "splunk:sourcetypes:all"
    KEY_APPS_LIST = "splunk:apps:all"
    KEY_SAVED_SEARCHES = "splunk:savedsearches:all"
    KEY_FIELDS_PREFIX = "splunk:fields:"
    KEY_SUGGESTION_PREFIX = "splunk:suggest:"

    # TTL constants
    TTL_INDEXES = timedelta(hours=24)  # 24 hours for indexes
    TTL_SOURCETYPES = timedelta(hours=12)  # 12 hours for sourcetypes
    TTL_APPS = timedelta(hours=24)  # 24 hours for apps
    TTL_FIELDS = timedelta(hours=1)  # 1 hour for field lists
    TTL_SAVED_SEARCHES = timedelta(hours=1)  # 1 hour for saved searches
    TTL_SUGGESTIONS = timedelta(hours=1)  # 1 hour for value suggestions

    def __init__(self, cache: SkillCache | None = None):
        """
        Initialize autocomplete cache.

        Args:
            cache: Optional SkillCache instance (creates one if not provided)
        """
        self._cache = cache or get_skill_cache("splunk_autocomplete")
        self._memory_cache: dict[str, Any] = {}
        self._memory_cache_time: dict[str, float] = {}

    def get_indexes(
        self, client: SplunkClient | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get cached index definitions.

        Args:
            client: Splunk client (required if cache miss)
            force_refresh: Force refresh from API

        Returns:
            List of index dicts with name, totalEventCount, etc.
        """
        if not force_refresh:
            # Check memory cache first
            if self.KEY_INDEXES_LIST in self._memory_cache:
                cache_time = self._memory_cache_time.get(self.KEY_INDEXES_LIST, 0)
                if time.time() - cache_time < 300:  # 5 min memory cache
                    return cast(
                        list[dict[str, Any]], self._memory_cache[self.KEY_INDEXES_LIST]
                    )

            # Check persistent cache
            cached = self._cache.get(self.KEY_INDEXES_LIST, category="field")
            if cached:
                self._memory_cache[self.KEY_INDEXES_LIST] = cached
                self._memory_cache_time[self.KEY_INDEXES_LIST] = time.time()
                return cast(list[dict[str, Any]], cached)

        # Fetch from API if client provided
        if client:
            try:
                response = client.get(
                    "/services/data/indexes",
                    params={"output_mode": "json", "count": 0},
                )
                indexes = []
                for entry in response.get("entry", []):
                    content = entry.get("content", {})
                    indexes.append(
                        {
                            "name": entry.get("name"),
                            "totalEventCount": content.get("totalEventCount", 0),
                            "currentDBSizeMB": content.get("currentDBSizeMB", 0),
                            "datatype": content.get("datatype", "event"),
                        }
                    )
                self.set_indexes(indexes)
                return indexes
            except Exception:
                pass

        return []

    def set_indexes(self, indexes: list[dict[str, Any]]) -> None:
        """
        Cache index definitions.

        Args:
            indexes: List of index dicts
        """
        self._cache.set(
            self.KEY_INDEXES_LIST,
            indexes,
            category="field",
            ttl=self.TTL_INDEXES,
        )
        self._memory_cache[self.KEY_INDEXES_LIST] = indexes
        self._memory_cache_time[self.KEY_INDEXES_LIST] = time.time()

    def get_sourcetypes(
        self, client: SplunkClient | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get cached sourcetype definitions.

        Args:
            client: Splunk client (required if cache miss)
            force_refresh: Force refresh from API

        Returns:
            List of sourcetype dicts
        """
        if not force_refresh:
            # Check memory cache first
            if self.KEY_SOURCETYPES_LIST in self._memory_cache:
                cache_time = self._memory_cache_time.get(self.KEY_SOURCETYPES_LIST, 0)
                if time.time() - cache_time < 300:  # 5 min memory cache
                    return cast(
                        list[dict[str, Any]],
                        self._memory_cache[self.KEY_SOURCETYPES_LIST],
                    )

            # Check persistent cache
            cached = self._cache.get(self.KEY_SOURCETYPES_LIST, category="field")
            if cached:
                self._memory_cache[self.KEY_SOURCETYPES_LIST] = cached
                self._memory_cache_time[self.KEY_SOURCETYPES_LIST] = time.time()
                return cast(list[dict[str, Any]], cached)

        # Fetch from API if client provided
        if client:
            try:
                response = client.get(
                    "/services/saved/sourcetypes",
                    params={"output_mode": "json", "count": 0},
                )
                sourcetypes = []
                for entry in response.get("entry", []):
                    sourcetypes.append(
                        {
                            "name": entry.get("name"),
                            "description": entry.get("content", {}).get(
                                "description", ""
                            ),
                        }
                    )
                self.set_sourcetypes(sourcetypes)
                return sourcetypes
            except Exception:
                pass

        return []

    def set_sourcetypes(self, sourcetypes: list[dict[str, Any]]) -> None:
        """
        Cache sourcetype definitions.

        Args:
            sourcetypes: List of sourcetype dicts
        """
        self._cache.set(
            self.KEY_SOURCETYPES_LIST,
            sourcetypes,
            category="field",
            ttl=self.TTL_SOURCETYPES,
        )
        self._memory_cache[self.KEY_SOURCETYPES_LIST] = sourcetypes
        self._memory_cache_time[self.KEY_SOURCETYPES_LIST] = time.time()

    def get_apps(
        self, client: SplunkClient | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get cached app definitions.

        Args:
            client: Splunk client (required if cache miss)
            force_refresh: Force refresh from API

        Returns:
            List of app dicts with name, label, etc.
        """
        if not force_refresh:
            cached = self._cache.get(self.KEY_APPS_LIST, category="field")
            if cached:
                return cast(list[dict[str, Any]], cached)

        # Fetch from API if client provided
        if client:
            try:
                response = client.get(
                    "/services/apps/local",
                    params={"output_mode": "json", "count": 0},
                )
                apps = []
                for entry in response.get("entry", []):
                    content = entry.get("content", {})
                    apps.append(
                        {
                            "name": entry.get("name"),
                            "label": content.get("label", ""),
                            "version": content.get("version", ""),
                            "visible": content.get("visible", True),
                        }
                    )
                self._cache.set(
                    self.KEY_APPS_LIST,
                    apps,
                    category="field",
                    ttl=self.TTL_APPS,
                )
                return apps
            except Exception:
                pass

        return []

    def get_saved_searches(
        self,
        client: SplunkClient | None = None,
        force_refresh: bool = False,
        app: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get cached saved search definitions.

        Args:
            client: Splunk client (required if cache miss)
            force_refresh: Force refresh from API
            app: Optional app to filter by

        Returns:
            List of saved search dicts
        """
        cache_key = f"{self.KEY_SAVED_SEARCHES}:{app or 'all'}"

        if not force_refresh:
            cached = self._cache.get(cache_key, category="search")
            if cached:
                return cast(list[dict[str, Any]], cached)

        # Fetch from API if client provided
        if client:
            try:
                params = {"output_mode": "json", "count": 100}
                if app:
                    params["app"] = app

                response = client.get("/services/saved/searches", params=params)
                searches = []
                for entry in response.get("entry", []):
                    content = entry.get("content", {})
                    searches.append(
                        {
                            "name": entry.get("name"),
                            "search": content.get("search", ""),
                            "description": content.get("description", ""),
                            "is_scheduled": content.get("is_scheduled", False),
                        }
                    )
                self._cache.set(
                    cache_key,
                    searches,
                    category="search",
                    ttl=self.TTL_SAVED_SEARCHES,
                )
                return searches
            except Exception:
                pass

        return []

    def get_fields_for_sourcetype(
        self,
        sourcetype: str,
        client: SplunkClient | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get cached field definitions for a sourcetype.

        Args:
            sourcetype: Sourcetype to get fields for
            client: Splunk client (required if cache miss)
            force_refresh: Force refresh from API

        Returns:
            List of field dicts with name and type
        """
        cache_key = f"{self.KEY_FIELDS_PREFIX}{sourcetype}"

        if not force_refresh:
            cached = self._cache.get(cache_key, category="field")
            if cached:
                return cast(list[dict[str, Any]], cached)

        # Field discovery requires a search, skip for now
        # Could be implemented using: | metadata type=sourcetypes sourcetype=X
        return []

    def warm_cache(self, client: SplunkClient) -> dict[str, int]:
        """
        Pre-warm the autocomplete cache.

        Args:
            client: Splunk client

        Returns:
            Dict with counts of cached items
        """
        stats = {"indexes": 0, "sourcetypes": 0, "apps": 0}

        try:
            indexes = self.get_indexes(client, force_refresh=True)
            stats["indexes"] = len(indexes)

            sourcetypes = self.get_sourcetypes(client, force_refresh=True)
            stats["sourcetypes"] = len(sourcetypes)

            apps = self.get_apps(client, force_refresh=True)
            stats["apps"] = len(apps)

        except Exception as e:
            print(f"Warning: Cache warming failed: {e}")

        return stats

    def invalidate(self, sourcetype: str | None = None) -> int:
        """
        Invalidate cached autocomplete data.

        Args:
            sourcetype: Specific sourcetype to invalidate fields for,
                       or None to invalidate all

        Returns:
            Number of entries invalidated
        """
        count = 0

        if sourcetype:
            # Invalidate specific sourcetype fields
            cache_key = f"{self.KEY_FIELDS_PREFIX}{sourcetype}"
            count += cast(int, self._cache.invalidate(key=cache_key, category="field"))
        else:
            # Invalidate all autocomplete data
            count += cast(
                int, self._cache.invalidate(key=self.KEY_INDEXES_LIST, category="field")
            )
            count += cast(
                int,
                self._cache.invalidate(key=self.KEY_SOURCETYPES_LIST, category="field"),
            )
            count += cast(
                int, self._cache.invalidate(key=self.KEY_APPS_LIST, category="field")
            )
            count += cast(
                int, self._cache.invalidate(pattern=f"{self.KEY_FIELDS_PREFIX}*")
            )
            count += cast(
                int, self._cache.invalidate(pattern=f"{self.KEY_SAVED_SEARCHES}*")
            )

            # Clear memory cache
            self._memory_cache.clear()
            self._memory_cache_time.clear()

        return count

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        cache_stats = self._cache.get_stats()

        # Check what's currently cached
        has_indexes = (
            self._cache.get(self.KEY_INDEXES_LIST, category="field") is not None
        )
        has_sourcetypes = (
            self._cache.get(self.KEY_SOURCETYPES_LIST, category="field") is not None
        )
        has_apps = self._cache.get(self.KEY_APPS_LIST, category="field") is not None

        return {
            "indexes_cached": has_indexes,
            "sourcetypes_cached": has_sourcetypes,
            "apps_cached": has_apps,
            "memory_cache_size": len(self._memory_cache),
            "total_cache_entries": cache_stats.entry_count,
            "cache_hit_rate": f"{cache_stats.hit_rate * 100:.1f}%",
        }


# Singleton instance for shared access
_autocomplete_cache: AutocompleteCache | None = None
_autocomplete_cache_lock = threading.Lock()


def get_autocomplete_cache() -> AutocompleteCache:
    """
    Get or create the singleton autocomplete cache.

    Thread-safe singleton access using double-checked locking pattern.

    Returns:
        AutocompleteCache instance
    """
    global _autocomplete_cache
    if _autocomplete_cache is None:
        with _autocomplete_cache_lock:
            if _autocomplete_cache is None:
                _autocomplete_cache = AutocompleteCache()
    return _autocomplete_cache
