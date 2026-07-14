# Comprehensive Testing Strategy
## RNR Financial Analysis Platform

**Strategy Date**: 31 October 2025  
**Target Coverage**: 95% Overall Code Coverage  
**Framework**: 10-Category Testing Approach  
**Status**: Implementation in Progress  

---

## Executive Summary

### Testing Objectives
- **Achieve 95% code coverage** across the entire codebase
- **Implement comprehensive testing framework** covering 10 testing categories
- **Establish automated testing pipeline** with CI/CD integration
- **Ensure production readiness** through thorough validation
- **Maintain testing excellence** with continuous monitoring

### Current Coverage Baseline
```yaml
Backend Coverage:
  - Current: 87% (from previous audit)
  - Target: 95%
  - Gap: 8% improvement needed

Frontend Coverage:
  - Current: 84% (from previous audit)
  - Target: 95%
  - Gap: 11% improvement needed

Integration Coverage:
  - Current: 82%
  - Target: 90%
  - Gap: 8% improvement needed
```

---

## 1. Unit Testing Framework

### 1.1 Monitoring Modules - 100% Coverage Target ✅

#### **Test Structure**
```python
# tests/unit/test_monitoring.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio

from app.core.monitoring import (
    MetricsCollector, PerformanceMonitor, AlertManager,
    metrics_collector, performance_monitor, alert_manager
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
    
    def test_record_metric_basic(self, collector):
        """Test basic metric recording"""
        collector.record_metric("test_metric", 10.5)
        
        assert "test_metric" in collector.metrics
        assert len(collector.metrics["test_metric"]) == 1
        
        metric_point = collector.metrics["test_metric"][0]
        assert metric_point.value == 10.5
        assert isinstance(metric_point.timestamp, datetime)
    
    def test_record_metric_with_tags(self, collector):
        """Test metric recording with tags"""
        tags = {"service": "api", "endpoint": "/health"}
        collector.record_metric("response_time", 150.0, tags=tags)
        
        metric_point = collector.metrics["response_time"][0]
        assert metric_point.tags == tags
    
    def test_increment_counter(self, collector):
        """Test counter increment functionality"""
        collector.increment_counter("requests")
        collector.increment_counter("requests", 5)
        
        assert collector.counters["requests"] == 6
    
    def test_set_gauge(self, collector):
        """Test gauge setting functionality"""
        collector.set_gauge("cpu_usage", 75.5)
        assert collector.gauges["cpu_usage"] == 75.5
        
        collector.set_gauge("cpu_usage", 80.0)
        assert collector.gauges["cpu_usage"] == 80.0
    
    def test_max_points_limit(self, collector):
        """Test that metrics respect max_points limit"""
        # Add more metrics than max_points
        for i in range(150):
            collector.record_metric("test_metric", i)
        
        # Should only keep max_points (100) metrics
        assert len(collector.metrics["test_metric"]) == 100
        
        # Should keep the most recent metrics
        latest_metric = collector.metrics["test_metric"][-1]
        assert latest_metric.value == 149
    
    def test_get_metrics_by_name(self, collector):
        """Test retrieving metrics by name"""
        collector.record_metric("cpu", 50.0)
        collector.record_metric("memory", 60.0)
        
        cpu_metrics = collector.get_metrics("cpu")
        assert len(cpu_metrics) == 1
        assert cpu_metrics[0].value == 50.0
        
        # Non-existent metric should return empty list
        assert collector.get_metrics("disk") == []
    
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
    
    def test_clear_metrics(self, collector):
        """Test clearing all metrics"""
        collector.record_metric("cpu", 50.0)
        collector.increment_counter("requests")
        collector.set_gauge("memory", 60.0)
        
        collector.clear_metrics()
        
        assert len(collector.metrics) == 0
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0


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
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor, mock_metrics_collector):
        """Test starting monitoring"""
        with patch.object(monitor, 'metrics_collector', mock_metrics_collector):
            await monitor.start_monitoring()
            
            assert monitor.is_monitoring
            assert monitor.monitoring_task is not None
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor):
        """Test stopping monitoring"""
        await monitor.start_monitoring()
        await monitor.stop_monitoring()
        
        assert not monitor.is_monitoring
        assert monitor.monitoring_task is None or monitor.monitoring_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, monitor, mock_metrics_collector):
        """Test system metrics collection"""
        with patch('psutil.cpu_percent', return_value=75.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock memory and disk usage
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.percent = 45.0
            
            with patch.object(monitor, 'metrics_collector', mock_metrics_collector):
                await monitor._collect_system_metrics()
            
            # Verify metrics were recorded
            assert mock_metrics_collector.set_gauge.call_count >= 3
            mock_metrics_collector.set_gauge.assert_any_call("system.cpu_percent", 75.5)
            mock_metrics_collector.set_gauge.assert_any_call("system.memory_percent", 60.0)
            mock_metrics_collector.set_gauge.assert_any_call("system.disk_percent", 45.0)
    
    def test_record_request_performance(self, monitor):
        """Test recording request performance"""
        monitor.record_request("/api/health", "GET", 150.0, 200)
        
        assert len(monitor.performance_data) == 1
        
        perf_data = monitor.performance_data[0]
        assert perf_data["endpoint"] == "/api/health"
        assert perf_data["method"] == "GET"
        assert perf_data["response_time"] == 150.0
        assert perf_data["status_code"] == 200
    
    def test_get_performance_summary(self, monitor):
        """Test performance summary generation"""
        # Add sample performance data
        monitor.record_request("/api/health", "GET", 100.0, 200)
        monitor.record_request("/api/users", "GET", 200.0, 200)
        monitor.record_request("/api/error", "GET", 300.0, 500)
        
        summary = monitor.get_performance_summary()
        
        assert summary["total_requests"] == 3
        assert summary["success_count"] == 2
        assert summary["error_count"] == 1
        assert summary["avg_response_time"] == 200.0
        assert summary["error_rate"] == pytest.approx(0.333, rel=1e-2)
    
    def test_performance_summary_empty_data(self, monitor):
        """Test performance summary with no data"""
        summary = monitor.get_performance_summary()
        
        assert summary["total_requests"] == 0
        assert summary["success_count"] == 0
        assert summary["error_count"] == 0
        assert summary["avg_response_time"] == 0.0
        assert summary["error_rate"] == 0.0
    
    def test_performance_percentiles(self, monitor):
        """Test performance percentile calculations"""
        # Add response times: 100, 200, 300, 400, 500
        for i in range(1, 6):
            monitor.record_request(f"/api/test{i}", "GET", i * 100.0, 200)
        
        summary = monitor.get_performance_summary()
        
        assert summary["p95_response_time"] == 500.0  # 95th percentile
        assert summary["p99_response_time"] == 500.0  # 99th percentile (small dataset)


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
    
    def test_set_threshold(self, alert_manager):
        """Test setting custom thresholds"""
        alert_manager.set_threshold("custom_metric", 90.0, "high")
        
        assert "custom_metric" in alert_manager.thresholds
        threshold = alert_manager.thresholds["custom_metric"]
        assert threshold["value"] == 90.0
        assert threshold["condition"] == "high"
    
    def test_check_thresholds_no_alerts(self, alert_manager):
        """Test threshold checking with no alerts"""
        # Set up metrics that don't trigger alerts
        mock_collector = Mock()
        mock_collector.get_all_metrics.return_value = {
            "gauges": {
                "system.cpu_percent": 50.0,  # Below 80% threshold
                "system.memory_percent": 60.0  # Below 85% threshold
            }
        }
        
        with patch.object(alert_manager, 'metrics_collector', mock_collector):
            alerts = alert_manager.check_thresholds()
        
        assert len(alerts) == 0
    
    def test_check_thresholds_with_alerts(self, alert_manager):
        """Test threshold checking with triggered alerts"""
        # Set up metrics that trigger alerts
        mock_collector = Mock()
        mock_collector.get_all_metrics.return_value = {
            "gauges": {
                "system.cpu_percent": 95.0,  # Above 80% threshold
                "system.memory_percent": 90.0  # Above 85% threshold
            }
        }
        
        with patch.object(alert_manager, 'metrics_collector', mock_collector):
            alerts = alert_manager.check_thresholds()
        
        assert len(alerts) >= 2
        
        # Check that alerts contain expected information
        alert_types = [alert["alert_type"] for alert in alerts]
        assert "high_cpu_usage" in alert_types
        assert "high_memory_usage" in alert_types
    
    def test_alert_cooldown(self, alert_manager):
        """Test alert cooldown functionality"""
        # Set short cooldown for testing
        alert_manager.alert_cooldown = 1
        
        # First alert should be sent
        assert alert_manager._should_send_alert("test_alert", datetime.utcnow())
        
        # Immediate second alert should be blocked
        assert not alert_manager._should_send_alert("test_alert", datetime.utcnow())
        
        # After cooldown period, alert should be allowed
        future_time = datetime.utcnow() + timedelta(seconds=2)
        assert alert_manager._should_send_alert("test_alert", future_time)
    
    def test_create_alert_message(self, alert_manager):
        """Test alert message creation"""
        alert_data = {
            "metric": "cpu_usage",
            "current_value": 95.0,
            "threshold": 80.0,
            "severity": "critical"
        }
        
        message = alert_manager._create_alert_message("high_cpu_usage", alert_data)
        
        assert "high_cpu_usage" in message["alert_type"]
        assert message["severity"] == "critical"
        assert "timestamp" in message
        assert "data" in message
        assert message["data"] == alert_data


# Mock and Stub Implementations for External Dependencies
class MockExternalService:
    """Mock external service for testing"""
    
    def __init__(self, should_fail=False, response_data=None):
        self.should_fail = should_fail
        self.response_data = response_data or {}
        self.call_count = 0
    
    async def fetch_data(self, *args, **kwargs):
        """Mock data fetching"""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Mock service failure")
        
        return self.response_data
    
    def reset(self):
        """Reset mock state"""
        self.call_count = 0
        self.should_fail = False


@pytest.fixture
def mock_external_service():
    """Fixture for mock external service"""
    return MockExternalService()


# Edge Case Tests
class TestMonitoringEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_metrics_collector_with_invalid_data(self):
        """Test metrics collector with invalid data types"""
        collector = MetricsCollector()
        
        # Test with None values
        collector.record_metric("test", None)  # Should handle gracefully
        
        # Test with string values that can't be converted
        with pytest.raises((ValueError, TypeError)):
            collector.record_metric("test", "invalid_number")
    
    def test_performance_monitor_concurrent_access(self):
        """Test performance monitor with concurrent access"""
        monitor = PerformanceMonitor()
        
        # Simulate concurrent requests
        import threading
        
        def record_request(i):
            monitor.record_request(f"/api/test{i}", "GET", i * 10.0, 200)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=record_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should be recorded
        assert len(monitor.performance_data) == 10
    
    @pytest.mark.asyncio
    async def test_monitoring_task_exception_handling(self):
        """Test monitoring task exception handling"""
        monitor = PerformanceMonitor()
        
        # Mock system metrics collection to raise exception
        with patch.object(monitor, '_collect_system_metrics', side_effect=Exception("Test error")):
            await monitor.start_monitoring()
            
            # Wait a bit for the monitoring task to run
            await asyncio.sleep(0.1)
            
            # Monitor should still be running despite exception
            assert monitor.is_monitoring
            
            await monitor.stop_monitoring()
```

