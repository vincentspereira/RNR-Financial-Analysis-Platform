"""
Monitoring and metrics endpoints
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.monitoring import metrics_collector, performance_monitor, alert_manager
from app.core.error_tracking import error_tracker
from app.core.database_performance import db_performance_monitor, db_health_checker
from app.core.cache import cache_manager
from app.core.logging import get_logger

router = APIRouter()
monitoring_logger = get_logger("monitoring.api")


@router.get("/metrics")
async def get_metrics():
    """Get comprehensive system metrics"""
    try:
        # Collect all metrics
        system_metrics = await performance_monitor.collect_system_metrics()
        app_metrics = metrics_collector.get_all_metrics()
        db_metrics = await db_performance_monitor.get_query_statistics()
        cache_metrics = await cache_manager.get_stats()
        error_stats = error_tracker.get_error_statistics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_metrics,
            "application": app_metrics,
            "database": db_metrics,
            "cache": cache_metrics,
            "errors": error_stats
        }
        
    except Exception as e:
        monitoring_logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/metrics/summary")
async def get_metrics_summary():
    """Get summarized metrics for dashboard"""
    try:
        summary = await performance_monitor.get_metrics_summary()
        
        # Add error rate
        error_stats = error_tracker.get_error_statistics()
        summary["error_rate"] = error_stats["error_rate"]
        summary["total_errors"] = error_stats["total_errors"]
        
        # Add cache hit rate
        cache_stats = await cache_manager.get_stats()
        if cache_stats.get("total_requests", 0) > 0:
            summary["cache_hit_rate"] = (
                cache_stats.get("hits", 0) / cache_stats.get("total_requests", 1) * 100
            )
        else:
            summary["cache_hit_rate"] = 0
        
        return summary
        
    except Exception as e:
        monitoring_logger.error(f"Failed to get metrics summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics summary")


@router.get("/performance")
async def get_performance_metrics():
    """Get detailed performance metrics"""
    try:
        # System performance
        system_metrics = await performance_monitor.collect_system_metrics()
        
        # Database performance
        db_stats = await db_performance_monitor.get_query_statistics()
        db_pool_stats = await db_performance_monitor.get_connection_pool_stats()
        
        # Application performance
        app_metrics = metrics_collector.get_metrics_by_type("histogram")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_performance": {
                "cpu_usage": system_metrics.get("cpu_usage_percent", 0),
                "memory_usage": system_metrics.get("memory_usage_percent", 0),
                "disk_usage": system_metrics.get("disk_usage_percent", 0),
                "network_io": system_metrics.get("network_io", {}),
                "process_metrics": system_metrics.get("process_metrics", {})
            },
            "database_performance": {
                "query_statistics": db_stats,
                "connection_pool": db_pool_stats,
                "slow_queries": db_stats.get("top_slow_queries", [])[:5]
            },
            "application_performance": {
                "response_times": app_metrics.get("http_request_duration", {}),
                "database_query_times": app_metrics.get("database_query_duration", {}),
                "cache_operations": app_metrics.get("cache_operation_duration", {})
            }
        }
        
    except Exception as e:
        monitoring_logger.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@router.get("/errors")
async def get_error_metrics():
    """Get error tracking metrics"""
    try:
        error_stats = error_tracker.get_error_statistics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error_summary": {
                "total_errors": error_stats["total_errors"],
                "error_rate": error_stats["error_rate"],
                "severity_distribution": error_stats["severity_distribution"],
                "category_distribution": error_stats["category_distribution"]
            },
            "top_errors": error_stats["top_errors"],
            "recent_errors": error_stats["recent_errors"]
        }
        
    except Exception as e:
        monitoring_logger.error(f"Failed to get error metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error metrics")


@router.get("/errors/{error_id}")
async def get_error_details(error_id: str):
    """Get detailed information about a specific error"""
    try:
        error_report = error_tracker.get_error_by_id(error_id)
        
        if not error_report:
            raise HTTPException(status_code=404, detail="Error not found")
        
        return {
            "error_details": error_report.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        monitoring_logger.error(f"Failed to get error details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error details")


@router.get("/alerts")
async def get_active_alerts():
    """Get active performance alerts"""
    try:
        alerts = await alert_manager.get_active_alerts()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_alerts": alerts,
            "alert_summary": {
                "total_alerts": len(alerts),
                "critical_alerts": len([a for a in alerts if a.get("severity") == "critical"]),
                "warning_alerts": len([a for a in alerts if a.get("severity") == "warning"])
            }
        }
        
    except Exception as e:
        monitoring_logger.error(f"Failed to get alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/health/detailed")
async def get_detailed_health():
    """Get comprehensive health status"""
    try:
        # Database health
        db_health = await db_health_checker.check_database_health()
        
        # Cache health
        cache_health = await _check_cache_health()
        
        # System health
        system_metrics = await performance_monitor.collect_system_metrics()
        system_health = _assess_system_health(system_metrics)
        
        # Application health
        error_stats = error_tracker.get_error_statistics()
        app_health = _assess_application_health(error_stats)
        
        # Overall health
        health_components = [db_health["status"], cache_health["status"], 
                           system_health["status"], app_health["status"]]
        
        if "unhealthy" in health_components:
            overall_status = "unhealthy"
        elif "degraded" in health_components:
            overall_status = "degraded"
        elif "warning" in health_components:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "components": {
                "database": db_health,
                "cache": cache_health,
                "system": system_health,
                "application": app_health
            }
        }
        
    except Exception as e:
        monitoring_logger.error(f"Failed to get detailed health: {str(e)}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "unhealthy",
            "error": "Health check failed",
            "components": {}
        }


@router.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        # Get all necessary data for dashboard
        metrics_summary = await performance_monitor.get_metrics_summary()
        error_stats = error_tracker.get_error_statistics()
        db_health = await db_health_checker.check_database_health()
        cache_stats = await cache_manager.get_stats()
        alerts = await alert_manager.get_active_alerts()
        
        # Calculate additional metrics
        cache_hit_rate = 0
        if cache_stats.get("total_requests", 0) > 0:
            cache_hit_rate = (
                cache_stats.get("hits", 0) / cache_stats.get("total_requests", 1) * 100
            )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": {
                "status": db_health["status"],
                "uptime": metrics_summary.get("uptime_seconds", 0),
                "total_requests": metrics_summary.get("total_requests", 0),
                "error_rate": error_stats["error_rate"],
                "cache_hit_rate": cache_hit_rate,
                "active_alerts": len(alerts)
            },
            "performance": {
                "avg_response_time": metrics_summary.get("avg_response_time", 0),
                "requests_per_second": metrics_summary.get("requests_per_second", 0),
                "cpu_usage": metrics_summary.get("cpu_usage_percent", 0),
                "memory_usage": metrics_summary.get("memory_usage_percent", 0)
            },
            "errors": {
                "total_errors": error_stats["total_errors"],
                "recent_errors": error_stats["recent_errors"][:5],
                "top_errors": error_stats["top_errors"][:5]
            },
            "database": {
                "status": db_health["status"],
                "connection_pool": db_health.get("checks", {}).get("connection_pool", {}),
                "slow_queries": db_health.get("performance_metrics", {}).get("query_statistics", {}).get("top_slow_queries", [])[:3]
            },
            "alerts": alerts[:10]  # Latest 10 alerts
        }
        
    except Exception as e:
        monitoring_logger.error(f"Failed to get dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


async def _check_cache_health() -> Dict[str, Any]:
    """Check cache health status"""
    try:
        stats = await cache_manager.get_stats()
        
        # Test cache connectivity
        test_key = "health_check_test"
        await cache_manager.set(test_key, "test_value", expire=10)
        test_value = await cache_manager.get(test_key)
        await cache_manager.delete(test_key)
        
        if test_value == "test_value":
            status = "healthy"
            message = "Cache is operational"
        else:
            status = "warning"
            message = "Cache connectivity issues"
        
        return {
            "status": status,
            "message": message,
            "stats": stats
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Cache health check failed: {str(e)}",
            "stats": {}
        }


def _assess_system_health(system_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Assess system health based on metrics"""
    cpu_usage = system_metrics.get("cpu_usage_percent", 0)
    memory_usage = system_metrics.get("memory_usage_percent", 0)
    disk_usage = system_metrics.get("disk_usage_percent", 0)
    
    issues = []
    
    if cpu_usage > 90:
        status = "critical"
        issues.append(f"High CPU usage: {cpu_usage:.1f}%")
    elif cpu_usage > 80:
        status = "warning"
        issues.append(f"Elevated CPU usage: {cpu_usage:.1f}%")
    elif memory_usage > 90:
        status = "critical"
        issues.append(f"High memory usage: {memory_usage:.1f}%")
    elif memory_usage > 80:
        status = "warning"
        issues.append(f"Elevated memory usage: {memory_usage:.1f}%")
    elif disk_usage > 95:
        status = "critical"
        issues.append(f"High disk usage: {disk_usage:.1f}%")
    elif disk_usage > 85:
        status = "warning"
        issues.append(f"Elevated disk usage: {disk_usage:.1f}%")
    else:
        status = "healthy"
    
    return {
        "status": status,
        "message": "; ".join(issues) if issues else "System resources are healthy",
        "metrics": {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage
        }
    }


def _assess_application_health(error_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Assess application health based on error statistics"""
    error_rate = error_stats["error_rate"]
    total_errors = error_stats["total_errors"]
    
    if error_rate > 10:  # More than 10 errors per minute
        status = "critical"
        message = f"High error rate: {error_rate:.1f} errors/min"
    elif error_rate > 5:  # More than 5 errors per minute
        status = "warning"
        message = f"Elevated error rate: {error_rate:.1f} errors/min"
    elif total_errors == 0:
        status = "healthy"
        message = "No recent errors"
    else:
        status = "healthy"
        message = f"Low error rate: {error_rate:.1f} errors/min"
    
    return {
        "status": status,
        "message": message,
        "error_rate": error_rate,
        "total_errors": total_errors
    }