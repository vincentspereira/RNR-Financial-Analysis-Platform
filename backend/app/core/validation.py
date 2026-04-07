"""
Input validation utilities for security
"""
import re
import html
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pydantic import BaseModel, validator, ValidationError
from fastapi import HTTPException, status

from app.core.logging import get_logger

logger = get_logger("validation")


class InputValidationError(Exception):
    """Custom validation error"""
    pass


class InputValidator:
    """Comprehensive input validation utilities"""
    
    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\bUNION\s+SELECT\b)",
        r"(\b(EXEC|EXECUTE)\s*\()",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValidationError("Input must be a string")
        
        # Check length
        if len(value) > max_length:
            raise ValidationError(f"Input too long (max {max_length} characters)")
        
        # HTML escape
        sanitized = html.escape(value.strip())
        
        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValidationError("Potentially malicious input detected")
        
        # Check for XSS patterns
        for pattern in InputValidator.XSS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValidationError("Potentially malicious script detected")
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format"""
        email = InputValidator.sanitize_string(email, 254)
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
        
        return email.lower()
    
    @staticmethod
    def validate_password(password: str) -> str:
        """Validate password strength"""
        if not isinstance(password, str):
            raise ValidationError("Password must be a string")
        
        if len(password) < 12:
            raise ValidationError("Password must be at least 12 characters long")
        
        if len(password) > 128:
            raise ValidationError("Password too long (max 128 characters)")
        
        # Check for required character types
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValidationError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        
        return password
    
    @staticmethod
    def validate_stock_symbol(symbol: str) -> str:
        """Validate stock symbol format"""
        symbol = InputValidator.sanitize_string(symbol, 10).upper()
        
        if not re.match(r'^[A-Z]{1,5}$', symbol):
            raise ValidationError("Invalid stock symbol format")
        
        return symbol
    
    @staticmethod
    def validate_numeric(value: Union[str, int, float], min_val: float = None, max_val: float = None) -> Decimal:
        """Validate numeric input"""
        try:
            if isinstance(value, str):
                # Remove any non-numeric characters except decimal point and minus
                cleaned = re.sub(r'[^\d.-]', '', value)
                decimal_value = Decimal(cleaned)
            else:
                decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid numeric value")
        
        if min_val is not None and decimal_value < Decimal(str(min_val)):
            raise ValidationError(f"Value must be at least {min_val}")
        
        if max_val is not None and decimal_value > Decimal(str(max_val)):
            raise ValidationError(f"Value must be at most {max_val}")
        
        return decimal_value
    
    @staticmethod
    def validate_date(date_str: str) -> datetime:
        """Validate date format"""
        date_str = InputValidator.sanitize_string(date_str, 20)
        
        # Try common date formats
        formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValidationError("Invalid date format")
    
    @staticmethod
    def validate_json_data(data: Dict[str, Any], max_depth: int = 5, max_keys: int = 100) -> Dict[str, Any]:
        """Validate JSON data structure"""
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
        
        def check_depth(obj, current_depth=0):
            if current_depth > max_depth:
                raise ValidationError(f"JSON too deeply nested (max depth: {max_depth})")
            
            if isinstance(obj, dict):
                if len(obj) > max_keys:
                    raise ValidationError(f"Too many keys in object (max: {max_keys})")
                
                for key, value in obj.items():
                    if not isinstance(key, str):
                        raise ValidationError("All keys must be strings")
                    
                    InputValidator.sanitize_string(key, 100)
                    check_depth(value, current_depth + 1)
            
            elif isinstance(obj, list):
                if len(obj) > max_keys:
                    raise ValidationError(f"Array too large (max: {max_keys})")
                
                for item in obj:
                    check_depth(item, current_depth + 1)
            
            elif isinstance(obj, str):
                InputValidator.sanitize_string(obj, 10000)
        
        check_depth(data)
        return data


class RequestValidator:
    """Request-level validation middleware"""
    
    @staticmethod
    def validate_content_type(content_type: str, allowed_types: List[str]) -> bool:
        """Validate request content type"""
        if not content_type:
            return False
        
        # Extract main content type (ignore charset, etc.)
        main_type = content_type.split(';')[0].strip().lower()
        return main_type in [t.lower() for t in allowed_types]
    
    @staticmethod
    def validate_content_length(content_length: int, max_size: int = 10 * 1024 * 1024) -> bool:
        """Validate request content length (default 10MB)"""
        return 0 <= content_length <= max_size
    
    @staticmethod
    def validate_user_agent(user_agent: str) -> bool:
        """Validate user agent string"""
        if not user_agent or len(user_agent) > 500:
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'eval\(',
            r'expression\(',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return False
        
        return True


# Pydantic models for common validation scenarios
class EmailValidation(BaseModel):
    email: str
    
    @validator('email')
    def validate_email_field(cls, v):
        return InputValidator.validate_email(v)


class PasswordValidation(BaseModel):
    password: str
    
    @validator('password')
    def validate_password_field(cls, v):
        return InputValidator.validate_password(v)


class StockSymbolValidation(BaseModel):
    symbol: str
    
    @validator('symbol')
    def validate_symbol_field(cls, v):
        return InputValidator.validate_stock_symbol(v)


def validate_request_data(data: Dict[str, Any], validation_model: BaseModel) -> Dict[str, Any]:
    """Validate request data using Pydantic model"""
    try:
        validated = validation_model(**data)
        return validated.dict()
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request validation failed. Please check your input and try again."
        )
    except Exception as e:
        logger.error(f"Invalid request data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request data. Please check your input and try again."
        )