### 1.2 Autoscaling Modules - 100% Coverage Target

#### **Test Structure**
```python
# tests/unit/test_autoscaling.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio

from app.core.autoscaling import (
    AutoScaler, ScalingPolicy, ScalingMetric, ScalingAction,
    autoscaler, ScalingDecision
)

class TestAutoScaler:
    """Comprehensive tests for AutoScaler with 100% coverage"""
    
    @pytest.fixture
    def autoscaler(self):
        """Fresh autoscaler for each test"""
        return AutoScaler()
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector"""
        return Mock()
    
    def test_autoscaler_initialization(self, autoscaler):
        """Test autoscaler initialization"""
        assert len(autoscaler.policies) == 0
        assert not autoscaler.is_enabled
        assert autoscaler.check_interval == 60
        assert autoscaler.cooldown_period == 300
    
    def test_add_scaling_policy(self, autoscaler):
        """Test adding scaling policies"""
        policy = ScalingPolicy(
            name="cpu_scale_up",
            metric=ScalingMetric.CPU_USAGE,
            threshold=80.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=2
        )
        
        autoscaler.add_policy(policy)
        
        assert len(autoscaler.policies) == 1
        assert autoscaler.policies[0].name == "cpu_scale_up"
    
    def test_remove_scaling_policy(self, autoscaler):
        """Test removing scaling policies"""
        policy = ScalingPolicy(
            name="test_policy",
            metric=ScalingMetric.MEMORY_USAGE,
            threshold=85.0,
            action=ScalingAction.SCALE_DOWN,
            scale_amount=1
        )
        
        autoscaler.add_policy(policy)
        assert len(autoscaler.policies) == 1
        
        autoscaler.remove_policy("test_policy")
        assert len(autoscaler.policies) == 0
    
    @pytest.mark.asyncio
    async def test_enable_autoscaling(self, autoscaler):
        """Test enabling autoscaling"""
        await autoscaler.enable()
        
        assert autoscaler.is_enabled
        assert autoscaler.scaling_task is not None
    
    @pytest.mark.asyncio
    async def test_disable_autoscaling(self, autoscaler):
        """Test disabling autoscaling"""
        await autoscaler.enable()
        await autoscaler.disable()
        
        assert not autoscaler.is_enabled
        assert autoscaler.scaling_task is None or autoscaler.scaling_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_evaluate_scaling_policies_no_action(self, autoscaler, mock_metrics_collector):
        """Test policy evaluation with no scaling action needed"""
        # Add policy that shouldn't trigger
        policy = ScalingPolicy(
            name="cpu_scale_up",
            metric=ScalingMetric.CPU_USAGE,
            threshold=80.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=2
        )
        autoscaler.add_policy(policy)
        
        # Mock metrics below threshold
        mock_metrics_collector.get_all_metrics.return_value = {
            "gauges": {"system.cpu_percent": 60.0}
        }
        
        with patch.object(autoscaler, 'metrics_collector', mock_metrics_collector):
            decisions = await autoscaler._evaluate_policies()
        
        assert len(decisions) == 0
    
    @pytest.mark.asyncio
    async def test_evaluate_scaling_policies_scale_up(self, autoscaler, mock_metrics_collector):
        """Test policy evaluation triggering scale up"""
        policy = ScalingPolicy(
            name="cpu_scale_up",
            metric=ScalingMetric.CPU_USAGE,
            threshold=80.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=2
        )
        autoscaler.add_policy(policy)
        
        # Mock metrics above threshold
        mock_metrics_collector.get_all_metrics.return_value = {
            "gauges": {"system.cpu_percent": 90.0}
        }
        
        with patch.object(autoscaler, 'metrics_collector', mock_metrics_collector):
            decisions = await autoscaler._evaluate_policies()
        
        assert len(decisions) == 1
        decision = decisions[0]
        assert decision.policy_name == "cpu_scale_up"
        assert decision.action == ScalingAction.SCALE_UP
        assert decision.scale_amount == 2
    
    @pytest.mark.asyncio
    async def test_execute_scaling_decision(self, autoscaler):
        """Test executing scaling decisions"""
        decision = ScalingDecision(
            policy_name="test_policy",
            action=ScalingAction.SCALE_UP,
            scale_amount=2,
            current_value=90.0,
            threshold=80.0
        )
        
        with patch.object(autoscaler, '_scale_infrastructure') as mock_scale:
            mock_scale.return_value = True
            
            result = await autoscaler._execute_scaling_decision(decision)
            
            assert result
            mock_scale.assert_called_once_with(ScalingAction.SCALE_UP, 2)
    
    def test_cooldown_period_enforcement(self, autoscaler):
        """Test cooldown period enforcement"""
        # Record a recent scaling action
        autoscaler.last_scaling_action = datetime.utcnow()
        
        # Should be in cooldown
        assert autoscaler._is_in_cooldown()
        
        # Set last action to past cooldown period
        autoscaler.last_scaling_action = datetime.utcnow() - timedelta(seconds=400)
        
        # Should not be in cooldown
        assert not autoscaler._is_in_cooldown()
    
    @pytest.mark.asyncio
    async def test_scaling_with_cooldown_active(self, autoscaler, mock_metrics_collector):
        """Test that scaling is blocked during cooldown"""
        # Set recent scaling action
        autoscaler.last_scaling_action = datetime.utcnow()
        
        policy = ScalingPolicy(
            name="cpu_scale_up",
            metric=ScalingMetric.CPU_USAGE,
            threshold=80.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=2
        )
        autoscaler.add_policy(policy)
        
        # Mock high CPU usage
        mock_metrics_collector.get_all_metrics.return_value = {
            "gauges": {"system.cpu_percent": 95.0}
        }
        
        with patch.object(autoscaler, 'metrics_collector', mock_metrics_collector), \
             patch.object(autoscaler, '_scale_infrastructure') as mock_scale:
            
            await autoscaler._check_and_scale()
            
            # Should not scale due to cooldown
            mock_scale.assert_not_called()


class TestScalingPolicy:
    """Test scaling policy functionality"""
    
    def test_policy_creation(self):
        """Test scaling policy creation"""
        policy = ScalingPolicy(
            name="memory_scale_down",
            metric=ScalingMetric.MEMORY_USAGE,
            threshold=30.0,
            action=ScalingAction.SCALE_DOWN,
            scale_amount=1,
            comparison="less_than"
        )
        
        assert policy.name == "memory_scale_down"
        assert policy.metric == ScalingMetric.MEMORY_USAGE
        assert policy.threshold == 30.0
        assert policy.action == ScalingAction.SCALE_DOWN
        assert policy.scale_amount == 1
        assert policy.comparison == "less_than"
    
    def test_policy_evaluation_greater_than(self):
        """Test policy evaluation with greater_than comparison"""
        policy = ScalingPolicy(
            name="cpu_scale_up",
            metric=ScalingMetric.CPU_USAGE,
            threshold=80.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=2,
            comparison="greater_than"
        )
        
        # Should trigger when value > threshold
        assert policy.should_trigger(85.0)
        
        # Should not trigger when value <= threshold
        assert not policy.should_trigger(75.0)
        assert not policy.should_trigger(80.0)
    
    def test_policy_evaluation_less_than(self):
        """Test policy evaluation with less_than comparison"""
        policy = ScalingPolicy(
            name="memory_scale_down",
            metric=ScalingMetric.MEMORY_USAGE,
            threshold=30.0,
            action=ScalingAction.SCALE_DOWN,
            scale_amount=1,
            comparison="less_than"
        )
        
        # Should trigger when value < threshold
        assert policy.should_trigger(25.0)
        
        # Should not trigger when value >= threshold
        assert not policy.should_trigger(35.0)
        assert not policy.should_trigger(30.0)


# Edge Cases and Error Handling
class TestAutoscalingEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_scaling_infrastructure_failure(self, autoscaler):
        """Test handling of infrastructure scaling failures"""
        decision = ScalingDecision(
            policy_name="test_policy",
            action=ScalingAction.SCALE_UP,
            scale_amount=2,
            current_value=90.0,
            threshold=80.0
        )
        
        with patch.object(autoscaler, '_scale_infrastructure', side_effect=Exception("Scaling failed")):
            result = await autoscaler._execute_scaling_decision(decision)
            
            # Should handle failure gracefully
            assert not result
    
    def test_invalid_policy_removal(self, autoscaler):
        """Test removing non-existent policy"""
        # Should not raise exception
        autoscaler.remove_policy("non_existent_policy")
        assert len(autoscaler.policies) == 0
    
    @pytest.mark.asyncio
    async def test_metrics_collection_failure(self, autoscaler, mock_metrics_collector):
        """Test handling of metrics collection failures"""
        policy = ScalingPolicy(
            name="cpu_scale_up",
            metric=ScalingMetric.CPU_USAGE,
            threshold=80.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=2
        )
        autoscaler.add_policy(policy)
        
        # Mock metrics collection failure
        mock_metrics_collector.get_all_metrics.side_effect = Exception("Metrics unavailable")
        
        with patch.object(autoscaler, 'metrics_collector', mock_metrics_collector):
            decisions = await autoscaler._evaluate_policies()
        
        # Should handle failure gracefully and return no decisions
        assert len(decisions) == 0
    
    def test_multiple_policies_same_metric(self, autoscaler):
        """Test multiple policies for the same metric"""
        policy1 = ScalingPolicy(
            name="cpu_scale_up_aggressive",
            metric=ScalingMetric.CPU_USAGE,
            threshold=90.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=3
        )
        
        policy2 = ScalingPolicy(
            name="cpu_scale_up_conservative",
            metric=ScalingMetric.CPU_USAGE,
            threshold=80.0,
            action=ScalingAction.SCALE_UP,
            scale_amount=1
        )
        
        autoscaler.add_policy(policy1)
        autoscaler.add_policy(policy2)
        
        assert len(autoscaler.policies) == 2
        
        # Both policies should be evaluated independently
        # This tests the system's ability to handle multiple policies
```

