"""Tests for search_context module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from splunk_as.search_context import (
    SearchContext,
    _context_cache,
    _deep_merge,
    clear_context_cache,
    format_context_summary,
    get_common_fields,
    get_common_sourcetypes,
    get_index_skill_path,
    get_search_context,
    get_search_defaults,
    get_skills_root,
    has_search_context,
    load_json_file,
    load_settings_context,
    load_skill_context,
    merge_contexts,
    suggest_spl_prefix,
)


class TestSearchContext:
    """Tests for SearchContext dataclass."""

    def test_basic_initialization(self):
        """Test basic SearchContext initialization."""
        ctx = SearchContext(index="main")
        assert ctx.index == "main"
        assert ctx.earliest_time == "-24h"
        assert ctx.latest_time == "now"
        assert ctx.app is None
        assert ctx.owner is None
        assert ctx.metadata == {}
        assert ctx.patterns == {}
        assert ctx.defaults == {}
        assert ctx.source == "none"
        assert ctx.discovered_at is None

    def test_custom_initialization(self):
        """Test SearchContext with custom values."""
        ctx = SearchContext(
            index="security",
            earliest_time="-1h",
            latest_time="now",
            app="search",
            owner="admin",
            metadata={"sourcetypes": ["syslog"]},
            patterns={"fields": {"host": 100}},
            defaults={"max_count": 1000},
            source="skill",
            discovered_at="2024-01-15T10:00:00",
        )
        assert ctx.index == "security"
        assert ctx.earliest_time == "-1h"
        assert ctx.app == "search"
        assert ctx.owner == "admin"
        assert ctx.metadata == {"sourcetypes": ["syslog"]}
        assert ctx.source == "skill"

    def test_has_context_true(self):
        """Test has_context returns True with metadata."""
        ctx = SearchContext(index="main", metadata={"sourcetypes": ["syslog"]})
        assert ctx.has_context() is True

    def test_has_context_with_patterns(self):
        """Test has_context returns True with patterns."""
        ctx = SearchContext(index="main", patterns={"fields": {"host": 10}})
        assert ctx.has_context() is True

    def test_has_context_with_defaults(self):
        """Test has_context returns True with defaults."""
        ctx = SearchContext(index="main", defaults={"max_count": 1000})
        assert ctx.has_context() is True

    def test_has_context_false(self):
        """Test has_context returns False without data."""
        ctx = SearchContext(index="main")
        assert ctx.has_context() is False

    def test_get_sourcetypes(self):
        """Test get_sourcetypes method."""
        ctx = SearchContext(
            index="main", metadata={"sourcetypes": ["syslog", "access_combined"]}
        )
        assert ctx.get_sourcetypes() == ["syslog", "access_combined"]

    def test_get_sourcetypes_empty(self):
        """Test get_sourcetypes with no sourcetypes."""
        ctx = SearchContext(index="main")
        assert ctx.get_sourcetypes() == []

    def test_get_hosts(self):
        """Test get_hosts method."""
        ctx = SearchContext(index="main", metadata={"hosts": ["server1", "server2"]})
        assert ctx.get_hosts() == ["server1", "server2"]

    def test_get_hosts_empty(self):
        """Test get_hosts with no hosts."""
        ctx = SearchContext(index="main")
        assert ctx.get_hosts() == []

    def test_get_sources(self):
        """Test get_sources method."""
        ctx = SearchContext(index="main", metadata={"sources": ["/var/log/syslog"]})
        assert ctx.get_sources() == ["/var/log/syslog"]

    def test_get_fields(self):
        """Test get_fields method."""
        fields = [{"name": "host", "type": "string"}]
        ctx = SearchContext(index="main", metadata={"fields": fields})
        assert ctx.get_fields() == fields

    def test_get_event_count(self):
        """Test get_event_count method."""
        ctx = SearchContext(index="main", metadata={"event_count": 1000000})
        assert ctx.get_event_count() == 1000000

    def test_get_event_count_none(self):
        """Test get_event_count with no count."""
        ctx = SearchContext(index="main")
        assert ctx.get_event_count() is None


class TestGetSkillsRoot:
    """Tests for get_skills_root function."""

    @patch("splunk_as.search_context.Path.cwd")
    def test_finds_claude_dir_in_current(self, mock_cwd):
        """Test finding .claude in current directory."""
        mock_path = MagicMock(spec=Path)
        mock_claude = MagicMock(spec=Path)
        mock_claude.exists.return_value = True
        mock_path.__truediv__ = MagicMock(return_value=mock_claude)
        mock_path.parents = []
        mock_cwd.return_value = mock_path

        result = get_skills_root()
        assert result == mock_claude

    @patch("splunk_as.search_context.Path.cwd")
    def test_fallback_to_cwd_claude(self, mock_cwd):
        """Test fallback when no .claude exists."""
        mock_path = MagicMock(spec=Path)
        mock_claude = MagicMock(spec=Path)
        mock_claude.exists.return_value = False
        mock_path.__truediv__ = MagicMock(return_value=mock_claude)
        mock_path.parents = []
        mock_cwd.return_value = mock_path

        result = get_skills_root()
        assert result == mock_claude


class TestGetIndexSkillPath:
    """Tests for get_index_skill_path function."""

    @patch("splunk_as.search_context.get_skills_root")
    def test_returns_correct_path(self, mock_root):
        """Test correct path is returned."""
        mock_root.return_value = Path("/project/.claude")
        result = get_index_skill_path("main")
        assert result == Path("/project/.claude/skills/splunk-index-main")

    @patch("splunk_as.search_context.get_skills_root")
    def test_handles_special_characters(self, mock_root):
        """Test index names with special characters."""
        mock_root.return_value = Path("/project/.claude")
        result = get_index_skill_path("my_index")
        assert result == Path("/project/.claude/skills/splunk-index-my_index")


class TestLoadJsonFile:
    """Tests for load_json_file function."""

    def test_load_existing_file(self, tmp_path):
        """Test loading existing JSON file."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        result = load_json_file(json_file)
        assert result == {"key": "value"}

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading non-existent file returns None."""
        result = load_json_file(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns None."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")

        result = load_json_file(json_file)
        assert result is None


class TestLoadSkillContext:
    """Tests for load_skill_context function."""

    @patch("splunk_as.search_context.get_index_skill_path")
    def test_skill_not_exists(self, mock_path):
        """Test returns None when skill directory doesn't exist."""
        mock_path.return_value = Path("/nonexistent")
        result = load_skill_context("main")
        assert result is None

    def test_load_skill_with_context(self, tmp_path):
        """Test loading skill with context files."""
        skill_path = tmp_path / "skills" / "splunk-index-main"
        context_dir = skill_path / "context"
        context_dir.mkdir(parents=True)

        # Create metadata.json
        metadata = {"sourcetypes": ["syslog"]}
        (context_dir / "metadata.json").write_text(json.dumps(metadata))

        # Create patterns.json
        patterns = {"fields": {"host": 100}}
        (context_dir / "patterns.json").write_text(json.dumps(patterns))

        # Create defaults.json at skill root
        defaults = {"earliest_time": "-1h"}
        (skill_path / "defaults.json").write_text(json.dumps(defaults))

        with patch(
            "splunk_as.search_context.get_index_skill_path"
        ) as mock:
            mock.return_value = skill_path
            result = load_skill_context("main")

        assert result is not None
        assert result["metadata"] == metadata
        assert result["patterns"] == patterns
        assert result["defaults"] == defaults


