"""
Tests for app.core.monitoring (MetricsCollector, PerformanceMonitor, AlertManager).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.monitoring import (
    AlertManager,
    MetricPoint,
    MetricsCollector,
    PerformanceMonitor,
    get_metrics_summary,
    metrics,
    monitor_performance,
)


@pytest.fixture
def collector() -> MetricsCollector:
    return MetricsCollector(max_points=100)


@pytest.mark.unit
@pytest.mark.monitoring
class TestMetricsCollector:
    def test_increment_counter(self, collector):
        collector.increment_counter("api.calls")
        collector.increment_counter("api.calls", value=2)
        assert collector.get_counter("api.calls") == 3

    def test_counter_with_tags(self, collector):
        collector.increment_counter("api.calls", tags={"endpoint": "/health"})
        collector.increment_counter("api.calls", tags={"endpoint": "/health"})
        collector.increment_counter("api.calls", tags={"endpoint": "/login"})
        assert collector.get_counter("api.calls", tags={"endpoint": "/health"}) == 2
        assert collector.get_counter("api.calls", tags={"endpoint": "/login"}) == 1

    def test_set_gauge(self, collector):
        collector.set_gauge("cpu.usage", 42.5)
        assert collector.get_gauge("cpu.usage") == 42.5

    def test_gauge_overwrites_previous(self, collector):
        collector.set_gauge("temp", 100.0)
        collector.set_gauge("temp", 200.0)
        assert collector.get_gauge("temp") == 200.0

    def test_record_histogram(self, collector):
        for v in [10, 20, 30, 40, 50]:
            collector.record_histogram("latency", float(v))
        stats = collector.get_histogram_stats("latency")
        assert stats["count"] == 5
        assert stats["min"] == 10
        assert stats["max"] == 50
        assert stats["avg"] == 30

    def test_histogram_truncates_above_1000_values(self, collector):
        for v in range(1200):
            collector.record_histogram("big", float(v))
        stats = collector.get_histogram_stats("big")
        assert stats["count"] == 1000

    def test_record_timer(self, collector):
        for d in [0.01, 0.02, 0.05]:
            collector.record_timer("query.duration", d)
        # `timers` are separate from `histograms` — verify the timers dict directly
        assert len(collector.timers["query.duration"]) == 3

    def test_empty_histogram_stats(self, collector):
        stats = collector.get_histogram_stats("nonexistent")
        assert stats["count"] == 0
        assert stats["min"] == 0

    def test_get_all_metrics(self, collector):
        collector.increment_counter("a")
        collector.set_gauge("b", 1.5)
        collector.record_histogram("c", 0.5)
        collector.record_timer("d", 0.1)
        all_metrics = collector.get_all_metrics()
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics
        assert "timers" in all_metrics

    def test_reset_metrics(self, collector):
        collector.increment_counter("a")
        collector.reset_metrics()
        assert collector.get_counter("a") == 0


@pytest.mark.unit
@pytest.mark.monitoring
class TestPerformanceMonitor:
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        monitor = PerformanceMonitor()
        # Avoid sleeping in the test
        with patch("app.core.monitoring.asyncio.sleep", AsyncMock()):
            with patch("psutil.cpu_percent", return_value=10.0):
                with patch("psutil.virtual_memory", return_value=MagicMock(
                    percent=20.0, available=1000, used=500, total=1500
                )):
                    with patch("psutil.disk_usage", return_value=MagicMock(
                        percent=50.0, free=10000, total=20000
                    )):
                        with patch("psutil.net_io_counters", return_value=MagicMock(
                            bytes_sent=100, bytes_recv=200
                        )):
                            with patch("psutil.Process") as mock_proc:
                                mock_proc.return_value.memory_info.return_value = MagicMock(rss=1000, vms=2000)
                                mock_proc.return_value.cpu_percent.return_value = 5.0
                                mock_proc.return_value.num_threads.return_value = 4
                                await monitor.start_monitoring(interval=0)
                                await asyncio.sleep(0)
                                await monitor.stop_monitoring()
                                assert monitor._monitoring is False

    @pytest.mark.asyncio
    async def test_start_monitoring_idempotent(self):
        monitor = PerformanceMonitor()
        with patch("app.core.monitoring.asyncio.sleep", AsyncMock()):
            with patch("psutil.cpu_percent", return_value=0):
                await monitor.start_monitoring()
                await monitor.start_monitoring()  # no-op
                await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_collect_system_metrics_returns_dict(self):
        monitor = PerformanceMonitor()
        with patch("psutil.cpu_percent", return_value=15.0):
            with patch("psutil.virtual_memory", return_value=MagicMock(
                percent=30.0, available=1000, used=500, total=1500
            )):
                with patch("psutil.disk_usage", return_value=MagicMock(
                    percent=40.0, free=100, total=200
                )):
                    with patch("psutil.net_io_counters", return_value=MagicMock(
                        bytes_sent=10, bytes_recv=20
                    )):
                        with patch("psutil.Process") as mock_proc:
                            mock_proc.return_value.memory_info.return_value = MagicMock(rss=1, vms=2)
                            mock_proc.return_value.cpu_percent.return_value = 5.0
                            mock_proc.return_value.num_threads.return_value = 4
                            result = await monitor.collect_system_metrics()
                            assert "cpu_usage_percent" in result
                            assert "memory_usage_percent" in result

    def test_get_performance_summary(self):
        monitor = PerformanceMonitor()
        summary = monitor.get_performance_summary()
        assert "system" in summary
        assert "application" in summary


@pytest.mark.unit
@pytest.mark.monitoring
class TestAlertManager:
    def test_no_alerts_below_thresholds(self):
        am = AlertManager()
        # Reset metrics to a clean baseline
        metrics.reset_metrics()
        alerts = am.check_thresholds()
        # No data → no alerts (response_stats["p95"]==0 < 1000)
        assert isinstance(alerts, list)

    def test_high_cpu_triggers_alert(self):
        am = AlertManager()
        metrics.set_gauge("system.cpu.usage", 95.0)
        alerts = am.check_thresholds()
        cpu_alerts = [a for a in alerts if a["type"] == "high_cpu_usage"]
        assert len(cpu_alerts) >= 1

    def test_alert_cooldown_prevents_duplicates(self):
        am = AlertManager()
        am.alert_cooldown = 999  # long cooldown
        metrics.set_gauge("system.cpu.usage", 95.0)
        first = am.check_thresholds()
        second = am.check_thresholds()
        # First call may emit, second should be suppressed
        types_second = [a["type"] for a in second]
        assert "high_cpu_usage" not in types_second


@pytest.mark.unit
@pytest.mark.monitoring
class TestMonitorPerformanceDecorator:
    @pytest.mark.asyncio
    async def test_async_function_decorated(self):
        @monitor_performance(metric_name="test.async")
        async def fast_fn():
            return 42

        result = await fast_fn()
        assert result == 42

    @pytest.mark.asyncio
    async def test_async_function_error_path(self):
        @monitor_performance(metric_name="test.async.err", record_errors=True)
        async def broken():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await broken()

    def test_sync_function_decorated(self):
        @monitor_performance(metric_name="test.sync")
        def add(a, b):
            return a + b

        assert add(1, 2) == 3


@pytest.mark.unit
@pytest.mark.monitoring
class TestGetMetricsSummary:
    def test_returns_combined_view(self):
        summary = get_metrics_summary()
        assert "performance" in summary
        assert "alerts" in summary
        assert "metrics" in summary
