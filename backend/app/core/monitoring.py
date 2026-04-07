"""
Performance monitoring and metrics collection for the Financial Analysis Platform
"""
import time
import psutil
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading

from app.core.logging import get_logger
from app.core.cache import cache_manager

monitor_logger = get_logger("app.monitoring")


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    response_times: List[float] = field(default_factory=list)
    error_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0


class MetricsCollector:
    """Centralized metrics collection system"""

    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        with self._lock:
            key = self._build_key(name, tags)
            self.counters[key] += value
            self._add_metric_point(name, value, tags)

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        with self._lock:
            key = self._build_key(name, tags)
            self.gauges[key] = value
            self._add_metric_point(name, value, tags)

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        with self._lock:
            key = self._build_key(name, tags)
            self.histograms[key].append(value)
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            self._add_metric_point(name, value, tags)

    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        with self._lock:
            key = self._build_key(name, tags)
            self.timers[key].append(duration)
            if len(self.timers[key]) > 1000:
                self.timers[key] = self.timers[key][-1000:]
            self._add_metric_point(name, duration, tags)

    def _build_key(self, name: str, tags: Dict[str, str] = None) -> str:
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"

    def _add_metric_point(self, name: str, value: float, tags: Dict[str, str] = None):
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            tags=tags or {}
        )
        self.metrics[name].append(point)

    def get_counter(self, name: str, tags: Dict[str, str] = None) -> int:
        key = self._build_key(name, tags)
        return self.counters.get(key, 0)

    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> float:
        key = self._build_key(name, tags)
        return self.gauges.get(key, 0.0)

    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        key = self._build_key(name, tags)
        values = self.histograms.get(key, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_values = sorted(values)
        count = len(sorted_values)
        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "p50": self._percentile(sorted_values, 50),
            "p95": self._percentile(sorted_values, 95),
            "p99": self._percentile(sorted_values, 99)
        }

    def get_timer_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        return self.get_histogram_stats(name, tags)

    def _percentile(self, values: List[float], percentile: int) -> float:
        if not values:
            return 0.0
        index = int((percentile / 100.0) * len(values))
        if index >= len(values):
            index = len(values) - 1
        return values[index]

    def get_all_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {k: self.get_histogram_stats(k.split('[')[0], self._parse_tags(k)) for k in self.histograms.keys()},
                "timers": {k: self.get_timer_stats(k.split('[')[0], self._parse_tags(k)) for k in self.timers.keys()}
            }

    def _parse_tags(self, key: str) -> Dict[str, str]:
        if '[' not in key:
            return {}
        tag_part = key.split('[')[1].rstrip(']')
        tags = {}
        for tag in tag_part.split(','):
            if '=' in tag:
                k, v = tag.split('=', 1)
                tags[k] = v
        return tags

    def reset_metrics(self):
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self.metrics.clear()


# Global metrics collector
metrics = MetricsCollector()


class PerformanceMonitor:
    """Performance monitoring utilities"""

    def __init__(self):
        self.system_metrics_task: Optional[asyncio.Task] = None
        self._monitoring = False

    async def start_monitoring(self, interval: int = 60):
        if self._monitoring:
            return
        self._monitoring = True
        self.system_metrics_task = asyncio.create_task(
            self._collect_system_metrics(interval)
        )
        monitor_logger.logger.info("Performance monitoring started")

    async def stop_monitoring(self):
        self._monitoring = False
        if self.system_metrics_task:
            self.system_metrics_task.cancel()
            try:
                await self.system_metrics_task
            except asyncio.CancelledError:
                pass
        monitor_logger.logger.info("Performance monitoring stopped")

    async def _collect_system_metrics(self, interval: int):
        """Collect system metrics periodically"""
        while self._monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                metrics.set_gauge("system.cpu.usage", cpu_percent)
                memory = psutil.virtual_memory()
                metrics.set_gauge("system.memory.usage", memory.percent)
                metrics.set_gauge("system.memory.available", memory.available)
                metrics.set_gauge("system.memory.used", memory.used)
                disk = psutil.disk_usage('/')
                metrics.set_gauge("system.disk.usage", disk.percent)
                metrics.set_gauge("system.disk.free", disk.free)
                network = psutil.net_io_counters()
                metrics.set_gauge("system.network.bytes_sent", network.bytes_sent)
                metrics.set_gauge("system.network.bytes_recv", network.bytes_recv)
                process = psutil.Process()
                metrics.set_gauge("process.memory.rss", process.memory_info().rss)
                metrics.set_gauge("process.memory.vms", process.memory_info().vms)
                metrics.set_gauge("process.cpu.percent", process.cpu_percent())
                metrics.set_gauge("process.threads", process.num_threads())
                if cache_manager._connected:
                    cache_stats = await cache_manager.get_stats()
                    if cache_stats.get("connected"):
                        metrics.set_gauge("cache.hit_rate", cache_stats.get("hit_rate", 0))
                        metrics.set_gauge("cache.connected_clients", cache_stats.get("connected_clients", 0))
                await asyncio.sleep(interval)
            except Exception as e:
                monitor_logger.logger.error(f"Error collecting system metrics: {str(e)}")
                await asyncio.sleep(interval)

    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect and return current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            process = psutil.Process()
            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available": memory.available,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_usage_percent": disk.percent,
                "disk_free": disk.free,
                "disk_total": disk.total,
                "network_io": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                },
                "process": {
                    "memory_rss": process.memory_info().rss,
                    "memory_vms": process.memory_info().vms,
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads(),
                }
            }
        except Exception as e:
            monitor_logger.logger.error(f"Error collecting system metrics: {str(e)}")
            return {}

    def get_performance_summary(self) -> Dict[str, Any]:
        return {
            "system": {
                "cpu_usage": metrics.get_gauge("system.cpu.usage"),
                "memory_usage": metrics.get_gauge("system.memory.usage"),
                "disk_usage": metrics.get_gauge("system.disk.usage"),
            },
            "application": {
                "requests_total": metrics.get_counter("http.requests.total"),
                "requests_errors": metrics.get_counter("http.requests.errors"),
                "response_time": metrics.get_timer_stats("http.request.duration"),
                "database_queries": metrics.get_counter("database.queries.total"),
                "cache_hits": metrics.get_counter("cache.hits"),
                "cache_misses": metrics.get_counter("cache.misses"),
            }
        }