class TestLoadSettingsContext:
    """Tests for load_settings_context function."""

    def test_no_settings_file(self, tmp_path):
        """Test returns None when no settings file."""
        with patch(
            "splunk_as.search_context.get_skills_root"
        ) as mock:
            mock.return_value = tmp_path / ".claude"
            result = load_settings_context("main")
        assert result is None

    def test_load_settings_with_index(self, tmp_path):
        """Test loading settings with index config."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        settings = {
            "splunk": {
                "indexes": {
                    "main": {"defaults": {"earliest_time": "-4h"}, "metadata": {"note": "test"}}
                }
            }
        }
        (tmp_path / "settings.local.json").write_text(json.dumps(settings))

        with patch(
            "splunk_as.search_context.get_skills_root"
        ) as mock:
            mock.return_value = claude_dir
            result = load_settings_context("main")

        assert result is not None
        assert result["defaults"]["earliest_time"] == "-4h"
        assert result["metadata"]["note"] == "test"

    def test_load_settings_no_index_config(self, tmp_path):
        """Test returns None when index not configured."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        settings = {"splunk": {"indexes": {}}}
        (tmp_path / "settings.local.json").write_text(json.dumps(settings))

        with patch(
            "splunk_as.search_context.get_skills_root"
        ) as mock:
            mock.return_value = claude_dir
            result = load_settings_context("main")

        assert result is None