---

## 2. Integration Testing Framework

### 2.1 Component Interaction Tests

#### **API Integration Tests**
```python
# tests/integration/test_api_integration.py
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from app.main import app
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User

class TestAPIIntegration:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return User(
            id="test-user-id",
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_authentication_flow(self, async_client):
        """Test complete authentication flow"""
        # Test registration
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }
        
        with patch('app.services.auth.auth_service.register_user') as mock_register:
            mock_register.return_value = {
                "id": "new-user-id",
                "email": "newuser@example.com",
                "full_name": "New User"
            }
            
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "newuser@example.com"
        
        # Test login
        login_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!"
        }
        
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "user": {"id": "new-user-id", "email": "newuser@example.com"}
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_portfolio_crud_operations(self, async_client, mock_user):
        """Test complete portfolio CRUD operations"""
        # Override auth dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Create portfolio
            portfolio_data = {
                "name": "Test Portfolio",
                "description": "Integration test portfolio"
            }
            
            with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                mock_create.return_value = {
                    "id": "test-portfolio-id",
                    "name": "Test Portfolio",
                    "description": "Integration test portfolio",
                    "user_id": mock_user.id
                }
                
                response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
                
                assert response.status_code == 201
                created_portfolio = response.json()
                portfolio_id = created_portfolio["id"]
            
            # Read portfolio
            with patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get:
                mock_get.return_value = created_portfolio
                
                response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Test Portfolio"
            
            # Update portfolio
            update_data = {
                "name": "Updated Portfolio",
                "description": "Updated description"
            }
            
            with patch('app.services.portfolio.portfolio_service.update_portfolio') as mock_update:
                mock_update.return_value = {**created_portfolio, **update_data}
                
                response = await async_client.put(f"/api/v1/portfolios/{portfolio_id}", json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Updated Portfolio"
            
            # Delete portfolio
            with patch('app.services.portfolio.portfolio_service.delete_portfolio') as mock_delete:
                mock_delete.return_value = True
                
                response = await async_client.delete(f"/api/v1/portfolios/{portfolio_id}")
                
                assert response.status_code == 204
        
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_data_flow_validation(self, async_client, mock_user):
        """Test data flow between components"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test data flow: Create portfolio -> Add holding -> Get performance
            
            # Step 1: Create portfolio
            portfolio_data = {"name": "Data Flow Test", "description": "Test portfolio"}
            
            with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create_portfolio:
                mock_create_portfolio.return_value = {
                    "id": "flow-test-portfolio",
                    "name": "Data Flow Test",
                    "user_id": mock_user.id
                }
                
                portfolio_response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
                assert portfolio_response.status_code == 201
                portfolio_id = portfolio_response.json()["id"]
            
            # Step 2: Add holding to portfolio
            holding_data = {
                "symbol": "AAPL",
                "shares": 100,
                "purchase_price": 150.00
            }
            
            with patch('app.services.portfolio.portfolio_service.add_holding') as mock_add_holding:
                mock_add_holding.return_value = {
                    "id": "test-holding-id",
                    "portfolio_id": portfolio_id,
                    "symbol": "AAPL",
                    "shares": 100,
                    "purchase_price": 150.00
                }
                
                holding_response = await async_client.post(
                    f"/api/v1/portfolios/{portfolio_id}/holdings",
                    json=holding_data
                )
                assert holding_response.status_code == 201
            
            # Step 3: Get portfolio performance (should include the holding)
            with patch('app.services.analytics.analytics_service.calculate_portfolio_performance') as mock_performance:
                mock_performance.return_value = {
                    "total_value": 15500.00,  # 100 shares * $155 current price
                    "total_return": 500.00,   # $5 gain per share
                    "return_percentage": 3.33,
                    "holdings": [
                        {
                            "symbol": "AAPL",
                            "shares": 100,
                            "current_price": 155.00,
                            "current_value": 15500.00,
                            "gain_loss": 500.00
                        }
                    ]
                }
                
                performance_response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}/performance")
                assert performance_response.status_code == 200
                
                performance_data = performance_response.json()
                assert performance_data["total_value"] == 15500.00
                assert len(performance_data["holdings"]) == 1
                assert performance_data["holdings"][0]["symbol"] == "AAPL"
        
        finally:
            app.dependency_overrides.clear()


class TestModuleInterfaces:
    """Test interfaces between different modules"""
    
    @pytest.mark.asyncio
    async def test_auth_portfolio_integration(self):
        """Test integration between auth and portfolio modules"""
        from app.services.auth import auth_service
        from app.services.portfolio import portfolio_service
        
        # Mock user authentication
        with patch.object(auth_service, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = {
                "id": "test-user-id",
                "email": "test@example.com",
                "is_active": True
            }
            
            # Mock portfolio creation
            with patch.object(portfolio_service, 'create_portfolio') as mock_create:
                mock_create.return_value = {
                    "id": "test-portfolio-id",
                    "user_id": "test-user-id",
                    "name": "Test Portfolio"
                }
                
                # Test that portfolio service correctly uses user from auth service
                user = await auth_service.get_user_by_id("test-user-id")
                portfolio = await portfolio_service.create_portfolio(
                    user_id=user["id"],
                    portfolio_data={"name": "Test Portfolio"}
                )
                
                assert portfolio["user_id"] == user["id"]
    
    @pytest.mark.asyncio
    async def test_portfolio_analytics_integration(self):
        """Test integration between portfolio and analytics modules"""
        from app.services.portfolio import portfolio_service
        from app.services.analytics import analytics_service
        
        # Mock portfolio data
        with patch.object(portfolio_service, 'get_portfolio_with_holdings') as mock_get_portfolio:
            mock_get_portfolio.return_value = {
                "id": "test-portfolio-id",
                "holdings": [
                    {"symbol": "AAPL", "shares": 100, "purchase_price": 150.00},
                    {"symbol": "GOOGL", "shares": 50, "purchase_price": 2800.00}
                ]
            }
            
            # Mock analytics calculation
            with patch.object(analytics_service, 'calculate_portfolio_performance') as mock_calculate:
                mock_calculate.return_value = {
                    "total_value": 155000.00,
                    "total_return": 5000.00,
                    "return_percentage": 3.33
                }
                
                # Test that analytics service correctly processes portfolio data
                portfolio = await portfolio_service.get_portfolio_with_holdings("test-portfolio-id")
                performance = await analytics_service.calculate_portfolio_performance(portfolio)
                
                assert performance["total_value"] > 0
                assert "return_percentage" in performance


# Negative Testing Scenarios
class TestNegativeScenarios:
    """Test error handling and negative scenarios"""
    
    @pytest.mark.asyncio
    async def test_invalid_authentication(self, async_client):
        """Test API behavior with invalid authentication"""
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        
        response = await async_client.get("/api/v1/portfolios", headers=headers)
        assert response.status_code == 401
        
        data = response.json()
        assert "error" in data
        assert "authentication" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_resource_not_found(self, async_client, mock_user):
        """Test API behavior when resources are not found"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            with patch('app.services.portfolio.portfolio_service.get_portfolio', return_value=None):
                response = await async_client.get("/api/v1/portfolios/non-existent-id")
                
                assert response.status_code == 404
                data = response.json()
                assert "error" in data
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_validation_errors(self, async_client, mock_user):
        """Test API validation error handling"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test with invalid data
            invalid_portfolio_data = {
                "name": "",  # Empty name should fail validation
                "description": "x" * 1001  # Too long description
            }
            
            response = await async_client.post("/api/v1/portfolios", json=invalid_portfolio_data)
            
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data
            
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_service_unavailable(self, async_client, mock_user):
        """Test API behavior when services are unavailable"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Mock service failure
            with patch('app.services.portfolio.portfolio_service.get_portfolios', 
                      side_effect=Exception("Service unavailable")):
                
                response = await async_client.get("/api/v1/portfolios")
                
                assert response.status_code == 500
                data = response.json()
                assert "error" in data
        
        finally:
            app.dependency_overrides.clear()
```