# Global instances
metrics_collector = metrics
performance_monitor = PerformanceMonitor()
alert_manager = None  # Initialized below


def monitor_performance(
    metric_name: str = None,
    tags: Dict[str, str] = None,
    record_errors: bool = True
):
    """Decorator to monitor function performance"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            try:
                metrics.increment_counter(f"{name}.calls", tags=tags)
                result = await func(*args, **kwargs)
                metrics.increment_counter(f"{name}.success", tags=tags)
                return result
            except Exception as e:
                if record_errors:
                    error_tags = {**(tags or {}), "error_type": type(e).__name__}
                    metrics.increment_counter(f"{name}.errors", tags=error_tags)
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                metrics.record_timer(f"{name}.duration", duration, tags=tags)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            try:
                metrics.increment_counter(f"{name}.calls", tags=tags)
                result = func(*args, **kwargs)
                metrics.increment_counter(f"{name}.success", tags=tags)
                return result
            except Exception as e:
                if record_errors:
                    error_tags = {**(tags or {}), "error_type": type(e).__name__}
                    metrics.increment_counter(f"{name}.errors", tags=error_tags)
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                metrics.record_timer(f"{name}.duration", duration, tags=tags)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class AlertManager:
    """Alert management for performance thresholds"""

    def __init__(self):
        self.thresholds = {
            "response_time_p95": 1000,
            "error_rate": 5.0,
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
        }
        self.alert_cooldown = 300
        self.last_alerts = {}

    def check_thresholds(self) -> List[Dict[str, Any]]:
        alerts = []
        current_time = datetime.now(timezone.utc)
        response_stats = metrics.get_timer_stats("http.request.duration")
        if response_stats["p95"] > self.thresholds["response_time_p95"]:
            alert = self._create_alert(
                "high_response_time",
                f"95th percentile response time is {response_stats['p95']:.2f}ms",
                "warning",
                {"value": response_stats["p95"], "threshold": self.thresholds["response_time_p95"]}
            )
            if self._should_send_alert("high_response_time", current_time):
                alerts.append(alert)
        total_requests = metrics.get_counter("http.requests.total")
        error_requests = metrics.get_counter("http.requests.errors")
        if total_requests > 0:
            error_rate = (error_requests / total_requests) * 100
            if error_rate > self.thresholds["error_rate"]:
                alert = self._create_alert(
                    "high_error_rate",
                    f"Error rate is {error_rate:.2f}%",
                    "critical",
                    {"value": error_rate, "threshold": self.thresholds["error_rate"]}
                )
                if self._should_send_alert("high_error_rate", current_time):
                    alerts.append(alert)
        cpu_usage = metrics.get_gauge("system.cpu.usage")
        if cpu_usage > self.thresholds["cpu_usage"]:
            alert = self._create_alert(
                "high_cpu_usage",
                f"CPU usage is {cpu_usage:.1f}%",
                "warning",
                {"value": cpu_usage, "threshold": self.thresholds["cpu_usage"]}
            )
            if self._should_send_alert("high_cpu_usage", current_time):
                alerts.append(alert)
        memory_usage = metrics.get_gauge("system.memory.usage")
        if memory_usage > self.thresholds["memory_usage"]:
            alert = self._create_alert(
                "high_memory_usage",
                f"Memory usage is {memory_usage:.1f}%",
                "warning",
                {"value": memory_usage, "threshold": self.thresholds["memory_usage"]}
            )
            if self._should_send_alert("high_memory_usage", current_time):
                alerts.append(alert)
        return alerts

    def _create_alert(self, alert_type: str, message: str, severity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

    def _should_send_alert(self, alert_type: str, current_time: datetime) -> bool:
        last_alert_time = self.last_alerts.get(alert_type)
        if not last_alert_time:
            self.last_alerts[alert_type] = current_time
            return True
        if (current_time - last_alert_time).total_seconds() > self.alert_cooldown:
            self.last_alerts[alert_type] = current_time
            return True
        return False


# Initialize alert_manager after class definition
alert_manager = AlertManager()

# Convenience functions
async def start_monitoring():
    await performance_monitor.start_monitoring()


async def stop_monitoring():
    await performance_monitor.stop_monitoring()


def get_metrics_summary() -> Dict[str, Any]:
    return {
        "performance": performance_monitor.get_performance_summary(),
        "alerts": alert_manager.check_thresholds(),
        "metrics": metrics.get_all_metrics()
    }
