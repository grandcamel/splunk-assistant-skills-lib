"""Tests for job_poller module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from splunk_as.job_poller import (
    JobProgress,
    JobState,
    _encode_sid,
    cancel_job,
    delete_job,
    finalize_job,
    get_dispatch_state,
    get_job_summary,
    list_jobs,
    pause_job,
    poll_job_status,
    set_job_ttl,
    touch_job,
    unpause_job,
    wait_for_job,
)
from splunk_as.error_handler import JobFailedError


class TestEncodeSid:
    """Tests for _encode_sid function."""

    def test_encodes_simple_sid(self):
        """Test simple SID is encoded."""
        sid = "1234567890.12345"
        result = _encode_sid(sid)
        assert result == "1234567890.12345"

    def test_encodes_special_characters(self):
        """Test special characters are URL encoded."""
        sid = "search/with/slashes"
        result = _encode_sid(sid)
        assert "/" not in result
        assert "%2F" in result

    def test_encodes_spaces(self):
        """Test spaces are encoded."""
        sid = "search with spaces"
        result = _encode_sid(sid)
        assert " " not in result
        assert "%20" in result

    def test_encodes_query_params(self):
        """Test query-like characters are encoded."""
        sid = "search?param=value"
        result = _encode_sid(sid)
        assert "?" not in result
        assert "=" not in result


class TestJobStateEnum:
    """Tests for JobState enum."""

    def test_all_states_exist(self):
        """Test all expected states exist."""
        assert JobState.QUEUED.value == "QUEUED"
        assert JobState.PARSING.value == "PARSING"
        assert JobState.RUNNING.value == "RUNNING"
        assert JobState.FINALIZING.value == "FINALIZING"
        assert JobState.DONE.value == "DONE"
        assert JobState.FAILED.value == "FAILED"
        assert JobState.PAUSED.value == "PAUSED"

    def test_is_active_property(self):
        """Test is_active property for active states."""
        assert JobState.QUEUED.is_active is True
        assert JobState.PARSING.is_active is True
        assert JobState.RUNNING.is_active is True
        assert JobState.FINALIZING.is_active is True
        assert JobState.DONE.is_active is False
        assert JobState.FAILED.is_active is False
        assert JobState.PAUSED.is_active is False

    def test_is_terminal_property(self):
        """Test is_terminal property for terminal states."""
        assert JobState.QUEUED.is_terminal is False
        assert JobState.PARSING.is_terminal is False
        assert JobState.RUNNING.is_terminal is False
        assert JobState.FINALIZING.is_terminal is False
        assert JobState.DONE.is_terminal is True
        assert JobState.FAILED.is_terminal is True
        assert JobState.PAUSED.is_terminal is False

    def test_is_success_property(self):
        """Test is_success property."""
        assert JobState.DONE.is_success is True
        assert JobState.FAILED.is_success is False
        assert JobState.QUEUED.is_success is False
        assert JobState.RUNNING.is_success is False
        assert JobState.PAUSED.is_success is False


class TestJobProgress:
    """Tests for JobProgress class."""

    def test_basic_initialization(self):
        """Test basic JobProgress initialization."""
        data = {
            "sid": "1234567890.12345",
            "dispatchState": "RUNNING",
            "doneProgress": 0.5,
            "eventCount": 1000,
            "resultCount": 500,
            "scanCount": 10000,
            "runDuration": 5.25,
        }
        progress = JobProgress(data)
        assert progress.sid == "1234567890.12345"
        assert progress.state == JobState.RUNNING
        assert progress.done_progress == 0.5
        assert progress.event_count == 1000
        assert progress.result_count == 500
        assert progress.scan_count == 10000
        assert progress.run_duration == 5.25

    def test_progress_percent_property(self):
        """Test progress_percent property."""
        data = {"dispatchState": "RUNNING", "doneProgress": 0.75}
        progress = JobProgress(data)
        assert progress.progress_percent == 75.0

    def test_missing_dispatch_state_raises(self):
        """Test missing dispatchState raises ValueError."""
        with pytest.raises(ValueError, match="Missing dispatchState"):
            JobProgress({})

    def test_invalid_dispatch_state_raises(self):
        """Test invalid dispatchState raises ValueError."""
        with pytest.raises(ValueError, match="Invalid dispatchState"):
            JobProgress({"dispatchState": "INVALID_STATE"})

    def test_safe_defaults_for_missing_fields(self):
        """Test safe defaults when fields are missing."""
        data = {"dispatchState": "RUNNING"}
        progress = JobProgress(data)
        assert progress.sid == ""
        assert progress.done_progress == 0.0
        assert progress.event_count == 0
        assert progress.result_count == 0
        assert progress.scan_count == 0
        assert progress.run_duration == 0.0

    def test_safe_int_with_invalid_value(self):
        """Test _safe_int handles invalid values."""
        data = {"dispatchState": "RUNNING", "eventCount": "not_a_number"}
        progress = JobProgress(data)
        assert progress.event_count == 0

    def test_safe_float_with_invalid_value(self):
        """Test _safe_float handles invalid values."""
        data = {"dispatchState": "RUNNING", "doneProgress": "invalid"}
        progress = JobProgress(data)
        assert progress.done_progress == 0.0

    def test_boolean_fields(self):
        """Test boolean field parsing."""
        data = {
            "dispatchState": "DONE",
            "isDone": True,
            "isFailed": False,
            "isPaused": False,
        }
        progress = JobProgress(data)
        assert progress.is_done is True
        assert progress.is_failed is False
        assert progress.is_paused is False

    def test_messages_field(self):
        """Test messages field parsing."""
        data = {
            "dispatchState": "FAILED",
            "isFailed": True,
            "messages": [
                {"type": "ERROR", "text": "Search syntax error"},
                {"type": "INFO", "text": "Some info"},
            ],
        }
        progress = JobProgress(data)
        assert len(progress.messages) == 2
        assert progress.error_message == "Search syntax error"

    def test_error_message_no_error(self):
        """Test error_message returns None when not failed."""
        data = {"dispatchState": "DONE", "isDone": True}
        progress = JobProgress(data)
        assert progress.error_message is None

    def test_error_message_no_messages(self):
        """Test error_message returns None with no messages."""
        data = {"dispatchState": "FAILED", "isFailed": True, "messages": []}
        progress = JobProgress(data)
        assert progress.error_message is None

    def test_repr(self):
        """Test __repr__ method."""
        data = {
            "sid": "test_sid",
            "dispatchState": "RUNNING",
            "doneProgress": 0.5,
            "resultCount": 100,
        }
        progress = JobProgress(data)
        repr_str = repr(progress)
        assert "test_sid" in repr_str
        assert "RUNNING" in repr_str
        assert "50.0%" in repr_str
        assert "100" in repr_str


class TestGetDispatchState:
    """Tests for get_dispatch_state function."""

    def test_get_dispatch_state(self):
        """Test successful dispatch state retrieval."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "dispatchState": "RUNNING",
                        "doneProgress": 0.5,
                        "eventCount": 1000,
                    }
                }
            ]
        }

        result = get_dispatch_state(mock_client, "test_sid")

        assert isinstance(result, JobProgress)
        assert result.state == JobState.RUNNING
        assert result.sid == "test_sid"
        mock_client.get.assert_called_once()

    def test_get_dispatch_state_invalid_response(self):
        """Test invalid response raises ValueError."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"entry": []}

        with pytest.raises(ValueError, match="Invalid job status response"):
            get_dispatch_state(mock_client, "test_sid")


class TestPollJobStatus:
    """Tests for poll_job_status function."""

    def test_poll_returns_on_done(self):
        """Test polling returns when job is done."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "dispatchState": "DONE",
                        "isDone": True,
                        "doneProgress": 1.0,
                    }
                }
            ]
        }

        result = poll_job_status(mock_client, "test_sid", timeout=5)

        assert result.state == JobState.DONE
        assert result.is_done is True

    def test_poll_raises_on_failed(self):
        """Test polling raises JobFailedError on failure."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "dispatchState": "FAILED",
                        "isFailed": True,
                        "messages": [{"type": "ERROR", "text": "Search error"}],
                    }
                }
            ]
        }

        with pytest.raises(JobFailedError) as exc_info:
            poll_job_status(mock_client, "test_sid", timeout=5)

        # Check exception was raised with correct SID
        assert exc_info.value.sid == "test_sid"
        assert exc_info.value.dispatch_state == "FAILED"

    def test_poll_returns_on_paused(self):
        """Test polling returns when job is paused."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "dispatchState": "PAUSED",
                        "isPaused": True,
                        "doneProgress": 0.5,
                    }
                }
            ]
        }

        result = poll_job_status(mock_client, "test_sid", timeout=5)

        assert result.state == JobState.PAUSED
        assert result.is_paused is True

    @patch("splunk_as.job_poller.time.sleep")
    def test_poll_timeout(self, mock_sleep):
        """Test polling raises TimeoutError after timeout."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "dispatchState": "RUNNING",
                        "doneProgress": 0.5,
                    }
                }
            ]
        }

        # Simulate time passing quickly
        call_count = [0]
        original_time = time.time

        def mock_time():
            call_count[0] += 1
            if call_count[0] > 2:
                return original_time() + 1000  # Simulate timeout
            return original_time()

        with patch("splunk_as.job_poller.time.time", mock_time):
            with pytest.raises(TimeoutError, match="did not complete"):
                poll_job_status(mock_client, "test_sid", timeout=1)

    @patch("splunk_as.job_poller.time.sleep")
    def test_poll_calls_progress_callback(self, mock_sleep):
        """Test progress callback is called during polling."""
        mock_client = MagicMock()
        # First call: running, second call: done
        mock_client.get.side_effect = [
            {
                "entry": [
                    {"content": {"dispatchState": "RUNNING", "doneProgress": 0.5}}
                ]
            },
            {
                "entry": [
                    {"content": {"dispatchState": "DONE", "isDone": True, "doneProgress": 1.0}}
                ]
            },
        ]

        callback = MagicMock()
        result = poll_job_status(
            mock_client, "test_sid", timeout=10, progress_callback=callback
        )

        assert callback.call_count == 2
        assert result.state == JobState.DONE

    @patch("splunk_as.job_poller.time.sleep")
    def test_poll_callback_error_ignored(self, mock_sleep):
        """Test callback errors don't fail polling."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {"content": {"dispatchState": "DONE", "isDone": True, "doneProgress": 1.0}}
            ]
        }

        def bad_callback(progress):
            raise RuntimeError("Callback error")

        # Should not raise despite callback error
        result = poll_job_status(
            mock_client, "test_sid", timeout=5, progress_callback=bad_callback
        )
        assert result.state == JobState.DONE


