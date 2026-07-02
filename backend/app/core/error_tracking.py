"""
Error tracking and reporting system
"""
import traceback
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from uuid import uuid4
from contextlib import contextmanager

from app.core.logging import get_logger
from app.core.monitoring import metrics_collector

error_logger = get_logger("error_tracking")


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    NETWORK = "network"
    PERFORMANCE = "performance"
    SECURITY = "security"


class ErrorContext:
    """Context information for errors"""
    
    def __init__(self):
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.request_id: Optional[str] = None
        self.ip_address: Optional[str] = None
        self.user_agent: Optional[str] = None
        self.endpoint: Optional[str] = None
        self.method: Optional[str] = None
        self.parameters: Optional[Dict[str, Any]] = None
        self.additional_data: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "endpoint": self.endpoint,
            "method": self.method,
            "parameters": self.parameters,
            "additional_data": self.additional_data
        }


class ErrorReport:
    """Structured error report"""
    
    def __init__(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[ErrorContext] = None,
        custom_message: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        self.id = str(uuid4())
        self.timestamp = datetime.now(timezone.utc)
        self.error = error
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.custom_message = custom_message
        self.tags = tags or {}
        
        # Extract error information
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.traceback = traceback.format_exc()
        self.stack_trace = traceback.extract_tb(error.__traceback__)
        
        # Get the frame where the error occurred
        if self.stack_trace:
            frame = self.stack_trace[-1]
            self.filename = frame.filename
            self.line_number = frame.lineno
            self.function_name = frame.name
        else:
            self.filename = None
            self.line_number = None
            self.function_name = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "custom_message": self.custom_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "filename": self.filename,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "traceback": self.traceback,
            "context": self.context.to_dict(),
            "tags": self.tags
        }


