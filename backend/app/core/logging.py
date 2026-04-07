"""
Structured logging configuration for the Financial Analysis Platform
"""
import logging
import logging.config
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4
import traceback
from contextvars import ContextVar

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log structure
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context information
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id
        
        session_id = session_id_var.get()
        if session_id:
            log_entry["session_id"] = session_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": ''.join(traceback.format_exception(*record.exc_info))
            }
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class SecurityLogFilter(logging.Filter):
    """Filter for security-related logs"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter security-related log records"""
        security_keywords = [
            'login', 'logout', 'authentication', 'authorization',
            'permission', 'access', 'token', 'password', 'security',
            'breach', 'attack', 'suspicious', 'unauthorized'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in security_keywords)


class PerformanceLogFilter(logging.Filter):
    """Filter for performance-related logs"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter performance-related log records"""
        performance_keywords = [
            'slow', 'performance', 'timeout', 'latency',
            'response_time', 'query_time', 'execution_time'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in performance_keywords)


class LoggerManager:
    """Centralized logger management"""
    
    def __init__(self):
        self.configured = False
    
    def configure_logging(self, log_level: str = "INFO", log_file: Optional[str] = None):
        """Configure structured logging"""
        
        if self.configured:
            return
        
        # Logging configuration
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structured": {
                    "()": StructuredFormatter,
                },
                "simple": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "filters": {
                "security": {
                    "()": SecurityLogFilter,
                },
                "performance": {
                    "()": PerformanceLogFilter,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "structured",
                    "stream": sys.stdout
                },
                "security": {
                    "class": "logging.StreamHandler",
                    "level": "WARNING",
                    "formatter": "structured",
                    "stream": sys.stderr,
                    "filters": ["security"]
                },
                "performance": {
                    "class": "logging.StreamHandler",
                    "level": "WARNING",
                    "formatter": "structured",
                    "stream": sys.stdout,
                    "filters": ["performance"]
                }
            },
            "loggers": {
                "": {  # Root logger
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "app": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "app.security": {
                    "level": "INFO",
                    "handlers": ["console", "security"],
                    "propagate": False
                },
                "app.performance": {
                    "level": "INFO",
                    "handlers": ["console", "performance"],
                    "propagate": False
                },
                "sqlalchemy.engine": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False
                },
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
        
        # Add file handler if log file is specified
        if log_file:
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "structured",
                "filename": log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
            
            # Add file handler to all loggers
            for logger_config in config["loggers"].values():
                if "file" not in logger_config["handlers"]:
                    logger_config["handlers"].append("file")
        
        logging.config.dictConfig(config)
        self.configured = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger"""
        if not self.configured:
            self.configure_logging()
        
        return logging.getLogger(name)


class ContextLogger:
    """Logger with context management"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message"""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception message"""
        self.logger.exception(message, *args, **kwargs)
    
    def set_request_context(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Set request context for logging"""
        if request_id:
            request_id_var.set(request_id)
        if user_id:
            user_id_var.set(user_id)
        if session_id:
            session_id_var.set(session_id)
    
    def clear_context(self):
        """Clear request context"""
        request_id_var.set(None)
        user_id_var.set(None)
        session_id_var.set(None)
    
    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log API request"""
        self.logger.info(
            f"API Request: {method} {path}",
            extra={
                "event_type": "api_request",
                "method": method,
                "path": path,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "user_id": user_id,
                "ip_address": ip_address
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log security event"""
        extra_data = {
            "event_type": "security_event",
            "security_event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address
        }
        
        if additional_data:
            extra_data.update(additional_data)
        
        # Use security logger
        security_logger = logging.getLogger("app.security")
        security_logger.warning(message, extra=extra_data)
    
    def log_performance_issue(
        self,
        operation: str,
        duration_ms: float,
        threshold_ms: float = 1000,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log performance issue"""
        if duration_ms > threshold_ms:
            extra_data = {
                "event_type": "performance_issue",
                "operation": operation,
                "duration_ms": duration_ms,
                "threshold_ms": threshold_ms
            }
            
            if additional_data:
                extra_data.update(additional_data)
            
            # Use performance logger
            performance_logger = logging.getLogger("app.performance")
            performance_logger.warning(
                f"Slow operation detected: {operation} took {duration_ms}ms",
                extra=extra_data
            )
    
    def log_business_event(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log business event"""
        extra_data = {
            "event_type": "business_event",
            "business_event_type": event_type,
            "user_id": user_id
        }
        
        if additional_data:
            extra_data.update(additional_data)
        
        self.logger.info(message, extra=extra_data)
    
    def log_external_api_call(
        self,
        service_name: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log external API call"""
        extra_data = {
            "event_type": "external_api_call",
            "service_name": service_name,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "success": success
        }
        
        if error_message:
            extra_data["error_message"] = error_message
        
        level = logging.INFO if success else logging.ERROR
        message = f"External API call to {service_name}: {method} {endpoint}"
        
        self.logger.log(level, message, extra=extra_data)


# Global logger manager
logger_manager = LoggerManager()

# Convenience function to get a context logger
def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger"""
    base_logger = logger_manager.get_logger(name)
    return ContextLogger(base_logger)

# Application loggers
app_logger = get_logger("app")
security_logger = get_logger("app.security")
performance_logger = get_logger("app.performance")
api_logger = get_logger("app.api")
db_logger = get_logger("app.database")
external_logger = get_logger("app.external")