class TestMergeContexts:
    """Tests for merge_contexts function."""

    def test_both_none(self):
        """Test both contexts None."""
        merged, source = merge_contexts(None, None)
        assert merged == {}
        assert source == "none"

    def test_skill_only(self):
        """Test only skill context."""
        skill_ctx = {"metadata": {"sourcetypes": ["syslog"]}}
        merged, source = merge_contexts(skill_ctx, None)
        assert merged == skill_ctx
        assert source == "skill"

    def test_settings_only(self):
        """Test only settings context."""
        settings_ctx = {"defaults": {"earliest_time": "-1h"}}
        merged, source = merge_contexts(None, settings_ctx)
        assert merged == settings_ctx
        assert source == "settings"

    def test_merged_contexts(self):
        """Test merged skill and settings contexts."""
        skill_ctx = {
            "metadata": {"sourcetypes": ["syslog"]},
            "defaults": {"earliest_time": "-24h"},
        }
        settings_ctx = {"defaults": {"earliest_time": "-1h", "max_count": 1000}}

        merged, source = merge_contexts(skill_ctx, settings_ctx)

        assert source == "merged"
        assert merged["metadata"]["sourcetypes"] == ["syslog"]
        assert merged["defaults"]["earliest_time"] == "-1h"  # Settings override
        assert merged["defaults"]["max_count"] == 1000


class TestDeepMerge:
    """Tests for _deep_merge function."""

    def test_simple_merge(self):
        """Test simple dict merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test nested dict merge."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}
        result = _deep_merge(base, override)
        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_override_replaces_non_dict(self):
        """Test override replaces non-dict values."""
        base = {"key": "string_value"}
        override = {"key": {"nested": "dict"}}
        result = _deep_merge(base, override)
        assert result == {"key": {"nested": "dict"}}


class TestGetSearchContext:
    """Tests for get_search_context function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_context_cache()

    def test_caches_context(self):
        """Test context is cached."""
        with patch(
            "splunk_as.search_context.load_skill_context"
        ) as mock_skill:
            with patch(
                "splunk_as.search_context.load_settings_context"
            ) as mock_settings:
                mock_skill.return_value = None
                mock_settings.return_value = None

                ctx1 = get_search_context("main")
                ctx2 = get_search_context("main")

                # Should only load once
                assert mock_skill.call_count == 1
                assert ctx1 is ctx2

    def test_force_refresh_bypasses_cache(self):
        """Test force_refresh bypasses cache."""
        with patch(
            "splunk_as.search_context.load_skill_context"
        ) as mock_skill:
            with patch(
                "splunk_as.search_context.load_settings_context"
            ) as mock_settings:
                mock_skill.return_value = None
                mock_settings.return_value = None

                get_search_context("main")
                get_search_context("main", force_refresh=True)

                assert mock_skill.call_count == 2

    def test_loads_from_skill_and_settings(self):
        """Test loads and merges from both sources."""
        skill_ctx = {"metadata": {"sourcetypes": ["syslog"]}}
        settings_ctx = {"defaults": {"earliest_time": "-1h"}}

        with patch(
            "splunk_as.search_context.load_skill_context"
        ) as mock_skill:
            with patch(
                "splunk_as.search_context.load_settings_context"
            ) as mock_settings:
                mock_skill.return_value = skill_ctx
                mock_settings.return_value = settings_ctx

                ctx = get_search_context("main")

                assert ctx.index == "main"
                assert ctx.metadata == {"sourcetypes": ["syslog"]}
                assert ctx.earliest_time == "-1h"
                assert ctx.source == "merged"


class TestClearContextCache:
    """Tests for clear_context_cache function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_context_cache()

    def test_clear_all(self):
        """Test clearing all cache."""
        _context_cache["main"] = SearchContext(index="main")
        _context_cache["security"] = SearchContext(index="security")

        clear_context_cache()

        assert len(_context_cache) == 0

    def test_clear_specific_index(self):
        """Test clearing specific index cache."""
        _context_cache["main"] = SearchContext(index="main")
        _context_cache["security"] = SearchContext(index="security")

        clear_context_cache("main")

        assert "main" not in _context_cache
        assert "security" in _context_cache

    def test_clear_nonexistent_index(self):
        """Test clearing non-existent index doesn't error."""
        clear_context_cache("nonexistent")  # Should not raise


class TestGetSearchDefaults:
    """Tests for get_search_defaults function."""

    def test_returns_defaults_dict(self):
        """Test returns defaults dictionary."""
        ctx = SearchContext(
            index="main",
            earliest_time="-1h",
            latest_time="now",
            app="search",
            owner="admin",
            defaults={"max_count": 1000},
        )

        result = get_search_defaults(ctx)

        assert result["earliest_time"] == "-1h"
        assert result["latest_time"] == "now"
        assert result["app"] == "search"
        assert result["owner"] == "admin"
        assert result["max_count"] == 1000