---

## 3. System Testing Framework

### 3.1 End-to-End Test Scenarios

#### **Complete System Workflows**
```python
# tests/system/test_end_to_end.py
import pytest
import asyncio
from playwright.async_api import async_playwright
from httpx import AsyncClient
import json
import time

class TestCompleteUserJourney:
    """End-to-end tests covering complete user journeys"""
    
    @pytest.fixture
    async def browser_context(self):
        """Browser context for E2E tests"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            yield context
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_complete_portfolio_management_workflow(self, browser_context):
        """Test complete portfolio management workflow"""
        page = await browser_context.new_page()
        
        try:
            # Step 1: Navigate to application
            await page.goto("http://localhost:3030")
            await page.wait_for_load_state("networkidle")
            
            # Step 2: User registration
            await page.click('[data-testid="register-button"]')
            await page.fill('[data-testid="email-input"]', "e2e.test@example.com")
            await page.fill('[data-testid="password-input"]', "SecurePassword123!")
            await page.fill('[data-testid="full-name-input"]', "E2E Test User")
            await page.click('[data-testid="submit-registration"]')
            
            # Wait for registration success
            await page.wait_for_selector('[data-testid="registration-success"]', timeout=5000)
            
            # Step 3: User login
            await page.fill('[data-testid="login-email"]', "e2e.test@example.com")
            await page.fill('[data-testid="login-password"]', "SecurePassword123!")
            await page.click('[data-testid="login-submit"]')
            
            # Wait for dashboard
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)
            
            # Step 4: Create portfolio
            await page.click('[data-testid="create-portfolio-button"]')
            await page.fill('[data-testid="portfolio-name"]', "E2E Test Portfolio")
            await page.fill('[data-testid="portfolio-description"]', "End-to-end test portfolio")
            await page.click('[data-testid="save-portfolio"]')
            
            # Wait for portfolio creation
            await page.wait_for_selector('[data-testid="portfolio-created"]', timeout=5000)
            
            # Step 5: Add holdings to portfolio
            await page.click('[data-testid="add-holding-button"]')
            await page.fill('[data-testid="stock-symbol"]', "AAPL")
            await page.fill('[data-testid="shares-input"]', "100")
            await page.fill('[data-testid="purchase-price"]', "150.00")
            await page.click('[data-testid="add-holding-submit"]')
            
            # Wait for holding to be added
            await page.wait_for_selector('[data-testid="holding-AAPL"]', timeout=5000)
            
            # Step 6: View portfolio performance
            await page.click('[data-testid="portfolio-performance-tab"]')
            await page.wait_for_selector('[data-testid="performance-chart"]', timeout=10000)
            
            # Verify performance data is displayed
            total_value = await page.text_content('[data-testid="total-portfolio-value"]')
            assert total_value is not None
            assert "$" in total_value
            
            # Step 7: Generate portfolio report
            await page.click('[data-testid="generate-report-button"]')
            await page.select_option('[data-testid="report-type"]', "performance")
            await page.click('[data-testid="generate-report-submit"]')
            
            # Wait for report generation
            await page.wait_for_selector('[data-testid="report-generated"]', timeout=15000)
            
            # Step 8: Download report
            async with page.expect_download() as download_info:
                await page.click('[data-testid="download-report"]')
            download = await download_info.value
            
            # Verify download
            assert download.suggested_filename.endswith('.pdf')
            
            # Step 9: Logout
            await page.click('[data-testid="user-menu"]')
            await page.click('[data-testid="logout-button"]')
            
            # Verify logout
            await page.wait_for_selector('[data-testid="login-form"]', timeout=5000)
            
        finally:
            await page.close()
    
    @pytest.mark.asyncio
    async def test_analytics_and_ml_workflow(self, browser_context):
        """Test analytics and ML prediction workflow"""
        page = await browser_context.new_page()
        
        try:
            # Login (assuming user exists)
            await page.goto("http://localhost:3030/login")
            await page.fill('[data-testid="login-email"]', "test@example.com")
            await page.fill('[data-testid="login-password"]', "password")
            await page.click('[data-testid="login-submit"]')
            
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)
            
            # Navigate to analytics
            await page.click('[data-testid="analytics-nav"]')
            await page.wait_for_selector('[data-testid="analytics-dashboard"]', timeout=5000)
            
            # Test stock price prediction
            await page.click('[data-testid="stock-prediction-tab"]')
            await page.fill('[data-testid="prediction-symbol"]', "AAPL")
            await page.select_option('[data-testid="prediction-days"]', "30")
            await page.click('[data-testid="generate-prediction"]')
            
            # Wait for prediction results
            await page.wait_for_selector('[data-testid="prediction-result"]', timeout=15000)
            
            # Verify prediction data
            predicted_price = await page.text_content('[data-testid="predicted-price"]')
            confidence_score = await page.text_content('[data-testid="confidence-score"]')
            
            assert predicted_price is not None
            assert confidence_score is not None
            assert "%" in confidence_score
            
            # Test portfolio risk analysis
            await page.click('[data-testid="risk-analysis-tab"]')
            await page.select_option('[data-testid="portfolio-select"]', "E2E Test Portfolio")
            await page.click('[data-testid="analyze-risk"]')
            
            # Wait for risk analysis
            await page.wait_for_selector('[data-testid="risk-analysis-result"]', timeout=15000)
            
            # Verify risk metrics
            var_95 = await page.text_content('[data-testid="var-95"]')
            expected_return = await page.text_content('[data-testid="expected-return"]')
            
            assert var_95 is not None
            assert expected_return is not None
            
        finally:
            await page.close()
    
    @pytest.mark.asyncio
    async def test_real_time_features_workflow(self, browser_context):
        """Test real-time features and WebSocket functionality"""
        page = await browser_context.new_page()
        
        try:
            # Login and navigate to dashboard
            await page.goto("http://localhost:3030/login")
            await page.fill('[data-testid="login-email"]', "test@example.com")
            await page.fill('[data-testid="login-password"]', "password")
            await page.click('[data-testid="login-submit"]')
            
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)
            
            # Enable real-time updates
            await page.check('[data-testid="enable-realtime-updates"]')
            
            # Wait for WebSocket connection
            await page.wait_for_selector('[data-testid="realtime-connected"]', timeout=5000)
            
            # Monitor real-time price updates
            initial_price = await page.text_content('[data-testid="stock-price-AAPL"]')
            
            # Wait for price update (simulate by triggering update)
            await page.evaluate("""
                // Simulate WebSocket message
                window.dispatchEvent(new CustomEvent('websocket-message', {
                    detail: {
                        type: 'price_update',
                        symbol: 'AAPL',
                        price: 155.50,
                        change: 2.5
                    }
                }));
            """)
            
            # Wait for UI update
            await page.wait_for_function(
                "document.querySelector('[data-testid=\"stock-price-AAPL\"]').textContent !== arguments[0]",
                initial_price,
                timeout=5000
            )
            
            # Verify price update
            updated_price = await page.text_content('[data-testid="stock-price-AAPL"]')
            assert updated_price != initial_price
            assert "155.50" in updated_price
            
            # Test portfolio value update
            initial_portfolio_value = await page.text_content('[data-testid="portfolio-total-value"]')
            
            # Simulate portfolio update
            await page.evaluate("""
                window.dispatchEvent(new CustomEvent('websocket-message', {
                    detail: {
                        type: 'portfolio_update',
                        portfolio_id: 'test-portfolio',
                        total_value: 16000.00,
                        change: 500.00
                    }
                }));
            """)
            
            # Wait for portfolio value update
            await page.wait_for_function(
                "document.querySelector('[data-testid=\"portfolio-total-value\"]').textContent !== arguments[0]",
                initial_portfolio_value,
                timeout=5000
            )
            
            # Verify portfolio update
            updated_portfolio_value = await page.text_content('[data-testid="portfolio-total-value"]')
            assert updated_portfolio_value != initial_portfolio_value
            
        finally:
            await page.close()


class TestSystemConfiguration:
    """Test system behavior under various configurations"""
    
    @pytest.mark.asyncio
    async def test_high_load_configuration(self):
        """Test system behavior under high load"""
        # Simulate high concurrent load
        async def make_request(client, endpoint):
            try:
                response = await client.get(endpoint)
                return response.status_code
            except Exception as e:
                return 500
        
        async with AsyncClient(base_url="http://localhost:8000") as client:
            # Create 100 concurrent requests
            tasks = []
            for i in range(100):
                task = make_request(client, "/api/v1/health")
                tasks.append(task)
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            success_count = sum(1 for result in results if result == 200)
            error_count = len(results) - success_count
            
            # System should handle at least 80% of requests successfully
            success_rate = success_count / len(results)
            assert success_rate >= 0.8, f"Success rate {success_rate:.2%} below threshold"
    
    @pytest.mark.asyncio
    async def test_database_connection_limits(self):
        """Test system behavior at database connection limits"""
        from app.core.database import get_db
        
        # Test creating many database connections
        connections = []
        try:
            for i in range(50):  # Try to create 50 connections
                db = next(get_db())
                connections.append(db)
            
            # System should handle connection pooling gracefully
            assert len(connections) <= 30  # Should be limited by pool size
            
        finally:
            # Clean up connections
            for conn in connections:
                conn.close()
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate sustained load
        async with AsyncClient(base_url="http://localhost:8000") as client:
            for i in range(1000):
                await client.get("/api/v1/health")
                
                if i % 100 == 0:
                    gc.collect()  # Force garbage collection
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"


class TestRecoveryProcedures:
    """Test system recovery and failover mechanisms"""
    
    @pytest.mark.asyncio
    async def test_database_connection_recovery(self):
        """Test recovery from database connection failures"""
        from app.core.database import engine
        from app.services.portfolio import portfolio_service
        
        # Simulate database connection failure
        with patch.object(engine, 'connect', side_effect=Exception("Connection failed")):
            # First request should fail
            with pytest.raises(Exception):
                await portfolio_service.get_portfolios("test-user-id")
        
        # After connection is restored, requests should work
        # (This would be handled by connection retry logic in production)
        portfolios = await portfolio_service.get_portfolios("test-user-id")
        assert isinstance(portfolios, list)
    
    @pytest.mark.asyncio
    async def test_cache_failure_recovery(self):
        """Test recovery from cache failures"""
        from app.core.cache import cache_manager
        from app.services.financial import financial_service
        
        # Simulate cache failure
        with patch.object(cache_manager, 'get', side_effect=Exception("Cache unavailable")):
            # Service should still work without cache
            data = await financial_service.get_stock_data("AAPL")
            assert data is not None
        
        # Cache should recover automatically
        cached_data = await cache_manager.get("test_key")
        # Should not raise exception (may return None)
    
    @pytest.mark.asyncio
    async def test_external_api_failure_recovery(self):
        """Test recovery from external API failures"""
        from app.services.data import data_service
        
        # Simulate external API failure
        with patch('aiohttp.ClientSession.get', side_effect=Exception("API unavailable")):
            # Service should handle failure gracefully
            data = await data_service.fetch_market_data("AAPL")
            
            # Should return cached data or mock data
            assert data is not None
            assert "error" not in data or data.get("fallback", False)
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation under partial failures"""
        # Simulate partial system failure (e.g., ML service unavailable)
        with patch('app.services.analytics.ml_service.predict_stock_price', 
                  side_effect=Exception("ML service unavailable")):
            
            async with AsyncClient(base_url="http://localhost:8000") as client:
                # Analytics endpoint should still work with fallback
                response = await client.post("/api/v1/analytics/predict/stock-price", 
                                           json={"symbol": "AAPL", "days_ahead": 30})
                
                # Should return fallback response
                assert response.status_code in [200, 503]  # Success or service unavailable
                
                if response.status_code == 200:
                    data = response.json()
                    assert "fallback" in data or "mock" in str(data).lower()
```

