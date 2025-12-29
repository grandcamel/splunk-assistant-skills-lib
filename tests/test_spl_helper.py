#!/usr/bin/env python3
"""Unit tests for spl_helper module."""

import pytest

from splunk_assistant_skills_lib.spl_helper import (
    add_field_extraction,
    add_head_limit,
    add_time_bounds,
    build_filter_clause,
    build_search,
    estimate_search_complexity,
    extract_fields_from_spl,
    parse_spl_commands,
    quote_field_value,
    validate_spl_syntax,
)


class TestBuildSearch:
    """Tests for build_search."""

    def test_basic_query(self):
        result = build_search("index=main | head 10")
        assert result == "index=main | head 10"

    def test_add_index(self):
        result = build_search("error", index="main")
        assert result == "index=main error"

    def test_add_time_bounds(self):
        result = build_search("index=main", earliest_time="-1h", latest_time="now")
        assert "earliest=-1h" in result
        assert "latest=now" in result

    def test_add_fields(self):
        result = build_search("index=main", fields=["host", "status"])
        assert "| fields host, status" in result

    def test_add_head(self):
        result = build_search("index=main", head=100)
        assert "| head 100" in result


class TestAddTimeBounds:
    """Tests for add_time_bounds."""

    def test_add_earliest(self):
        result = add_time_bounds("index=main", earliest="-1h")
        assert "earliest=-1h" in result

    def test_add_latest(self):
        result = add_time_bounds("index=main", latest="now")
        assert "latest=now" in result

    def test_skip_existing_time_bounds(self):
        spl = "index=main earliest=-1d latest=now"
        result = add_time_bounds(spl, earliest="-1h", latest="-5m")
        assert result == spl


class TestAddFieldExtraction:
    """Tests for add_field_extraction."""

    def test_add_fields(self):
        result = add_field_extraction("index=main", ["host", "status"])
        assert result == "index=main | fields host, status"

    def test_skip_existing_fields(self):
        spl = "index=main | fields host"
        result = add_field_extraction(spl, ["status"])
        assert result == spl


class TestAddHeadLimit:
    """Tests for add_head_limit."""

    def test_add_head(self):
        result = add_head_limit("index=main", 100)
        assert result == "index=main | head 100"

    def test_skip_existing_head(self):
        spl = "index=main | head 50"
        result = add_head_limit(spl, 100)
        assert result == spl


class TestValidateSplSyntax:
    """Tests for validate_spl_syntax."""

    def test_valid_query(self):
        is_valid, issues = validate_spl_syntax("index=main | head 10")
        assert is_valid
        assert len(issues) == 0

    def test_unbalanced_parens(self):
        is_valid, issues = validate_spl_syntax("index=main | eval x=(1+2")
        assert not is_valid
        assert "Unbalanced parentheses" in issues

    def test_empty_pipe(self):
        is_valid, issues = validate_spl_syntax("index=main | | head")
        assert not is_valid
        assert "Empty pipe segment" in issues


class TestParseSplCommands:
    """Tests for parse_spl_commands."""

    def test_simple_search(self):
        commands = parse_spl_commands("index=main | head 10")
        assert len(commands) == 2
        assert commands[0][0] == "search"
        assert commands[1][0] == "head"

    def test_generating_command(self):
        commands = parse_spl_commands("| tstats count by host")
        assert commands[0][0] == "tstats"


class TestEstimateSearchComplexity:
    """Tests for estimate_search_complexity."""

    def test_simple_search(self):
        assert estimate_search_complexity("index=main | head 10") == "simple"

    def test_medium_search(self):
        assert estimate_search_complexity("index=main | stats count | sort -count") == "medium"

    def test_complex_search(self):
        assert estimate_search_complexity("index=main | transaction host") == "complex"


class TestExtractFieldsFromSpl:
    """Tests for extract_fields_from_spl."""

    def test_extract_by_clause(self):
        fields = extract_fields_from_spl("index=main | stats count by host, status")
        assert "host" in fields
        assert "status" in fields

    def test_extract_fields_command(self):
        fields = extract_fields_from_spl("index=main | fields host, status")
        assert "host" in fields
        assert "status" in fields


class TestQuoteFieldValue:
    """Tests for quote_field_value."""

    def test_simple_value(self):
        assert quote_field_value("server1") == "server1"

    def test_value_with_spaces(self):
        assert quote_field_value("my server") == '"my server"'

    def test_value_with_quotes(self):
        assert quote_field_value('test"value') == '"test\\"value"'


class TestBuildFilterClause:
    """Tests for build_filter_clause."""

    def test_simple_filter(self):
        result = build_filter_clause({"host": "server1"})
        assert result == "host=server1"

    def test_list_filter(self):
        result = build_filter_clause({"host": ["server1", "server2"]})
        assert "host=server1" in result
        assert "host=server2" in result
        assert "OR" in result

    def test_null_filter(self):
        result = build_filter_clause({"host": None})
        assert result == "NOT host=*"