class TestWaitForJob:
    """Tests for wait_for_job function."""

    def test_wait_returns_on_done(self):
        """Test wait returns when job is done."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {"content": {"dispatchState": "DONE", "isDone": True, "doneProgress": 1.0}}
            ]
        }

        result = wait_for_job(mock_client, "test_sid", timeout=5)

        assert result.state == JobState.DONE

    @patch("builtins.print")
    def test_wait_shows_progress(self, mock_print):
        """Test wait shows progress when enabled."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "dispatchState": "DONE",
                        "isDone": True,
                        "doneProgress": 1.0,
                        "resultCount": 100,
                    }
                }
            ]
        }

        wait_for_job(mock_client, "test_sid", timeout=5, show_progress=True)

        # Should have printed progress at least once
        assert mock_print.called

    @patch("builtins.print")
    def test_wait_prints_newline_on_error(self, mock_print):
        """Test wait prints newline on error when showing progress."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "dispatchState": "FAILED",
                        "isFailed": True,
                    }
                }
            ]
        }

        with pytest.raises(JobFailedError):
            wait_for_job(mock_client, "test_sid", timeout=5, show_progress=True)


class TestJobControlFunctions:
    """Tests for job control functions."""

    def test_cancel_job(self):
        """Test cancel_job posts cancel action."""
        mock_client = MagicMock()
        mock_client.post.return_value = {}

        result = cancel_job(mock_client, "test_sid")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "cancel" in str(call_args)

    def test_pause_job(self):
        """Test pause_job posts pause action."""
        mock_client = MagicMock()
        mock_client.post.return_value = {}

        result = pause_job(mock_client, "test_sid")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "pause" in str(call_args)

    def test_unpause_job(self):
        """Test unpause_job posts unpause action."""
        mock_client = MagicMock()
        mock_client.post.return_value = {}

        result = unpause_job(mock_client, "test_sid")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "unpause" in str(call_args)

    def test_finalize_job(self):
        """Test finalize_job posts finalize action."""
        mock_client = MagicMock()
        mock_client.post.return_value = {}

        result = finalize_job(mock_client, "test_sid")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "finalize" in str(call_args)

    def test_set_job_ttl(self):
        """Test set_job_ttl posts setttl action."""
        mock_client = MagicMock()
        mock_client.post.return_value = {}

        result = set_job_ttl(mock_client, "test_sid", 3600)

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "setttl" in str(call_args)

    def test_touch_job(self):
        """Test touch_job posts touch action."""
        mock_client = MagicMock()
        mock_client.post.return_value = {}

        result = touch_job(mock_client, "test_sid")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "touch" in str(call_args)


class TestGetJobSummary:
    """Tests for get_job_summary function."""

    def test_get_job_summary(self):
        """Test get_job_summary retrieves summary."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "fields": {
                "host": {"count": 10, "distinctCount": 3},
                "source": {"count": 10, "distinctCount": 5},
            }
        }

        result = get_job_summary(mock_client, "test_sid")

        assert "fields" in result
        mock_client.get.assert_called_once()


