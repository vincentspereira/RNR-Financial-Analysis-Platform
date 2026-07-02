"""
Tests for app.core.error_tracking (ErrorTracker, ErrorReport, ErrorContext, decorators).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.error_tracking import (
    ErrorCategory,
    ErrorContext,
    ErrorReport,
    ErrorSeverity,
    ErrorTracker,
    track_api_error,
    track_async_function_errors,
    track_database_error,
    track_errors,
    track_function_errors,
    track_security_error,
    track_validation_error,
)


@pytest.fixture
def tracker() -> ErrorTracker:
    return ErrorTracker()


@pytest.fixture
def sample_error() -> Exception:
    try:
        raise ValueError("test error")
    except ValueError as e:
        return e


# ---------------------------------------------------------------------------
# ErrorContext
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorContext:
    def test_default_context_empty(self):
        ctx = ErrorContext()
        d = ctx.to_dict()
        assert d["user_id"] is None
        assert d["additional_data"] == {}

    def test_populated_context(self):
        ctx = ErrorContext()
        ctx.user_id = "u-1"
        ctx.endpoint = "/api/v1/test"
        ctx.method = "GET"
        ctx.additional_data = {"k": "v"}
        d = ctx.to_dict()
        assert d["user_id"] == "u-1"
        assert d["endpoint"] == "/api/v1/test"
        assert d["additional_data"] == {"k": "v"}


# ---------------------------------------------------------------------------
# ErrorReport
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorReport:
    def test_report_captures_type_and_message(self, sample_error):
        report = ErrorReport(sample_error)
        assert report.error_type == "ValueError"
        assert report.error_message == "test error"
        assert report.id is not None
        assert isinstance(report.timestamp, datetime)

    def test_report_to_dict(self, sample_error):
        ctx = ErrorContext()
        ctx.endpoint = "/x"
        report = ErrorReport(
            sample_error,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            context=ctx,
            tags={"env": "test"},
        )
        d = report.to_dict()
        assert d["error_type"] == "ValueError"
        assert d["severity"] == "high"
        assert d["category"] == "validation"
        assert d["tags"] == {"env": "test"}
        assert d["context"]["endpoint"] == "/x"

    def test_report_without_traceback(self):
        # Error built without a real raise — no __traceback__
        err = RuntimeError("no traceback")
        report = ErrorReport(err)
        assert report.filename is None
        assert report.line_number is None
        assert report.function_name is None


# ---------------------------------------------------------------------------
# ErrorTracker
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorTracker:
    def test_track_error_returns_id(self, tracker, sample_error):
        error_id = tracker.track_error(sample_error)
        assert error_id
        assert isinstance(error_id, str)
        assert len(tracker.error_reports) == 1

    def test_track_error_increments_count(self, tracker, sample_error):
        tracker.track_error(sample_error)
        tracker.track_error(sample_error)
        # Same error type + category → same key
        key = f"ValueError:{ErrorCategory.SYSTEM.value}"
        assert tracker.error_counts[key] == 2

    def test_max_reports_respected(self):
        tracker = ErrorTracker()
        tracker.max_reports = 5
        for i in range(10):
            try:
                raise RuntimeError(f"err {i}")
            except RuntimeError as e:
                tracker.track_error(e)
        # Should keep only the most recent 5
        assert len(tracker.error_reports) == 5

    def test_critical_error_logs_alert(self, tracker, sample_error):
        with patch.object(tracker, "_handle_critical_error") as mock_critical:
            tracker.track_error(sample_error, severity=ErrorSeverity.CRITICAL)
            mock_critical.assert_called_once()

    def test_get_error_by_id(self, tracker, sample_error):
        error_id = tracker.track_error(sample_error)
        report = tracker.get_error_by_id(error_id)
        assert report is not None
        assert report.id == error_id

    def test_get_error_by_unknown_id(self, tracker):
        assert tracker.get_error_by_id("does-not-exist") is None

    def test_clear_old_errors(self, tracker, sample_error):
        tracker.track_error(sample_error)
        # Backdate the report
        tracker.error_reports[0].timestamp = datetime.now(timezone.utc) - timedelta(days=30)
        tracker.clear_old_errors(days=7)
        assert tracker.error_reports == []

    def test_get_statistics_empty(self, tracker):
        stats = tracker.get_error_statistics()
        assert stats["total_errors"] == 0
        assert stats["top_errors"] == []

    def test_get_statistics_with_errors(self, tracker):
        # Track errors of different types/severities
        try:
            raise ValueError("v1")
        except ValueError as e:
            tracker.track_error(e, severity=ErrorSeverity.LOW, category=ErrorCategory.VALIDATION)
        try:
            raise RuntimeError("r1")
        except RuntimeError as e:
            tracker.track_error(e, severity=ErrorSeverity.HIGH, category=ErrorCategory.SYSTEM)
        stats = tracker.get_error_statistics()
        assert stats["total_errors"] == 2
        assert stats["severity_distribution"] == {"low": 1, "high": 1}
        assert "validation" in stats["category_distribution"]
        assert "system" in stats["category_distribution"]


# ---------------------------------------------------------------------------
# Decorators / context managers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrackErrors:
    def test_context_manager_tracks_and_reraises(self):
        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            mock_tracker.track_error.return_value = "id-1"
            with pytest.raises(RuntimeError):
                with track_errors():
                    raise RuntimeError("boom")
            mock_tracker.track_error.assert_called_once()

    def test_context_manager_swallows_when_reraise_false(self):
        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            mock_tracker.track_error.return_value = "id-2"
            with track_errors(reraise=False):
                raise RuntimeError("boom")
            mock_tracker.track_error.assert_called_once()


@pytest.mark.unit
class TestFunctionDecorators:
    def test_track_function_errors_passthrough(self):
        @track_function_errors()
        def add(a, b):
            return a + b
        assert add(2, 3) == 5

    def test_track_function_errors_records_failure(self):
        @track_function_errors()
        def broken():
            raise RuntimeError("oops")

        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            mock_tracker.track_error.return_value = "id"
            with pytest.raises(RuntimeError):
                broken()
            mock_tracker.track_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_async_function_errors_passthrough(self):
        @track_async_function_errors()
        async def fn():
            return "ok"
        assert await fn() == "ok"

    @pytest.mark.asyncio
    async def test_track_async_function_errors_records_failure(self):
        @track_async_function_errors()
        async def broken():
            raise RuntimeError("oops async")
        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            mock_tracker.track_error.return_value = "id"
            with pytest.raises(RuntimeError):
                await broken()
            mock_tracker.track_error.assert_called_once()


@pytest.mark.unit
class TestConvenienceErrorTrackers:
    def test_track_database_error(self, sample_error):
        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            track_database_error(sample_error)
            mock_tracker.track_error.assert_called_once()

    def test_track_api_error(self, sample_error):
        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            track_api_error(sample_error)
            mock_tracker.track_error.assert_called_once()

    def test_track_validation_error(self, sample_error):
        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            track_validation_error(sample_error)
            mock_tracker.track_error.assert_called_once()

    def test_track_security_error(self, sample_error):
        with patch("app.core.error_tracking.error_tracker") as mock_tracker:
            track_security_error(sample_error)
            mock_tracker.track_error.assert_called_once()