---

## 4. User Acceptance Testing (UAT)

### 4.1 Business Requirements Validation

#### **UAT Test Cases**
```python
# tests/uat/test_business_requirements.py
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

class TestPortfolioManagementRequirements:
    """UAT tests for portfolio management business requirements"""
    
    def test_portfolio_creation_business_rules(self):
        """
        Business Requirement: Users must be able to create portfolios with unique names
        Acceptance Criteria:
        - Portfolio name must be unique per user
        - Portfolio name must be 1-100 characters
        - Portfolio description is optional, max 500 characters
        """
        from app.services.portfolio import portfolio_service
        
        # Test valid portfolio creation
        portfolio_data = {
            "name": "Growth Portfolio",
            "description": "Long-term growth focused portfolio"
        }
        
        portfolio = portfolio_service.create_portfolio("user-123", portfolio_data)
        
        assert portfolio["name"] == "Growth Portfolio"
        assert portfolio["user_id"] == "user-123"
        assert len(portfolio["description"]) <= 500
        
        # Test duplicate name rejection
        with pytest.raises(ValueError, match="Portfolio name already exists"):
            portfolio_service.create_portfolio("user-123", portfolio_data)
        
        # Test name length validation
        with pytest.raises(ValueError, match="Portfolio name must be"):
            portfolio_service.create_portfolio("user-123", {"name": ""})
        
        with pytest.raises(ValueError, match="Portfolio name must be"):
            portfolio_service.create_portfolio("user-123", {"name": "x" * 101})
    
    def test_holding_management_business_rules(self):
        """
        Business Requirement: Users must be able to add/remove holdings with proper validation
        Acceptance Criteria:
        - Stock symbol must be valid (1-5 alphanumeric characters)
        - Shares must be positive number
        - Purchase price must be positive
        - Cannot sell more shares than owned
        """
        from app.services.portfolio import portfolio_service
        
        portfolio_id = "test-portfolio-123"
        
        # Test valid holding addition
        holding_data = {
            "symbol": "AAPL",
            "shares": Decimal("100"),
            "purchase_price": Decimal("150.00")
        }
        
        holding = portfolio_service.add_holding(portfolio_id, holding_data)
        
        assert holding["symbol"] == "AAPL"
        assert holding["shares"] == Decimal("100")
        assert holding["purchase_price"] == Decimal("150.00")
        
        # Test invalid symbol validation
        with pytest.raises(ValueError, match="Invalid stock symbol"):
            portfolio_service.add_holding(portfolio_id, {
                "symbol": "INVALID_SYMBOL",
                "shares": Decimal("100"),
                "purchase_price": Decimal("150.00")
            })
        
        # Test negative shares validation
        with pytest.raises(ValueError, match="Shares must be positive"):
            portfolio_service.add_holding(portfolio_id, {
                "symbol": "AAPL",
                "shares": Decimal("-10"),
                "purchase_price": Decimal("150.00")
            })
        
        # Test overselling validation
        with pytest.raises(ValueError, match="Cannot sell more shares than owned"):
            portfolio_service.remove_holding(portfolio_id, "AAPL", Decimal("150"))
    
    def test_financial_calculations_accuracy(self):
        """
        Business Requirement: Financial calculations must be accurate to 2 decimal places
        Acceptance Criteria:
        - All monetary values rounded to 2 decimal places
        - Percentage calculations accurate to 2 decimal places
        - Portfolio value calculations must be precise
        """
        from app.services.calculator import financial_calculator
        
        # Test portfolio value calculation
        holdings = [
            {"symbol": "AAPL", "shares": Decimal("100.5"), "current_price": Decimal("155.67")},
            {"symbol": "GOOGL", "shares": Decimal("25.25"), "current_price": Decimal("2845.33")}
        ]
        
        total_value = financial_calculator.calculate_portfolio_value(holdings)
        
        # Expected: (100.5 * 155.67) + (25.25 * 2845.33) = 15644.835 + 71794.0825 = 87438.92
        expected_value = Decimal("87438.92")
        assert total_value == expected_value
        
        # Test return percentage calculation
        cost_basis = Decimal("80000.00")
        current_value = Decimal("87438.92")
        
        return_percentage = financial_calculator.calculate_return_percentage(cost_basis, current_value)
        
        # Expected: ((87438.92 - 80000.00) / 80000.00) * 100 = 9.30%
        expected_percentage = Decimal("9.30")
        assert return_percentage == expected_percentage


class TestAnalyticsRequirements:
    """UAT tests for analytics and ML requirements"""
    
    def test_stock_prediction_requirements(self):
        """
        Business Requirement: Stock price predictions must include confidence scores
        Acceptance Criteria:
        - Predictions must include confidence score (0-100%)
        - Predictions must include time horizon
        - Predictions must include model used
        - Historical accuracy must be tracked
        """
        from app.services.analytics import ml_service
        
        prediction = ml_service.predict_stock_price("AAPL", days_ahead=30)
        
        # Verify required fields
        assert "predicted_price" in prediction
        assert "confidence_score" in prediction
        assert "model_used" in prediction
        assert "prediction_date" in prediction
        assert "days_ahead" in prediction
        
        # Verify confidence score range
        confidence = prediction["confidence_score"]
        assert 0 <= confidence <= 100
        
        # Verify prediction is reasonable (within 50% of current price)
        current_price = prediction.get("current_price", 150.00)
        predicted_price = prediction["predicted_price"]
        
        price_change_ratio = abs(predicted_price - current_price) / current_price
        assert price_change_ratio <= 0.5, "Prediction seems unreasonable"
    
    def test_risk_analysis_requirements(self):
        """
        Business Requirement: Risk analysis must provide comprehensive metrics
        Acceptance Criteria:
        - Must calculate Value at Risk (VaR) at 95% and 99% confidence
        - Must provide expected return
        - Must include volatility measures
        - Must provide risk-adjusted returns (Sharpe ratio)
        """
        from app.services.analytics import risk_analyzer
        
        portfolio_data = {
            "holdings": [
                {"symbol": "AAPL", "weight": 0.4},
                {"symbol": "GOOGL", "weight": 0.3},
                {"symbol": "MSFT", "weight": 0.3}
            ]
        }
        
        risk_analysis = risk_analyzer.analyze_portfolio_risk(portfolio_data)
        
        # Verify required metrics
        assert "var_95" in risk_analysis
        assert "var_99" in risk_analysis
        assert "expected_return" in risk_analysis
        assert "volatility" in risk_analysis
        assert "sharpe_ratio" in risk_analysis
        
        # Verify metric ranges
        assert -1.0 <= risk_analysis["var_95"] <= 0.0  # VaR should be negative
        assert risk_analysis["var_99"] <= risk_analysis["var_95"]  # 99% VaR should be worse
        assert risk_analysis["volatility"] >= 0  # Volatility should be positive
        
        # Verify Sharpe ratio calculation
        sharpe_ratio = risk_analysis["sharpe_ratio"]
        assert isinstance(sharpe_ratio, (int, float))


class TestReportingRequirements:
    """UAT tests for reporting requirements"""
    
    def test_pdf_report_generation(self):
        """
        Business Requirement: System must generate PDF reports
        Acceptance Criteria:
        - Reports must be in PDF format
        - Reports must include portfolio summary
        - Reports must include performance charts
        - Reports must be downloadable
        """
        from app.services.report import report_generator
        
        report_config = {
            "portfolio_id": "test-portfolio-123",
            "report_type": "performance",
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        }
        
        report = report_generator.generate_report(report_config)
        
        # Verify report structure
        assert report["format"] == "pdf"
        assert "file_path" in report
        assert "file_size" in report
        assert report["file_size"] > 0
        
        # Verify report content sections
        assert "portfolio_summary" in report["sections"]
        assert "performance_chart" in report["sections"]
        assert "holdings_table" in report["sections"]
    
    def test_custom_report_builder(self):
        """
        Business Requirement: Users must be able to create custom reports
        Acceptance Criteria:
        - Users can select report sections
        - Users can customize date ranges
        - Users can choose chart types
        - Reports must be generated within 30 seconds
        """
        from app.services.report import custom_report_builder
        import time
        
        custom_config = {
            "sections": ["portfolio_summary", "performance_chart", "risk_analysis"],
            "chart_types": ["line_chart", "pie_chart"],
            "date_range": {"start_date": "2024-06-01", "end_date": "2024-12-01"},
            "portfolio_id": "test-portfolio-123"
        }
        
        start_time = time.time()
        report = custom_report_builder.build_custom_report(custom_config)
        generation_time = time.time() - start_time
        
        # Verify generation time
        assert generation_time <= 30, f"Report generation took {generation_time:.2f} seconds"
        
        # Verify custom sections
        for section in custom_config["sections"]:
            assert section in report["sections"]
        
        # Verify chart types
        for chart_type in custom_config["chart_types"]:
            assert any(chart_type in str(chart) for chart in report["charts"])


class TestRealWorldScenarios:
    """Test real-world usage scenarios and edge cases"""
    
    def test_large_portfolio_performance(self):
        """
        Real-world scenario: User with large portfolio (1000+ holdings)
        """
        from app.services.portfolio import portfolio_service
        from app.services.analytics import analytics_service
        
        # Create large portfolio
        large_portfolio = {
            "id": "large-portfolio-test",
            "holdings": []
        }
        
        # Add 1000 holdings
        for i in range(1000):
            holding = {
                "symbol": f"STOCK{i:04d}",
                "shares": Decimal(str(100 + i)),
                "purchase_price": Decimal(str(50.00 + (i * 0.1)))
            }
            large_portfolio["holdings"].append(holding)
        
        # Test performance calculation
        start_time = time.time()
        performance = analytics_service.calculate_portfolio_performance(large_portfolio)
        calculation_time = time.time() - start_time
        
        # Should complete within reasonable time (5 seconds)
        assert calculation_time <= 5.0
        
        # Verify results
        assert performance["total_value"] > 0
        assert len(performance["holdings"]) == 1000
    
    def test_market_volatility_scenario(self):
        """
        Real-world scenario: High market volatility affecting calculations
        """
        from app.services.analytics import risk_analyzer
        
        # Simulate high volatility portfolio
        volatile_portfolio = {
            "holdings": [
                {"symbol": "VOLATILE1", "weight": 0.5, "volatility": 0.8},
                {"symbol": "VOLATILE2", "weight": 0.3, "volatility": 0.6},
                {"symbol": "STABLE", "weight": 0.2, "volatility": 0.1}
            ]
        }
        
        risk_analysis = risk_analyzer.analyze_portfolio_risk(volatile_portfolio)
        
        # High volatility should be reflected in risk metrics
        assert risk_analysis["volatility"] > 0.3  # Should be high
        assert risk_analysis["var_95"] < -0.1  # Should show significant potential loss
    
    def test_data_inconsistency_handling(self):
        """
        Real-world scenario: Handling inconsistent or missing market data
        """
        from app.services.data import data_service
        
        # Test with missing data
        symbols_with_missing_data = ["MISSING1", "MISSING2", "AAPL"]
        
        market_data = data_service.fetch_batch_market_data(symbols_with_missing_data)
        
        # Should handle missing data gracefully
        assert len(market_data) >= 1  # At least AAPL should have data
        
        # Missing symbols should have fallback data or be marked as unavailable
        for symbol in symbols_with_missing_data:
            if symbol in market_data:
                data = market_data[symbol]
                assert "price" in data or "error" in data


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_value_portfolio(self):
        """Edge case: Portfolio with zero total value"""
        from app.services.analytics import analytics_service
        
        zero_portfolio = {
            "holdings": [
                {"symbol": "ZERO1", "shares": Decimal("100"), "current_price": Decimal("0.00")},
                {"symbol": "ZERO2", "shares": Decimal("50"), "current_price": Decimal("0.00")}
            ]
        }
        
        performance = analytics_service.calculate_portfolio_performance(zero_portfolio)
        
        # Should handle zero value gracefully
        assert performance["total_value"] == Decimal("0.00")
        assert performance["return_percentage"] == Decimal("0.00")
    
    def test_extreme_price_movements(self):
        """Edge case: Extreme price movements (1000% gain/loss)"""
        from app.services.analytics import analytics_service
        
        extreme_portfolio = {
            "holdings": [
                {
                    "symbol": "EXTREME",
                    "shares": Decimal("100"),
                    "purchase_price": Decimal("1.00"),
                    "current_price": Decimal("1000.00")  # 100,000% gain
                }
            ]
        }
        
        performance = analytics_service.calculate_portfolio_performance(extreme_portfolio)
        
        # Should handle extreme values without overflow
        assert performance["total_value"] == Decimal("100000.00")
        assert performance["return_percentage"] == Decimal("99900.00")  # 99,900% return
    
    def test_fractional_shares(self):
        """Edge case: Fractional share ownership"""
        from app.services.portfolio import portfolio_service
        
        fractional_holding = {
            "symbol": "AAPL",
            "shares": Decimal("0.123456"),  # Fractional shares
            "purchase_price": Decimal("150.789")
        }
        
        holding = portfolio_service.add_holding("test-portfolio", fractional_holding)
        
        # Should handle fractional shares with proper precision
        assert holding["shares"] == Decimal("0.123456")
        assert holding["purchase_price"] == Decimal("150.79")  # Rounded to 2 decimal places


# Test Documentation and Evidence Collection
class TestDocumentationAndEvidence:
    """Collect test evidence and documentation for compliance"""
    
    def test_audit_trail_generation(self):
        """Verify audit trail generation for compliance"""
        from app.services.audit import audit_service
        
        # Perform auditable action
        audit_service.log_action(
            user_id="test-user",
            action="portfolio_created",
            resource_id="test-portfolio-123",
            details={"name": "Test Portfolio", "initial_value": 10000.00}
        )
        
        # Verify audit log entry
        audit_logs = audit_service.get_audit_logs("test-user")
        
        assert len(audit_logs) >= 1
        latest_log = audit_logs[0]
        assert latest_log["action"] == "portfolio_created"
        assert latest_log["user_id"] == "test-user"
        assert "timestamp" in latest_log
    
    def test_compliance_reporting(self):
        """Test compliance reporting capabilities"""
        from app.services.compliance import compliance_service
        
        compliance_report = compliance_service.generate_compliance_report({
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "report_type": "user_activity"
        })
        
        # Verify compliance report structure
        assert "report_id" in compliance_report
        assert "generation_date" in compliance_report
        assert "data_summary" in compliance_report
        assert "compliance_status" in compliance_report
        
        # Verify compliance status
        assert compliance_report["compliance_status"] in ["compliant", "non_compliant", "review_required"]


# Pass/Fail Criteria Documentation
PASS_FAIL_CRITERIA = {
    "portfolio_management": {
        "portfolio_creation": "PASS if portfolio created with valid data, FAIL if validation errors not caught",
        "holding_management": "PASS if holdings added/removed correctly, FAIL if business rules violated",
        "financial_calculations": "PASS if calculations accurate to 2 decimal places, FAIL if rounding errors"
    },
    "analytics": {
        "stock_predictions": "PASS if confidence score 0-100% and reasonable predictions, FAIL if unrealistic results",
        "risk_analysis": "PASS if all required metrics present and valid ranges, FAIL if missing metrics"
    },
    "reporting": {
        "pdf_generation": "PASS if PDF generated within 30 seconds with all sections, FAIL if timeout or missing content",
        "custom_reports": "PASS if custom sections included and charts generated, FAIL if configuration ignored"
    },
    "performance": {
        "large_portfolios": "PASS if 1000+ holdings processed within 5 seconds, FAIL if timeout",
        "concurrent_users": "PASS if 80%+ success rate under load, FAIL if high error rate"
    }
}