class TestListJobs:
    """Tests for list_jobs function."""

    def test_list_jobs_returns_jobs(self):
        """Test list_jobs returns list of job dicts."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "entry": [
                {"name": "sid1", "content": {"dispatchState": "DONE"}},
                {"name": "sid2", "content": {"dispatchState": "RUNNING"}},
            ]
        }

        result = list_jobs(mock_client)

        assert len(result) == 2
        assert result[0]["sid"] == "sid1"
        assert result[0]["dispatchState"] == "DONE"
        assert result[1]["sid"] == "sid2"
        assert result[1]["dispatchState"] == "RUNNING"

    def test_list_jobs_empty(self):
        """Test list_jobs with no jobs."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"entry": []}

        result = list_jobs(mock_client)

        assert result == []

    def test_list_jobs_with_pagination(self):
        """Test list_jobs with count and offset."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"entry": []}

        list_jobs(mock_client, count=10, offset=20)

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["count"] == 10
        assert call_args[1]["params"]["offset"] == 20


class TestDeleteJob:
    """Tests for delete_job function."""

    def test_delete_job(self):
        """Test delete_job calls delete endpoint."""
        mock_client = MagicMock()
        mock_client.delete.return_value = {}

        result = delete_job(mock_client, "test_sid")

        assert result is True
        mock_client.delete.assert_called_once()
        call_args = mock_client.delete.call_args
        assert "test_sid" in str(call_args)


class TestSafeIntFloat:
    """Tests for _safe_int and _safe_float methods."""

    def test_safe_int_none(self):
        """Test _safe_int with None value."""
        assert JobProgress._safe_int(None, 42) == 42

    def test_safe_int_valid(self):
        """Test _safe_int with valid int."""
        assert JobProgress._safe_int(100, 0) == 100

    def test_safe_int_string_number(self):
        """Test _safe_int with string number."""
        assert JobProgress._safe_int("100", 0) == 100

    def test_safe_int_invalid_string(self):
        """Test _safe_int with invalid string."""
        assert JobProgress._safe_int("abc", 42) == 42

    def test_safe_int_float_value(self):
        """Test _safe_int with float value."""
        assert JobProgress._safe_int(10.5, 0) == 10

    def test_safe_float_none(self):
        """Test _safe_float with None value."""
        assert JobProgress._safe_float(None, 3.14) == 3.14

    def test_safe_float_valid(self):
        """Test _safe_float with valid float."""
        assert JobProgress._safe_float(0.75, 0.0) == 0.75

    def test_safe_float_string_number(self):
        """Test _safe_float with string number."""
        assert JobProgress._safe_float("0.5", 0.0) == 0.5

    def test_safe_float_invalid_string(self):
        """Test _safe_float with invalid string."""
        assert JobProgress._safe_float("not_a_number", 1.0) == 1.0

    def test_safe_float_int_value(self):
        """Test _safe_float with int value."""
        assert JobProgress._safe_float(5, 0.0) == 5.0
