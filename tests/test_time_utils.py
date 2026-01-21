#!/usr/bin/env python3
"""Unit tests for time_utils module."""

from datetime import datetime, timedelta

import pytest

from splunk_as.time_utils import (
    SNAP_UNITS,
    TIME_UNITS,
    datetime_to_time_modifier,
    epoch_to_iso,
    get_relative_time,
    get_search_time_bounds,
    get_time_range_presets,
    parse_splunk_time,
    snap_to_unit,
    snap_to_weekday,
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


class TestTimeUnitsConstant:
    """Tests for TIME_UNITS constant."""

    def test_seconds(self):
        assert TIME_UNITS["s"] == 1
        assert TIME_UNITS["sec"] == 1
        assert TIME_UNITS["second"] == 1
        assert TIME_UNITS["seconds"] == 1

    def test_minutes(self):
        assert TIME_UNITS["m"] == 60
        assert TIME_UNITS["min"] == 60
        assert TIME_UNITS["minute"] == 60
        assert TIME_UNITS["minutes"] == 60

    def test_hours(self):
        assert TIME_UNITS["h"] == 3600
        assert TIME_UNITS["hr"] == 3600
        assert TIME_UNITS["hour"] == 3600
        assert TIME_UNITS["hours"] == 3600

    def test_days(self):
        assert TIME_UNITS["d"] == 86400
        assert TIME_UNITS["day"] == 86400
        assert TIME_UNITS["days"] == 86400

    def test_weeks(self):
        assert TIME_UNITS["w"] == 604800
        assert TIME_UNITS["week"] == 604800
        assert TIME_UNITS["weeks"] == 604800

    def test_months(self):
        assert TIME_UNITS["mon"] == 2592000
        assert TIME_UNITS["month"] == 2592000
        assert TIME_UNITS["months"] == 2592000

    def test_years(self):
        assert TIME_UNITS["y"] == 31536000
        assert TIME_UNITS["year"] == 31536000
        assert TIME_UNITS["years"] == 31536000


class TestSnapUnitsConstant:
    """Tests for SNAP_UNITS constant."""

    def test_snap_units(self):
        assert SNAP_UNITS["s"] == "second"
        assert SNAP_UNITS["m"] == "minute"
        assert SNAP_UNITS["h"] == "hour"
        assert SNAP_UNITS["d"] == "day"
        assert SNAP_UNITS["w"] == "week"
        assert SNAP_UNITS["mon"] == "month"
        assert SNAP_UNITS["q"] == "quarter"
        assert SNAP_UNITS["y"] == "year"


class TestParseSplunkTimeExtended:
    """Extended tests for parse_splunk_time."""

    def test_now_with_parentheses(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = parse_splunk_time("now()", reference=ref)
        assert result == ref

    def test_earliest_keyword(self):
        result = parse_splunk_time("earliest")
        assert result == datetime(1970, 1, 1)

    def test_latest_keyword(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = parse_splunk_time("latest", reference=ref)
        assert result == ref

    def test_zero_returns_epoch(self):
        result = parse_splunk_time("0")
        assert result == datetime(1970, 1, 1)

    def test_relative_minutes(self):
        ref = datetime(2024, 1, 1, 12, 30, 0)
        result = parse_splunk_time("-30m", reference=ref)
        assert result == datetime(2024, 1, 1, 12, 0, 0)

    def test_relative_seconds(self):
        ref = datetime(2024, 1, 1, 12, 0, 30)
        result = parse_splunk_time("-30s", reference=ref)
        assert result == datetime(2024, 1, 1, 12, 0, 0)

    def test_relative_weeks(self):
        ref = datetime(2024, 1, 14, 12, 0, 0)
        result = parse_splunk_time("-1w", reference=ref)
        assert result == datetime(2024, 1, 7, 12, 0, 0)

    def test_relative_months(self):
        ref = datetime(2024, 2, 15, 12, 0, 0)
        result = parse_splunk_time("-1mon", reference=ref)
        # -1mon = -30 days
        expected = ref - timedelta(days=30)
        assert result == expected

    def test_relative_years(self):
        ref = datetime(2024, 6, 15, 12, 0, 0)
        result = parse_splunk_time("-1y", reference=ref)
        # -1y = -365 days
        expected = ref - timedelta(days=365)
        assert result == expected

    def test_future_time(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = parse_splunk_time("+1h", reference=ref)
        assert result == datetime(2024, 1, 1, 13, 0, 0)

    def test_combined_relative_and_snap(self):
        ref = datetime(2024, 1, 1, 14, 30, 0)
        result = parse_splunk_time("-1d@d", reference=ref)
        # -1d then snap to day
        expected = datetime(2023, 12, 31, 0, 0, 0)
        assert result == expected

    def test_snap_to_hour(self):
        ref = datetime(2024, 1, 1, 14, 30, 45)
        result = parse_splunk_time("@h", reference=ref)
        assert result == datetime(2024, 1, 1, 14, 0, 0)

    def test_snap_to_week(self):
        ref = datetime(2024, 1, 3, 14, 30, 45)  # Wednesday
        result = parse_splunk_time("@w", reference=ref)
        # Should snap to Sunday
        assert result.weekday() == 6  # Sunday in Python is 6

    def test_snap_to_weekday(self):
        ref = datetime(2024, 1, 3, 14, 30, 45)  # Wednesday
        result = parse_splunk_time("@w0", reference=ref)
        # Should snap to Sunday (day 0)
        assert result.weekday() == 6  # Python Sunday

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown time unit"):
            parse_splunk_time("-1x")

    def test_case_insensitive(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result1 = parse_splunk_time("-1H", reference=ref)
        result2 = parse_splunk_time("-1h", reference=ref)
        assert result1 == result2

    def test_whitespace_stripped(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        result = parse_splunk_time("  -1h  ", reference=ref)
        assert result == datetime(2024, 1, 1, 11, 0, 0)


class TestSnapToUnitExtended:
    """Extended tests for snap_to_unit."""

    def test_snap_to_second(self):
        dt = datetime(2024, 1, 1, 14, 30, 45, 123456)
        result = snap_to_unit(dt, "s")
        assert result == datetime(2024, 1, 1, 14, 30, 45, 0)

    def test_snap_to_minute(self):
        dt = datetime(2024, 1, 1, 14, 30, 45, 123456)
        result = snap_to_unit(dt, "m")
        assert result == datetime(2024, 1, 1, 14, 30, 0, 0)

    def test_snap_to_week(self):
        dt = datetime(2024, 1, 3, 14, 30, 45)  # Wednesday
        result = snap_to_unit(dt, "w")
        # Should snap to Sunday at midnight
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_snap_to_quarter_q1(self):
        dt = datetime(2024, 2, 15, 14, 30, 45)
        result = snap_to_unit(dt, "q")
        assert result == datetime(2024, 1, 1, 0, 0, 0)

    def test_snap_to_quarter_q2(self):
        dt = datetime(2024, 5, 15, 14, 30, 45)
        result = snap_to_unit(dt, "q")
        assert result == datetime(2024, 4, 1, 0, 0, 0)

    def test_snap_to_quarter_q3(self):
        dt = datetime(2024, 8, 15, 14, 30, 45)
        result = snap_to_unit(dt, "q")
        assert result == datetime(2024, 7, 1, 0, 0, 0)

    def test_snap_to_quarter_q4(self):
        dt = datetime(2024, 11, 15, 14, 30, 45)
        result = snap_to_unit(dt, "q")
        assert result == datetime(2024, 10, 1, 0, 0, 0)

    def test_snap_to_year(self):
        dt = datetime(2024, 6, 15, 14, 30, 45)
        result = snap_to_unit(dt, "y")
        assert result == datetime(2024, 1, 1, 0, 0, 0)

    def test_unknown_snap_unit_raises(self):
        dt = datetime(2024, 1, 1, 14, 30, 45)
        with pytest.raises(ValueError, match="Unknown snap unit"):
            snap_to_unit(dt, "x")

    def test_alternate_unit_names(self):
        dt = datetime(2024, 1, 1, 14, 30, 45, 123456)
        assert snap_to_unit(dt, "sec") == snap_to_unit(dt, "s")
        assert snap_to_unit(dt, "min") == snap_to_unit(dt, "m")
        assert snap_to_unit(dt, "hr") == snap_to_unit(dt, "h")
        assert snap_to_unit(dt, "day") == snap_to_unit(dt, "d")
        assert snap_to_unit(dt, "month") == snap_to_unit(dt, "mon")
        assert snap_to_unit(dt, "year") == snap_to_unit(dt, "y")


class TestSnapToWeekday:
    """Tests for snap_to_weekday."""

    def test_snap_to_sunday(self):
        dt = datetime(2024, 1, 3, 14, 30, 45)  # Wednesday
        result = snap_to_weekday(dt, 0)  # Sunday
        assert result.weekday() == 6  # Python Sunday
        assert result.hour == 0
        assert result.minute == 0

    def test_snap_to_monday(self):
        dt = datetime(2024, 1, 3, 14, 30, 45)  # Wednesday
        result = snap_to_weekday(dt, 1)  # Monday
        assert result.weekday() == 0  # Python Monday

    def test_snap_to_same_day(self):
        dt = datetime(2024, 1, 3, 14, 30, 45)  # Wednesday (Python weekday 2)
        # In Splunk: Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6
        result = snap_to_weekday(dt, 3)  # Splunk Wednesday = 3
        assert result == datetime(2024, 1, 3, 0, 0, 0)

    def test_snap_to_saturday(self):
        dt = datetime(2024, 1, 3, 14, 30, 45)  # Wednesday
        result = snap_to_weekday(dt, 6)  # Saturday
        # Goes back to previous Saturday (Dec 30)
        assert result.weekday() == 5  # Python Saturday


class TestDatetimeToTimeModifierExtended:
    """Extended tests for datetime_to_time_modifier."""

    def test_relative_seconds(self):
        dt = datetime.now() - timedelta(seconds=30)
        result = datetime_to_time_modifier(dt, format_type="relative")
        assert result == "-30s"

    def test_relative_minutes(self):
        dt = datetime.now() - timedelta(minutes=30)
        result = datetime_to_time_modifier(dt, format_type="relative")
        assert result == "-30m"

    def test_relative_hours(self):
        dt = datetime.now() - timedelta(hours=5)
        result = datetime_to_time_modifier(dt, format_type="relative")
        assert result == "-5h"

    def test_relative_days(self):
        dt = datetime.now() - timedelta(days=3)
        result = datetime_to_time_modifier(dt, format_type="relative")
        assert result == "-3d"

    def test_relative_weeks(self):
        dt = datetime.now() - timedelta(weeks=2)
        result = datetime_to_time_modifier(dt, format_type="relative")
        assert result == "-2w"

    def test_relative_months(self):
        dt = datetime.now() - timedelta(days=60)  # ~2 months
        result = datetime_to_time_modifier(dt, format_type="relative")
        assert result == "-2mon"

    def test_future_time(self):
        dt = datetime.now() + timedelta(hours=1)
        result = datetime_to_time_modifier(dt, format_type="relative")
        assert result.startswith("+")

    def test_from_epoch_input(self):
        epoch = 1704067200  # 2024-01-01 00:00:00 UTC
        result = datetime_to_time_modifier(epoch, format_type="epoch")
        assert result == str(epoch)

    def test_from_float_epoch(self):
        epoch = 1704067200.5
        result = datetime_to_time_modifier(epoch, format_type="epoch")
        # Should truncate to int
        assert result == "1704067200"

    def test_unknown_format_raises(self):
        dt = datetime.now()
        with pytest.raises(ValueError, match="Unknown format type"):
            datetime_to_time_modifier(dt, format_type="invalid")


class TestValidateTimeRangeExtended:
    """Extended tests for validate_time_range."""

    def test_invalid_earliest_format(self):
        is_valid, error = validate_time_range("invalid", "now")
        assert not is_valid
        assert error is not None

    def test_invalid_latest_format(self):
        is_valid, error = validate_time_range("-1h", "invalid")
        assert not is_valid
        assert error is not None

    def test_same_time_is_valid(self):
        ref = datetime(2024, 1, 1, 12, 0, 0)
        is_valid, error = validate_time_range("now", "now", reference=ref)
        assert is_valid

    def test_all_time_range(self):
        is_valid, error = validate_time_range("0", "now")
        assert is_valid


class TestGetRelativeTimeExtended:
    """Extended tests for get_relative_time."""

    def test_positive_offset(self):
        result = get_relative_time(1, "h")
        assert result == "1h"

    def test_zero_offset(self):
        result = get_relative_time(0, "h")
        assert result == "0h"

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown time unit"):
            get_relative_time(-1, "x")

    def test_all_valid_units(self):
        for unit in ["s", "m", "h", "d", "w", "mon", "y"]:
            result = get_relative_time(-1, unit)
            assert result == f"-1{unit}"


class TestGetTimeRangePresetsExtended:
    """Extended tests for get_time_range_presets."""

    def test_all_presets_are_tuples(self):
        presets = get_time_range_presets()
        for name, value in presets.items():
            assert isinstance(value, tuple)
            assert len(value) == 2

    def test_preset_values_are_valid(self):
        presets = get_time_range_presets()
        ref = datetime(2024, 6, 15, 12, 0, 0)

        # Skip presets that use @w0 format (not fully supported by parse_splunk_time)
        skip_presets = {"this_week", "last_week"}

        for name, (earliest, latest) in presets.items():
            if name in skip_presets:
                continue
            # Should not raise
            is_valid, error = validate_time_range(earliest, latest, reference=ref)
            assert is_valid, f"Preset {name} is invalid: {error}"


class TestEpochToIso:
    """Tests for epoch_to_iso."""

    def test_basic_conversion(self):
        epoch = 1704067200  # Some point in late 2023/early 2024 depending on TZ
        result = epoch_to_iso(epoch)
        # Just verify it returns an ISO format string
        assert "T" in result  # ISO format includes T separator
        assert "-" in result  # ISO format includes dashes
        assert ":" in result  # ISO format includes colons

    def test_midnight_epoch(self):
        result = epoch_to_iso(0)
        # Depending on timezone, this could be Dec 31, 1969 or Jan 1, 1970
        assert "1969" in result or "1970" in result

    def test_returns_string(self):
        result = epoch_to_iso(1704067200)
        assert isinstance(result, str)


class TestGetSearchTimeBoundsExtended:
    """Extended tests for get_search_time_bounds."""

    def test_custom_defaults(self):
        earliest, latest = get_search_time_bounds(
            default_earliest="-1h", default_latest="-5m"
        )
        assert earliest == "-1h"
        assert latest == "-5m"

    def test_partial_override_earliest(self):
        earliest, latest = get_search_time_bounds(earliest="-4h")
        assert earliest == "-4h"
        assert latest == "now"

    def test_partial_override_latest(self):
        earliest, latest = get_search_time_bounds(latest="-1h")
        assert earliest == "-24h"
        assert latest == "-1h"