class TestGetCommonSourcetypes:
    """Tests for get_common_sourcetypes function."""

    def test_returns_sorted_by_frequency(self):
        """Test returns sourcetypes sorted by frequency."""
        ctx = SearchContext(
            index="main",
            patterns={"sourcetypes": {"syslog": 100, "access_combined": 500, "audit": 50}},
        )

        result = get_common_sourcetypes(ctx)

        assert result == ["access_combined", "syslog", "audit"]

    def test_respects_limit(self):
        """Test respects limit parameter."""
        ctx = SearchContext(
            index="main",
            patterns={"sourcetypes": {"a": 100, "b": 90, "c": 80, "d": 70}},
        )

        result = get_common_sourcetypes(ctx, limit=2)

        assert len(result) == 2
        assert result == ["a", "b"]

    def test_empty_patterns(self):
        """Test returns empty list with no patterns."""
        ctx = SearchContext(index="main")
        result = get_common_sourcetypes(ctx)
        assert result == []


class TestGetCommonFields:
    """Tests for get_common_fields function."""

    def test_returns_sorted_by_frequency(self):
        """Test returns fields sorted by frequency."""
        ctx = SearchContext(
            index="main",
            patterns={"fields": {"host": 100, "source": 500, "sourcetype": 50}},
        )

        result = get_common_fields(ctx)

        assert result == ["source", "host", "sourcetype"]

    def test_respects_limit(self):
        """Test respects limit parameter."""
        ctx = SearchContext(
            index="main", patterns={"fields": {"a": 100, "b": 90, "c": 80, "d": 70}}
        )

        result = get_common_fields(ctx, limit=2)

        assert len(result) == 2


class TestSuggestSplPrefix:
    """Tests for suggest_spl_prefix function."""

    def test_basic_prefix(self):
        """Test basic SPL prefix."""
        ctx = SearchContext(index="main")
        result = suggest_spl_prefix(ctx)
        assert result == "index=main"

    def test_with_sourcetype(self):
        """Test prefix with common sourcetype."""
        ctx = SearchContext(
            index="main", patterns={"sourcetypes": {"syslog": 100, "audit": 50}}
        )
        result = suggest_spl_prefix(ctx)
        assert result == "index=main sourcetype=syslog"


class TestFormatContextSummary:
    """Tests for format_context_summary function."""

    def test_basic_summary(self):
        """Test basic context summary."""
        ctx = SearchContext(index="main", earliest_time="-1h", source="skill")

        result = format_context_summary(ctx)

        assert "Index: main" in result
        assert "Source: skill" in result
        assert "-1h to now" in result

    def test_summary_with_all_fields(self):
        """Test summary with all fields populated."""
        ctx = SearchContext(
            index="main",
            earliest_time="-24h",
            latest_time="now",
            app="search",
            source="merged",
            discovered_at="2024-01-15",
            metadata={
                "sourcetypes": ["syslog", "audit"],
                "hosts": ["server1", "server2"],
                "event_count": 1000000,
            },
            patterns={"fields": {"host": 100, "source": 50}},
        )

        result = format_context_summary(ctx)

        assert "Index: main" in result
        assert "App: search" in result
        assert "Discovered: 2024-01-15" in result
        assert "Sourcetypes:" in result
        assert "syslog" in result
        assert "Hosts:" in result
        assert "server1" in result
        assert "Event Count:" in result
        assert "Common Fields:" in result


class TestHasSearchContext:
    """Tests for has_search_context function."""

    @patch("splunk_as.search_context.get_index_skill_path")
    @patch("splunk_as.search_context.load_settings_context")
    def test_has_skill_directory(self, mock_settings, mock_path):
        """Test returns True when skill directory exists."""
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path.return_value = mock_path_obj

        result = has_search_context("main")

        assert result is True
        mock_settings.assert_not_called()

    @patch("splunk_as.search_context.get_index_skill_path")
    @patch("splunk_as.search_context.load_settings_context")
    def test_has_settings_config(self, mock_settings, mock_path):
        """Test returns True when settings config exists."""
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = False
        mock_path.return_value = mock_path_obj
        mock_settings.return_value = {"defaults": {"earliest_time": "-1h"}}

        result = has_search_context("main")

        assert result is True

    @patch("splunk_as.search_context.get_index_skill_path")
    @patch("splunk_as.search_context.load_settings_context")
    def test_no_context(self, mock_settings, mock_path):
        """Test returns False when no context exists."""
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = False
        mock_path.return_value = mock_path_obj
        mock_settings.return_value = None

        result = has_search_context("main")

        assert result is False
