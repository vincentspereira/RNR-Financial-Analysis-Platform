"""
Comprehensive unit tests for monitoring modules - 100% Coverage Target
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import asyncio
import threading
import time
from collections import deque

from app.core.monitoring import (
    MetricsCollector, PerformanceMonitor, AlertManager,
    metrics_collector, performance_monitor, alert_manager,
    MetricPoint, PerformanceMetrics
)


class TestMetricsCollector:
    """Comprehensive tests for MetricsCollector with 100% coverage"""
    
    @pytest.fixture
    def collector(self):
        """Fresh metrics collector for each test"""
        return MetricsCollector(max_points=100)
    
    def test_collector_initialization(self, collector):
        """Test collector initialization"""
        assert collector.max_points == 100
        assert len(collector.metrics) == 0
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert isinstance(collector.metrics, dict)
        assert isinstance(collector.counters, dict)
        assert isinstance(collector.gauges, dict)
    
    def test_record_metric_basic(self, collector):
        """Test basic metric recording"""
        collector.record_metric("test_metric", 10.5)
        
        assert "test_metric" in collector.metrics
        assert len(collector.metrics["test_metric"]) == 1
        
        metric_point = collector.metrics["test_metric"][0]
        assert isinstance(metric_point, MetricPoint)
        assert metric_point.value == 10.5
        assert isinstance(metric_point.timestamp, datetime)
        assert len(metric_point.tags) == 0
    
    def test_record_metric_with_tags(self, collector):
        """Test metric recording with tags"""
        tags = {"service": "api", "endpoint": "/health"}
        collector.record_metric("response_time", 150.0, tags=tags)
        
        metric_point = collector.metrics["response_time"][0]
        assert metric_point.tags == tags
        assert metric_point.value == 150.0
    
    def test_record_metric_multiple_values(self, collector):
        """Test recording multiple values for same metric"""
        collector.record_metric("cpu_usage", 50.0)
        collector.record_metric("cpu_usage", 60.0)
        collector.record_metric("cpu_usage", 70.0)
        
        assert len(collector.metrics["cpu_usage"]) == 3
        values = [point.value for point in collector.metrics["cpu_usage"]]
        assert values == [50.0, 60.0, 70.0]
    
    def test_increment_counter_basic(self, collector):
        """Test basic counter increment"""
        collector.increment_counter("requests")
        assert collector.counters["requests"] == 1
        
        collector.increment_counter("requests")
        assert collector.counters["requests"] == 2
    
    def test_increment_counter_with_value(self, collector):
        """Test counter increment with custom value"""
        collector.increment_counter("requests", 5)
        assert collector.counters["requests"] == 5
        
        collector.increment_counter("requests", 3)
        assert collector.counters["requests"] == 8
    
    def test_increment_counter_zero_value(self, collector):
        """Test counter increment with zero value"""
        collector.increment_counter("requests", 0)
        assert collector.counters["requests"] == 0
        
        collector.increment_counter("requests", 1)
        assert collector.counters["requests"] == 1
    
    def test_set_gauge_basic(self, collector):
        """Test basic gauge setting"""
        collector.set_gauge("cpu_usage", 75.5)
        assert collector.gauges["cpu_usage"] == 75.5
    
    def test_set_gauge_overwrite(self, collector):
        """Test gauge overwriting"""
        collector.set_gauge("memory_usage", 60.0)
        assert collector.gauges["memory_usage"] == 60.0
        
        collector.set_gauge("memory_usage", 80.0)
        assert collector.gauges["memory_usage"] == 80.0
    
    def test_max_points_limit(self, collector):
        """Test that metrics respect max_points limit"""
        # Add more metrics than max_points
        for i in range(150):
            collector.record_metric("test_metric", float(i))
        
        # Should only keep max_points (100) metrics
        assert len(collector.metrics["test_metric"]) == 100
        
        # Should keep the most recent metrics (50-149)
        values = [point.value for point in collector.metrics["test_metric"]]
        assert values[0] == 50.0  # First kept value
        assert values[-1] == 149.0  # Last value
    
    def test_get_metrics_by_name(self, collector):
        """Test retrieving metrics by name"""
        collector.record_metric("cpu", 50.0)
        collector.record_metric("memory", 60.0)
        collector.record_metric("cpu", 55.0)
        
        cpu_metrics = collector.get_metrics("cpu")
        assert len(cpu_metrics) == 2
        assert cpu_metrics[0].value == 50.0
        assert cpu_metrics[1].value == 55.0
        
        memory_metrics = collector.get_metrics("memory")
        assert len(memory_metrics) == 1
        assert memory_metrics[0].value == 60.0
    
    def test_get_metrics_nonexistent(self, collector):
        """Test retrieving non-existent metrics"""
        result = collector.get_metrics("nonexistent")
        assert result == []
    
    def test_get_all_metrics(self, collector):
        """Test retrieving all metrics"""
        collector.record_metric("cpu", 50.0)
        collector.increment_counter("requests")
        collector.set_gauge("memory", 60.0)
        
        all_metrics = collector.get_all_metrics()
        
        assert "metrics" in all_metrics
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        
        assert "cpu" in all_metrics["metrics"]
        assert all_metrics["counters"]["requests"] == 1
        assert all_metrics["gauges"]["memory"] == 60.0
    
    def test_get_all_metrics_empty(self, collector):
        """Test retrieving all metrics when empty"""
        all_metrics = collector.get_all_metrics()
        
        assert all_metrics["metrics"] == {}
        assert all_metrics["counters"] == {}
        assert all_metrics["gauges"] == {}
    
    def test_clear_metrics(self, collector):
        """Test clearing all metrics"""
        collector.record_metric("cpu", 50.0)
        collector.increment_counter("requests")
        collector.set_gauge("memory", 60.0)
        
        collector.clear_metrics()
        
        assert len(collector.metrics) == 0
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
    
    def test_clear_metrics_empty(self, collector):
        """Test clearing metrics when already empty"""
        collector.clear_metrics()  # Should not raise exception
        
        assert len(collector.metrics) == 0
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
    
    def test_concurrent_access(self, collector):
        """Test concurrent access to metrics collector"""
        def record_metrics(thread_id):
            for i in range(100):
                collector.record_metric(f"thread_{thread_id}", float(i))
                collector.increment_counter(f"counter_{thread_id}")
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_metrics, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all metrics were recorded
        for i in range(5):
            assert f"thread_{i}" in collector.metrics
            assert len(collector.metrics[f"thread_{i}"]) == 100
            assert collector.counters[f"counter_{i}"] == 100
    
    def test_metric_point_creation(self):
        """Test MetricPoint creation"""
        timestamp = datetime.utcnow()
        tags = {"service": "test"}
        
        point = MetricPoint(timestamp=timestamp, value=42.0, tags=tags)
        
        assert point.timestamp == timestamp
        assert point.value == 42.0
        assert point.tags == tags
    
    def test_metric_point_default_tags(self):
        """Test MetricPoint with default tags"""
        point = MetricPoint(timestamp=datetime.utcnow(), value=42.0)
        
        assert point.tags == {}
        assert isinstance(point.tags, dict)


class TestPerformanceMonitor:
    """Comprehensive tests for PerformanceMonitor with edge cases"""
    
    @pytest.fixture
    def monitor(self):
        """Fresh performance monitor for each test"""
        return PerformanceMonitor()
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector"""
        return Mock(spec=MetricsCollector)
    
    def test_monitor_initialization(self, monitor):
        """Test monitor initialization"""
        assert not monitor.is_monitoring
        assert monitor.monitoring_interval == 60
        assert len(monitor.performance_data) == 0
        assert monitor.monitoring_task is None
    
    def test_monitor_custom_interval(self):
        """Test monitor with custom interval"""
        monitor = PerformanceMonitor(monitoring_interval=30)
        assert monitor.monitoring_interval == 30
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor):
        """Test starting monitoring"""
        await monitor.start_monitoring()
        
        assert monitor.is_monitoring
        assert monitor.monitoring_task is not None
        assert not monitor.monitoring_task.done()
        
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self, monitor):
        """Test starting monitoring when already running"""
        await monitor.start_monitoring()
        first_task = monitor.monitoring_task
        
        # Starting again should not create new task
        await monitor.start_monitoring()
        assert monitor.monitoring_task is first_task
        
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor):
        """Test stopping monitoring"""
        await monitor.start_monitoring()
        task = monitor.monitoring_task
        
        await monitor.stop_monitoring()
        
        assert not monitor.is_monitoring
        assert monitor.monitoring_task is None
        assert task.cancelled()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_not_running(self, monitor):
        """Test stopping monitoring when not running"""
        # Should not raise exception
        await monitor.stop_monitoring()
        
        assert not monitor.is_monitoring
        assert monitor.monitoring_task is None
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, monitor):
        """Test system metrics collection"""
        with patch('psutil.cpu_percent', return_value=75.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_net:
            
            # Mock system metrics
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.percent = 45.0
            mock_net.return_value.bytes_sent = 1000000
            mock_net.return_value.bytes_recv = 2000000
            
            mock_collector = Mock()
            monitor.metrics_collector = mock_collector
            
            await monitor._collect_system_metrics()
            
            # Verify metrics were recorded
            mock_collector.set_gauge.assert_any_call("system.cpu_percent", 75.5)
            mock_collector.set_gauge.assert_any_call("system.memory_percent", 60.0)
            mock_collector.set_gauge.assert_any_call("system.disk_percent", 45.0)
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics_error(self, monitor):
        """Test system metrics collection with errors"""
        with patch('psutil.cpu_percent', side_effect=Exception("CPU error")):
            mock_collector = Mock()
            monitor.metrics_collector = mock_collector
            
            # Should handle error gracefully
            await monitor._collect_system_metrics()
            
            # Should not have recorded CPU metric
            cpu_calls = [call for call in mock_collector.set_gauge.call_args_list 
                        if "cpu_percent" in str(call)]
            assert len(cpu_calls) == 0
    
    def test_record_request_performance(self, monitor):
        """Test recording request performance"""
        monitor.record_request("/api/health", "GET", 150.0, 200)
        
        assert len(monitor.performance_data) == 1
        
        perf_data = monitor.performance_data[0]
        assert perf_data["endpoint"] == "/api/health"
        assert perf_data["method"] == "GET"
        assert perf_data["response_time"] == 150.0
        assert perf_data["status_code"] == 200
        assert isinstance(perf_data["timestamp"], datetime)
    
    def test_record_request_performance_multiple(self, monitor):
        """Test recording multiple request performances"""
        monitor.record_request("/api/health", "GET", 100.0, 200)
        monitor.record_request("/api/users", "POST", 200.0, 201)
        monitor.record_request("/api/error", "GET", 300.0, 500)
        
        assert len(monitor.performance_data) == 3
        
        endpoints = [data["endpoint"] for data in monitor.performance_data]
        assert "/api/health" in endpoints
        assert "/api/users" in endpoints
        assert "/api/error" in endpoints
    
    def test_get_performance_summary_with_data(self, monitor):
        """Test performance summary generation with data"""
        # Add sample performance data
        monitor.record_request("/api/health", "GET", 100.0, 200)
        monitor.record_request("/api/users", "GET", 200.0, 200)
        monitor.record_request("/api/error", "GET", 300.0, 500)
        monitor.record_request("/api/slow", "POST", 400.0, 200)
        
        summary = monitor.get_performance_summary()
        
        assert summary["total_requests"] == 4
        assert summary["success_count"] == 3  # Status codes 200, 200, 200
        assert summary["error_count"] == 1   # Status code 500
        assert summary["avg_response_time"] == 250.0  # (100+200+300+400)/4
        assert summary["error_rate"] == 0.25  # 1/4
        
        # Check percentiles
        assert summary["p95_response_time"] == 400.0
        assert summary["p99_response_time"] == 400.0
    
    def test_get_performance_summary_empty_data(self, monitor):
        """Test performance summary with no data"""
        summary = monitor.get_performance_summary()
        
        assert summary["total_requests"] == 0
        assert summary["success_count"] == 0
        assert summary["error_count"] == 0
        assert summary["avg_response_time"] == 0.0
        assert summary["error_rate"] == 0.0
        assert summary["p95_response_time"] == 0.0
        assert summary["p99_response_time"] == 0.0
    
    def test_performance_percentiles_calculation(self, monitor):
        """Test performance percentile calculations"""
        # Add response times: 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000
        for i in range(1, 11):
            monitor.record_request(f"/api/test{i}", "GET", i * 100.0, 200)
        
        summary = monitor.get_performance_summary()
        
        # For 10 values, 95th percentile should be 9.5th value = 950
        # For 10 values, 99th percentile should be 9.9th value = 990
        assert summary["p95_response_time"] == 950.0
        assert summary["p99_response_time"] == 990.0
    
    def test_performance_data_cleanup(self, monitor):
        """Test performance data cleanup for memory management"""
        # Add many performance records
        for i in range(2000):
            monitor.record_request(f"/api/test{i}", "GET", 100.0, 200)
        
        # Should limit data to prevent memory issues
        # (Implementation should have a max_records limit)
        assert len(monitor.performance_data) <= 1000  # Assuming 1000 is the limit
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_exception_handling(self, monitor):
        """Test monitoring loop exception handling"""
        with patch.object(monitor, '_collect_system_metrics', side_effect=Exception("Test error")):
            await monitor.start_monitoring()
            
            # Wait a bit for the monitoring task to run and handle exception
            await asyncio.sleep(0.1)
            
            # Monitor should still be running despite exception
            assert monitor.is_monitoring
            
            await monitor.stop_monitoring()
    
    def test_performance_metrics_dataclass(self):
        """Test PerformanceMetrics dataclass"""
        metrics = PerformanceMetrics()
        
        # Test default values
        assert metrics.response_times == []
        assert metrics.error_count == 0
        assert metrics.success_count == 0
        assert metrics.total_requests == 0
        assert metrics.avg_response_time == 0.0
        assert metrics.p95_response_time == 0.0
        assert metrics.p99_response_time == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.throughput == 0.0
        
        # Test with custom values
        custom_metrics = PerformanceMetrics(
            response_times=[100.0, 200.0, 300.0],
            error_count=5,
            success_count=95,
            total_requests=100,
            avg_response_time=200.0,
            p95_response_time=280.0,
            p99_response_time=295.0,
            error_rate=0.05,
            throughput=10.0
        )
        
        assert custom_metrics.response_times == [100.0, 200.0, 300.0]
        assert custom_metrics.error_count == 5
        assert custom_metrics.success_count == 95
        assert custom_metrics.total_requests == 100
        assert custom_metrics.avg_response_time == 200.0
        assert custom_metrics.p95_response_time == 280.0
        assert custom_metrics.p99_response_time == 295.0
        assert custom_metrics.error_rate == 0.05
        assert custom_metrics.throughput == 10.0


class TestAlertManager:
    """Comprehensive tests for AlertManager with threshold validation"""
    
    @pytest.fixture
    def alert_manager(self):
        """Fresh alert manager for each test"""
        return AlertManager()
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initialization"""
        assert len(alert_manager.thresholds) > 0  # Should have default thresholds
        assert alert_manager.alert_cooldown == 300  # 5 minutes default
        assert len(alert_manager.last_alerts) == 0
        assert alert_manager.metrics_collector is not None
    
    def test_alert_manager_custom_cooldown(self):
        """Test alert manager with custom cooldown"""
        manager = AlertManager(alert_cooldown=600)
        assert manager.alert_cooldown == 600
    
    def test_set_threshold(self, alert_manager):
        """Test setting custom thresholds"""
        alert_manager.set_threshold("custom_metric", 90.0, "greater_than")
        
        assert "custom_metric" in alert_manager.thresholds
        threshold = alert_manager.thresholds["custom_metric"]
        assert threshold["value"] == 90.0
        assert threshold["condition"] == "greater_than"
    
    def test_set_threshold_overwrite(self, alert_manager):
        """Test overwriting existing threshold"""
        alert_manager.set_threshold("cpu_usage", 70.0, "greater_than")
        alert_manager.set_threshold("cpu_usage", 85.0, "greater_than")
        
        threshold = alert_manager.thresholds["cpu_usage"]
        assert threshold["value"] == 85.0
    
    def test_check_thresholds_no_alerts(self, alert_manager):
        """Test threshold checking with no alerts"""
        # Set up metrics that don't trigger alerts
        mock_collector = Mock()
        mock_collector.get_all_metrics.return_value = {
            "gauges": {
                "system.cpu_percent": 50.0,  # Below default 80% threshold
                "system.memory_percent": 60.0  # Below default 85% threshold
            },
            "counters": {},
            "metrics": {}
        }
        
        alert_manager.metrics_collector = mock_collector
        alerts = alert_manager.check_thresholds()
        
        assert len(alerts) == 0
    
    def test_check_thresholds_with_alerts(self, alert_manager):
        """Test threshold checking with triggered alerts"""
        # Set up metrics that trigger alerts
        mock_collector = Mock()
        mock_collector.get_all_metrics.return_value = {
            "gauges": {
                "system.cpu_percent": 95.0,  # Above default 80% threshold
                "system.memory_percent": 90.0  # Above default 85% threshold
            },
            "counters": {},
            "metrics": {}
        }
        
        alert_manager.metrics_collector = mock_collector
        alerts = alert_manager.check_thresholds()
        
        assert len(alerts) >= 2
        
        # Check that alerts contain expected information
        alert_types = [alert["alert_type"] for alert in alerts]
        assert any("cpu" in alert_type.lower() for alert_type in alert_types)
        assert any("memory" in alert_type.lower() for alert_type in alert_types)
    
    def test_check_thresholds_less_than_condition(self, alert_manager):
        """Test threshold checking with less_than condition"""
        # Set a threshold for low disk space
        alert_manager.set_threshold("system.disk_free_percent", 10.0, "less_than")
        
        mock_collector = Mock()
        mock_collector.get_all_metrics.return_value = {
            "gauges": {
                "system.disk_free_percent": 5.0  # Below 10% threshold
            },
            "counters": {},
            "metrics": {}
        }
        
        alert_manager.metrics_collector = mock_collector
        alerts = alert_manager.check_thresholds()
        
        assert len(alerts) >= 1
        disk_alerts = [alert for alert in alerts if "disk" in alert["alert_type"].lower()]
        assert len(disk_alerts) >= 1
    
    def test_alert_cooldown_functionality(self, alert_manager):
        """Test alert cooldown functionality"""
        current_time = datetime.utcnow()
        
        # First alert should be sent
        assert alert_manager._should_send_alert("test_alert", current_time)
        
        # Immediate second alert should be blocked
        assert not alert_manager._should_send_alert("test_alert", current_time)
        
        # After cooldown period, alert should be allowed
        future_time = current_time + timedelta(seconds=alert_manager.alert_cooldown + 1)
        assert alert_manager._should_send_alert("test_alert", future_time)
    
    def test_alert_cooldown_different_types(self, alert_manager):
        """Test alert cooldown for different alert types"""
        current_time = datetime.utcnow()
        
        # Different alert types should have independent cooldowns
        assert alert_manager._should_send_alert("cpu_alert", current_time)
        assert alert_manager._should_send_alert("memory_alert", current_time)
        
        # Same types should be blocked
        assert not alert_manager._should_send_alert("cpu_alert", current_time)
        assert not alert_manager._should_send_alert("memory_alert", current_time)
    
    def test_create_alert_message(self, alert_manager):
        """Test alert message creation"""
        alert_data = {
            "metric": "cpu_usage",
            "current_value": 95.0,
            "threshold": 80.0,
            "severity": "critical"
        }
        
        message = alert_manager._create_alert_message("high_cpu_usage", alert_data)
        
        assert message["alert_type"] == "high_cpu_usage"
        assert message["severity"] == "critical"
        assert "timestamp" in message
        assert "data" in message
        assert message["data"] == alert_data
        assert isinstance(message["timestamp"], str)
    
    def test_create_alert_message_default_severity(self, alert_manager):
        """Test alert message creation with default severity"""
        alert_data = {
            "metric": "memory_usage",
            "current_value": 90.0,
            "threshold": 85.0
        }
        
        message = alert_manager._create_alert_message("high_memory_usage", alert_data)
        
        assert message["severity"] == "warning"  # Default severity
    
    def test_check_thresholds_with_counters(self, alert_manager):
        """Test threshold checking with counter metrics"""
        # Set threshold for error count
        alert_manager.set_threshold("error_count", 100, "greater_than")
        
        mock_collector = Mock()
        mock_collector.get_all_metrics.return_value = {
            "gauges": {},
            "counters": {
                "error_count": 150  # Above threshold
            },
            "metrics": {}
        }
        
        alert_manager.metrics_collector = mock_collector
        alerts = alert_manager.check_thresholds()
        
        error_alerts = [alert for alert in alerts if "error_count" in alert["alert_type"]]
        assert len(error_alerts) >= 1
    
    def test_check_thresholds_metrics_collection_error(self, alert_manager):
        """Test threshold checking when metrics collection fails"""
        mock_collector = Mock()
        mock_collector.get_all_metrics.side_effect = Exception("Metrics unavailable")
        
        alert_manager.metrics_collector = mock_collector
        
        # Should handle error gracefully
        alerts = alert_manager.check_thresholds()
        assert alerts == []
    
    def test_default_thresholds_setup(self, alert_manager):
        """Test that default thresholds are properly set up"""
        # Should have common system thresholds
        assert "system.cpu_percent" in alert_manager.thresholds
        assert "system.memory_percent" in alert_manager.thresholds
        
        # Verify threshold structure
        cpu_threshold = alert_manager.thresholds["system.cpu_percent"]
        assert "value" in cpu_threshold
        assert "condition" in cpu_threshold
        assert cpu_threshold["condition"] == "greater_than"
        assert isinstance(cpu_threshold["value"], (int, float))


class TestGlobalInstances:
    """Test global monitoring instances"""
    
    def test_global_metrics_collector(self):
        """Test global metrics collector instance"""
        assert metrics_collector is not None
        assert isinstance(metrics_collector, MetricsCollector)
    
    def test_global_performance_monitor(self):
        """Test global performance monitor instance"""
        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)
    
    def test_global_alert_manager(self):
        """Test global alert manager instance"""
        assert alert_manager is not None
        assert isinstance(alert_manager, AlertManager)
    
    def test_global_instances_independence(self):
        """Test that global instances are independent"""
        # Record metric in global collector
        metrics_collector.record_metric("test_global", 42.0)
        
        # Create new collector
        new_collector = MetricsCollector()
        
        # New collector should not have the metric
        assert "test_global" not in new_collector.metrics
        assert "test_global" in metrics_collector.metrics
        
        # Clean up
        metrics_collector.clear_metrics()


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error conditions"""
    
    def test_metrics_collector_with_none_values(self):
        """Test metrics collector with None values"""
        collector = MetricsCollector()
        
        # Should handle None gracefully or raise appropriate error
        try:
            collector.record_metric("test", None)
            # If it doesn't raise an error, verify it's handled properly
            metrics = collector.get_metrics("test")
            if len(metrics) > 0:
                assert metrics[0].value is None
        except (ValueError, TypeError):
            # This is also acceptable behavior
            pass
    
    def test_metrics_collector_with_invalid_types(self):
        """Test metrics collector with invalid data types"""
        collector = MetricsCollector()
        
        # Test with string that can't be converted to number
        with pytest.raises((ValueError, TypeError)):
            collector.record_metric("test", "invalid_number")
    
    def test_performance_monitor_concurrent_requests(self):
        """Test performance monitor with concurrent request recording"""
        monitor = PerformanceMonitor()
        
        def record_requests(thread_id):
            for i in range(100):
                monitor.record_request(f"/api/test{thread_id}_{i}", "GET", i * 10.0, 200)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_requests, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should be recorded
        assert len(monitor.performance_data) == 500
    
    @pytest.mark.asyncio
    async def test_monitoring_task_cancellation(self):
        """Test proper monitoring task cancellation"""
        monitor = PerformanceMonitor()
        
        await monitor.start_monitoring()
        task = monitor.monitoring_task
        
        # Cancel the task directly
        task.cancel()
        
        # Stop monitoring should handle cancelled task gracefully
        await monitor.stop_monitoring()
        
        assert not monitor.is_monitoring
        assert monitor.monitoring_task is None
    
    def test_alert_manager_with_empty_metrics(self):
        """Test alert manager with empty metrics"""
        alert_manager = AlertManager()
        
        mock_collector = Mock()
        mock_collector.get_all_metrics.return_value = {
            "gauges": {},
            "counters": {},
            "metrics": {}
        }
        
        alert_manager.metrics_collector = mock_collector
        alerts = alert_manager.check_thresholds()
        
        # Should not crash with empty metrics
        assert alerts == []
    
    def test_performance_summary_with_single_request(self):
        """Test performance summary with only one request"""
        monitor = PerformanceMonitor()
        monitor.record_request("/api/single", "GET", 150.0, 200)
        
        summary = monitor.get_performance_summary()
        
        assert summary["total_requests"] == 1
        assert summary["success_count"] == 1
        assert summary["error_count"] == 0
        assert summary["avg_response_time"] == 150.0
        assert summary["error_rate"] == 0.0
        assert summary["p95_response_time"] == 150.0
        assert summary["p99_response_time"] == 150.0
    
    def test_deque_maxlen_behavior(self):
        """Test deque maxlen behavior in MetricsCollector"""
        collector = MetricsCollector(max_points=3)
        
        # Add more items than maxlen
        collector.record_metric("test", 1.0)
        collector.record_metric("test", 2.0)
        collector.record_metric("test", 3.0)
        collector.record_metric("test", 4.0)  # Should evict first item
        
        metrics = collector.get_metrics("test")
        assert len(metrics) == 3
        values = [m.value for m in metrics]
        assert values == [2.0, 3.0, 4.0]  # First item (1.0) should be evicted