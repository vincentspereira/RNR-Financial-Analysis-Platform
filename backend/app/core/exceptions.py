"""
Standardized exception handling for the Financial Analysis Platform
"""
from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes"""
    
    # Authentication & Authorization
    INVALID_CREDENTIALS = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    TOKEN_INVALID = "AUTH_003"
    INSUFFICIENT_PERMISSIONS = "AUTH_004"
    ACCOUNT_LOCKED = "AUTH_005"
    PASSWORD_REQUIREMENTS_NOT_MET = "AUTH_006"
    
    # Validation Errors
    INVALID_INPUT = "VAL_001"
    MISSING_REQUIRED_FIELD = "VAL_002"
    INVALID_FORMAT = "VAL_003"
    VALUE_OUT_OF_RANGE = "VAL_004"
    DUPLICATE_ENTRY = "VAL_005"
    
    # Business Logic Errors
    COMPANY_NOT_FOUND = "BIZ_001"
    PORTFOLIO_NOT_FOUND = "BIZ_002"
    INSUFFICIENT_DATA = "BIZ_003"
    CALCULATION_ERROR = "BIZ_004"
    DATA_INTEGRITY_ERROR = "BIZ_005"
    
    # External Service Errors
    EXTERNAL_API_ERROR = "EXT_001"
    EXTERNAL_API_RATE_LIMIT = "EXT_002"
    EXTERNAL_API_UNAVAILABLE = "EXT_003"
    DATA_SOURCE_ERROR = "EXT_004"
    
    # System Errors
    DATABASE_ERROR = "SYS_001"
    CACHE_ERROR = "SYS_002"
    FILE_SYSTEM_ERROR = "SYS_003"
    CONFIGURATION_ERROR = "SYS_004"
    INTERNAL_SERVER_ERROR = "SYS_005"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_001"
    QUOTA_EXCEEDED = "RATE_002"


class BaseAPIException(Exception):
    """Base exception class for all API exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "details": self.details
            }
        }
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException"""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict(),
            headers=self.headers
        )


class AuthenticationError(BaseAPIException):
    """Authentication related errors"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.INVALID_CREDENTIALS,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(BaseAPIException):
    """Authorization related errors"""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: ErrorCode = ErrorCode.INSUFFICIENT_PERMISSIONS,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ValidationError(BaseAPIException):
    """Input validation errors"""
    
    def __init__(
        self,
        message: str = "Validation failed",
        error_code: ErrorCode = ErrorCode.INVALID_INPUT,
        details: Optional[Dict[str, Any]] = None,
        field_errors: Optional[Dict[str, str]] = None
    ):
        if field_errors:
            details = details or {}
            details["field_errors"] = field_errors
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundError(BaseAPIException):
    """Resource not found errors"""
    
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: ErrorCode = ErrorCode.COMPANY_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class BusinessLogicError(BaseAPIException):
    """Business logic related errors"""
    
    def __init__(
        self,
        message: str = "Business logic error",
        error_code: ErrorCode = ErrorCode.CALCULATION_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class ExternalServiceError(BaseAPIException):
    """External service related errors"""
    
    def __init__(
        self,
        message: str = "External service error",
        error_code: ErrorCode = ErrorCode.EXTERNAL_API_ERROR,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_502_BAD_GATEWAY
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details
        )


class RateLimitError(BaseAPIException):
    """Rate limiting errors"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            headers=headers
        )


class DatabaseError(BaseAPIException):
    """Database related errors"""
    
    def __init__(
        self,
        message: str = "Database error",
        error_code: ErrorCode = ErrorCode.DATABASE_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ErrorHandler:
    """Centralized error handling utilities"""
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str = "database operation") -> DatabaseError:
        """Handle database errors with logging"""
        logger.error(f"Database error during {operation}: {str(error)}")
        
        # Don't expose internal database errors to users
        return DatabaseError(
            message=f"An error occurred during {operation}",
            details={"operation": operation}
        )
    
    @staticmethod
    def handle_external_api_error(
        error: Exception,
        service_name: str,
        endpoint: str = None
    ) -> ExternalServiceError:
        """Handle external API errors with logging"""
        logger.error(f"External API error from {service_name}: {str(error)}")
        
        details = {"service": service_name}
        if endpoint:
            details["endpoint"] = endpoint
        
        return ExternalServiceError(
            message=f"Error communicating with {service_name}",
            details=details
        )
    
    @staticmethod
    def handle_validation_error(
        field_errors: Dict[str, str],
        message: str = "Validation failed"
    ) -> ValidationError:
        """Handle validation errors"""
        return ValidationError(
            message=message,
            field_errors=field_errors
        )
    
    @staticmethod
    def handle_business_logic_error(
        message: str,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None
    ) -> BusinessLogicError:
        """Handle business logic errors"""
        logger.warning(f"Business logic error: {message}")
        
        return BusinessLogicError(
            message=message,
            error_code=error_code,
            details=context
        )
    
    @staticmethod
    def log_and_raise(exception: BaseAPIException, context: Optional[Dict[str, Any]] = None):
        """Log exception and raise it"""
        log_data = {
            "error_code": exception.error_code.value,
            "message": exception.message,
            "status_code": exception.status_code
        }
        
        if context:
            log_data["context"] = context
        
        if exception.status_code >= 500:
            logger.error("Server error occurred", extra=log_data)
        else:
            logger.warning("Client error occurred", extra=log_data)
        
        raise exception


# Convenience functions for common error scenarios
def raise_not_found(resource_type: str, identifier: str):
    """Raise a not found error"""
    error_codes = {
        "company": ErrorCode.COMPANY_NOT_FOUND,
        "portfolio": ErrorCode.PORTFOLIO_NOT_FOUND,
    }
    
    error_code = error_codes.get(resource_type.lower(), ErrorCode.COMPANY_NOT_FOUND)
    
    raise NotFoundError(
        message=f"{resource_type.title()} not found",
        error_code=error_code,
        details={"resource_type": resource_type, "identifier": identifier}
    )


def raise_validation_error(field: str, message: str):
    """Raise a validation error for a specific field"""
    raise ValidationError(
        message="Validation failed",
        field_errors={field: message}
    )


def raise_insufficient_data(operation: str, required_data: str):
    """Raise an insufficient data error"""
    raise BusinessLogicError(
        message=f"Insufficient data for {operation}",
        error_code=ErrorCode.INSUFFICIENT_DATA,
        details={"operation": operation, "required_data": required_data}
    )


# Global error handler instance
error_handler = ErrorHandler()