class ErrorTracker:
    """Central error tracking system"""
    
    def __init__(self):
        self.error_reports: List[ErrorReport] = []
        self.error_counts: Dict[str, int] = {}
        self.max_reports = 1000  # Keep last 1000 error reports in memory
        
    def track_error(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[ErrorContext] = None,
        custom_message: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Track an error and return error ID"""
        
        # Create error report
        report = ErrorReport(
            error=error,
            severity=severity,
            category=category,
            context=context,
            custom_message=custom_message,
            tags=tags
        )
        
        # Add to reports list
        self.error_reports.append(report)
        
        # Maintain max reports limit
        if len(self.error_reports) > self.max_reports:
            self.error_reports = self.error_reports[-self.max_reports:]
        
        # Update error counts
        error_key = f"{report.error_type}:{report.category.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log error
        self._log_error(report)
        
        # Send metrics
        self._send_metrics(report)
        
        # Handle critical errors
        if severity == ErrorSeverity.CRITICAL:
            self._handle_critical_error(report)
        
        return report.id
    
    def _log_error(self, report: ErrorReport):
        """Log error report.

        NB: `message` is a reserved LogRecord attribute — using it in `extra`
        triggers a KeyError in the stdlib logging module. Use `error_message`
        instead.
        """
        log_data = {
            "error_id": report.id,
            "error_type": report.error_type,
            "severity": report.severity.value,
            "category": report.category.value,
            "error_message": report.custom_message or report.error_message,
            "context": report.context.to_dict(),
            "tags": report.tags,
        }
        
        if report.severity == ErrorSeverity.CRITICAL:
            error_logger.critical("Critical error occurred", extra=log_data)
        elif report.severity == ErrorSeverity.HIGH:
            error_logger.error("High severity error occurred", extra=log_data)
        elif report.severity == ErrorSeverity.MEDIUM:
            error_logger.warning("Medium severity error occurred", extra=log_data)
        else:
            error_logger.info("Low severity error occurred", extra=log_data)
    
    def _send_metrics(self, report: ErrorReport):
        """Send error metrics"""
        tags = {
            "error_type": report.error_type,
            "severity": report.severity.value,
            "category": report.category.value,
            **report.tags
        }
        
        # Increment error counter
        metrics_collector.increment_counter("errors_total", tags=tags)
        
        # Track error by endpoint if available
        if report.context.endpoint:
            endpoint_tags = {**tags, "endpoint": report.context.endpoint}
            metrics_collector.increment_counter("endpoint_errors_total", tags=endpoint_tags)
    
    def _handle_critical_error(self, report: ErrorReport):
        """Handle critical errors with immediate notifications"""
        # TODO: Implement immediate notification system
        # This could send alerts to Slack, email, PagerDuty, etc.
        error_logger.critical(
            f"CRITICAL ERROR ALERT: {report.error_type} - {report.error_message}",
            extra={
                "alert": True,
                "error_id": report.id,
                "context": report.context.to_dict()
            }
        )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_reports:
            return {
                "total_errors": 0,
                "error_rate": 0,
                "top_errors": [],
                "severity_distribution": {},
                "category_distribution": {}
            }
        
        # Calculate statistics
        total_errors = len(self.error_reports)
        
        # Severity distribution
        severity_dist = {}
        for report in self.error_reports:
            severity = report.severity.value
            severity_dist[severity] = severity_dist.get(severity, 0) + 1
        
        # Category distribution
        category_dist = {}
        for report in self.error_reports:
            category = report.category.value
            category_dist[category] = category_dist.get(category, 0) + 1
        
        # Top errors
        top_errors = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_errors": total_errors,
            "error_rate": self._calculate_error_rate(),
            "top_errors": [{"error": error, "count": count} for error, count in top_errors],
            "severity_distribution": severity_dist,
            "category_distribution": category_dist,
            "recent_errors": [
                {
                    "id": report.id,
                    "timestamp": report.timestamp.isoformat(),
                    "error_type": report.error_type,
                    "severity": report.severity.value,
                    "message": report.error_message[:100]
                }
                for report in self.error_reports[-10:]
            ]
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate (errors per minute)"""
        if not self.error_reports:
            return 0.0
        
        # Calculate errors in the last hour
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        recent_errors = [
            report for report in self.error_reports
            if report.timestamp >= one_hour_ago
        ]
        
        return len(recent_errors) / 60.0  # errors per minute
    
    def get_error_by_id(self, error_id: str) -> Optional[ErrorReport]:
        """Get error report by ID"""
        for report in self.error_reports:
            if report.id == error_id:
                return report
        return None
    
    def clear_old_errors(self, days: int = 7):
        """Clear errors older than specified days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        self.error_reports = [
            report for report in self.error_reports
            if report.timestamp >= cutoff_date
        ]


# Global error tracker instance
error_tracker = ErrorTracker()


# Context manager for error tracking
@contextmanager
def track_errors(
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    context: Optional[ErrorContext] = None,
    custom_message: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    reraise: bool = True
):
    """Context manager for automatic error tracking"""
    try:
        yield
    except Exception as e:
        error_tracker.track_error(
            error=e,
            severity=severity,
            category=category,
            context=context,
            custom_message=custom_message,
            tags=tags
        )
        if reraise:
            raise


# Decorator for automatic error tracking
def track_function_errors(
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    custom_message: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """Decorator for automatic function error tracking"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create context with function information
                context = ErrorContext()
                context.additional_data = {
                    "function_name": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
                
                error_tracker.track_error(
                    error=e,
                    severity=severity,
                    category=category,
                    context=context,
                    custom_message=custom_message or f"Error in function {func.__name__}",
                    tags=tags
                )
                raise
        return wrapper
    return decorator


# Async version of the decorator
def track_async_function_errors(
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    custom_message: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """Decorator for automatic async function error tracking"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Create context with function information
                context = ErrorContext()
                context.additional_data = {
                    "function_name": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
                
                error_tracker.track_error(
                    error=e,
                    severity=severity,
                    category=category,
                    context=context,
                    custom_message=custom_message or f"Error in async function {func.__name__}",
                    tags=tags
                )
                raise
        return wrapper
    return decorator


# Convenience functions for common error tracking scenarios
def track_database_error(error: Exception, context: Optional[ErrorContext] = None):
    """Track database-related errors"""
    return error_tracker.track_error(
        error=error,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.DATABASE,
        context=context,
        custom_message="Database operation failed"
    )


def track_api_error(error: Exception, context: Optional[ErrorContext] = None):
    """Track external API errors"""
    return error_tracker.track_error(
        error=error,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.EXTERNAL_API,
        context=context,
        custom_message="External API call failed"
    )


def track_validation_error(error: Exception, context: Optional[ErrorContext] = None):
    """Track validation errors"""
    return error_tracker.track_error(
        error=error,
        severity=ErrorSeverity.LOW,
        category=ErrorCategory.VALIDATION,
        context=context,
        custom_message="Input validation failed"
    )


def track_security_error(error: Exception, context: Optional[ErrorContext] = None):
    """Track security-related errors"""
    return error_tracker.track_error(
        error=error,
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.SECURITY,
        context=context,
        custom_message="Security violation detected"
    )
