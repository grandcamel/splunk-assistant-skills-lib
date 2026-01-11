#!/usr/bin/env python3
"""Unit tests for time_utils module."""

from datetime import datetime

import pytest

from splunk_assistant_skills_lib.time_utils import (
    datetime_to_time_modifier,
    get_relative_time,
    get_search_time_bounds,
    get_time_range_presets,
    parse_splunk_time,
    snap_to_unit,
    time_to_epoch,
    validate_time_range,
)


class TestParseSplunkTime:
    """Tests for parse_splunk_time."""

    def test_now(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = parse_splunk_time("now", reference=ref)
        assert result == ref

    def test_relative_hours(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = parse_splunk_time("-1h", reference=ref)
        assert result == datetime(2024, 1, 1, 11, 0, 0)

    def test_relative_days(self):
        ref = datetime(2024, 1, 10, 12, 0, 0)
        result = parse_splunk_time("-7d", reference=ref)
        assert result == datetime(2024, 1, 3, 12, 0, 0)

    def test_epoch(self):
        result = parse_splunk_time("1704067200")
        assert result == datetime.fromtimestamp(1704067200)

    def test_snap_to_day(self):
        ref = datetime(2024, 1, 1, 14, 30, 45)
        result = parse_splunk_time("@d", reference=ref)
        assert result == datetime(2024, 1, 1, 0, 0, 0)

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            parse_splunk_time("invalid")


class TestSnapToUnit:
    """Tests for snap_to_unit."""

    def test_snap_to_hour(self):
        dt = datetime(2024, 1, 1, 14, 30, 45, 123456)
        result = snap_to_unit(dt, "h")
        assert result == datetime(2024, 1, 1, 14, 0, 0)

    def test_snap_to_day(self):
        dt = datetime(2024, 1, 1, 14, 30, 45)
        result = snap_to_unit(dt, "d")
        assert result == datetime(2024, 1, 1, 0, 0, 0)

    def test_snap_to_month(self):
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = snap_to_unit(dt, "mon")
        assert result == datetime(2024, 1, 1, 0, 0, 0)


class TestDatetimeToTimeModifier:
    """Tests for datetime_to_time_modifier."""

    def test_format_epoch(self):
        dt = datetime(2024, 1, 1, 0, 0, 0)
        result = datetime_to_time_modifier(dt, format_type="epoch")
        assert result == str(int(dt.timestamp()))

    def test_format_iso(self):
        dt = datetime(2024, 1, 1, 12, 30, 45)
        result = datetime_to_time_modifier(dt, format_type="iso")
        assert "2024-01-01" in result


class TestValidateTimeRange:
    """Tests for validate_time_range."""

    def test_valid_range(self):
        is_valid, error = validate_time_range("-1h", "now")
        assert is_valid
        assert error is None

    def test_invalid_range(self):
        is_valid, error = validate_time_range("now", "-1h")
        assert not is_valid
        assert error is not None


class TestGetRelativeTime:
    """Tests for get_relative_time."""

    def test_negative_hours(self):
        result = get_relative_time(-1, "h")
        assert result == "-1h"

    def test_with_snap(self):
        result = get_relative_time(-1, "d", snap_to="d")
        assert result == "-1d@d"


class TestGetSearchTimeBounds:
    """Tests for get_search_time_bounds."""

    def test_use_provided(self):
        earliest, latest = get_search_time_bounds(earliest="-1h", latest="-5m")
        assert earliest == "-1h"
        assert latest == "-5m"

    def test_use_defaults(self):
        earliest, latest = get_search_time_bounds()
        assert earliest == "-24h"
        assert latest == "now"


class TestGetTimeRangePresets:
    """Tests for get_time_range_presets."""

    def test_has_common_presets(self):
        presets = get_time_range_presets()
        assert "last_hour" in presets
        assert "last_24_hours" in presets
        assert "today" in presets


class TestTimeToEpoch:
    """Tests for time_to_epoch."""

    def test_now(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = time_to_epoch("now", reference=ref)
        assert result == int(ref.timestamp())

    def test_relative(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = time_to_epoch("-1h", reference=ref)
        expected = datetime(2024, 1, 1, 11, 0, 0)
        assert result == int(expected.timestamp())
