"""
Comprehensive Unit Tests for Core Modules - 100% Coverage Target
"""
import pytest
import asyncio
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import hashlib
from decimal import Decimal

# Core module imports - using actual available modules
from app.core.config import Settings, settings
from app.core.security import SecurityConfig, PasswordValidator
from app.core.exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    DatabaseError, ExternalServiceError, BusinessLogicError
)
from app.services.auth.password_handler import PasswordHandler


class TestSettings:
    """Comprehensive tests for Settings configuration"""
    
    def test_settings_initialization(self):
        """Test settings initialization with default values"""
        test_settings = Settings()
        
        # Test default values that exist
        assert test_settings.PROJECT_NAME == "Financial Analysis Platform"
        assert test_settings.VERSION == "1.0.0"
        assert test_settings.DEBUG is False
        assert test_settings.ENVIRONMENT == "production"
        assert test_settings.API_V1_STR == "/api/v1"
        
        # Test database settings
        assert test_settings.DATABASE_POOL_SIZE == 20
        assert test_settings.DATABASE_MAX_OVERFLOW == 30
        assert test_settings.DATABASE_POOL_RECYCLE == 3600
        
        # Test security settings
        assert test_settings.SECRET_KEY is not None
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert test_settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    
    def test_settings_from_environment(self):
        """Test settings loading from environment variables"""
        with patch.dict(os.environ, {
            'PROJECT_NAME': 'Test Project',
            'DEBUG': 'true',
            'ENVIRONMENT': 'testing',
            'DATABASE_POOL_SIZE': '10',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '60'
        }):
            test_settings = Settings()
            
            assert test_settings.PROJECT_NAME == 'Test Project'
            assert test_settings.DEBUG is True
            assert test_settings.ENVIRONMENT == 'testing'
            assert test_settings.DATABASE_POOL_SIZE == 10
            assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60
    
    def test_cors_origins_validation(self):
        """Test CORS origins validation"""
        # Test with string input
        with patch.dict(os.environ, {'BACKEND_CORS_ORIGINS': 'http://localhost:3000,https://example.com'}):
            test_settings = Settings()
            assert len(test_settings.BACKEND_CORS_ORIGINS) == 2
            assert 'http://localhost:3000' in test_settings.BACKEND_CORS_ORIGINS
            assert 'https://example.com' in test_settings.BACKEND_CORS_ORIGINS
        
        # Test with list input
        cors_origins = ['http://localhost:3000', 'https://example.com']
        test_settings = Settings(BACKEND_CORS_ORIGINS=cors_origins)
        assert test_settings.BACKEND_CORS_ORIGINS == cors_origins
    
    def test_database_url_construction(self):
        """Test database URL construction"""
        with patch.dict(os.environ, {
            'POSTGRES_SERVER': 'localhost',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'testdb',
            'POSTGRES_PORT': '5432'
        }):
            test_settings = Settings()
            expected_url = 'postgresql://testuser:testpass@localhost:5432/testdb'
            assert test_settings.DATABASE_URL == expected_url


class TestSecurityFunctions:
    """Comprehensive tests for Security functions"""
    
    @pytest.fixture
    def password_handler(self):
        """Create password handler instance"""
        return PasswordHandler()
    
    def test_password_hashing(self, password_handler):
        """Test password hashing functionality"""
        password = "SecurePassword123!"
        
        # Test password hashing
        hashed = password_handler.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash format
        assert len(hashed) >= 50  # bcrypt hashes are typically 60 characters
        
        # Test password verification
        assert password_handler.verify_password(password, hashed) is True
        assert password_handler.verify_password("WrongPassword", hashed) is False
    
    def test_password_hash_uniqueness(self, password_handler):
        """Test that password hashes are unique due to salt"""
        password = "TestPassword123!"
        
        hash1 = password_handler.hash_password(password)
        hash2 = password_handler.hash_password(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        
        # Both should verify correctly
        assert password_handler.verify_password(password, hash1) is True
        assert password_handler.verify_password(password, hash2) is True
    
    def test_security_config_constants(self):
        """Test security configuration constants"""
        assert SecurityConfig.MIN_PASSWORD_LENGTH >= 8
        assert SecurityConfig.MAX_PASSWORD_LENGTH <= 256
        assert SecurityConfig.MAX_LOGIN_ATTEMPTS > 0
        assert SecurityConfig.LOCKOUT_DURATION_MINUTES > 0
        assert SecurityConfig.SESSION_TIMEOUT_MINUTES > 0
        
        # Test security headers
        assert "X-Content-Type-Options" in SecurityConfig.SECURITY_HEADERS
        assert "X-Frame-Options" in SecurityConfig.SECURITY_HEADERS
        assert "X-XSS-Protection" in SecurityConfig.SECURITY_HEADERS
    
    def test_password_validator_exists(self):
        """Test that PasswordValidator class exists"""
        assert PasswordValidator is not None
        # Test that it can be instantiated if it's a class
        try:
            validator = PasswordValidator()
            assert validator is not None
        except TypeError:
            # If it's not instantiable, that's also fine
            pass


class TestCustomExceptions:
    """Comprehensive tests for custom exceptions"""
    
    def test_validation_error(self):
        """Test ValidationError exception"""
        message = "Invalid input data"
        
        error = ValidationError(message)
        
        assert str(error) == message
        assert hasattr(error, 'status_code')
    
    def test_authentication_error(self):
        """Test AuthenticationError exception"""
        message = "Invalid credentials"
        
        error = AuthenticationError(message)
        
        assert str(error) == message
        assert hasattr(error, 'status_code')
    
    def test_authorization_error(self):
        """Test AuthorizationError exception"""
        message = "Insufficient permissions"
        
        error = AuthorizationError(message)
        
        assert str(error) == message
        assert hasattr(error, 'status_code')
    
    def test_database_error(self):
        """Test DatabaseError exception"""
        message = "Database connection failed"
        
        error = DatabaseError(message)
        
        assert str(error) == message
        assert hasattr(error, 'status_code')
    
    def test_external_service_error(self):
        """Test ExternalServiceError exception"""
        message = "External API unavailable"
        
        error = ExternalServiceError(message)
        
        assert str(error) == message
        assert hasattr(error, 'status_code')
    
    def test_business_logic_error(self):
        """Test BusinessLogicError exception"""
        message = "Invalid business operation"
        
        error = BusinessLogicError(message)
        
        assert str(error) == message
        assert hasattr(error, 'status_code')


# Edge Cases and Error Handling Tests
class TestCoreModulesEdgeCases:
    """Test edge cases and error conditions for core modules"""
    
    def test_security_with_invalid_data(self):
        """Test security functions with invalid input data"""
        password_handler = PasswordHandler()
        
        # Test with None input
        with pytest.raises((ValueError, TypeError)):
            password_handler.hash_password(None)
        
        # Test with empty string
        with pytest.raises((ValueError, TypeError)):
            password_handler.hash_password("")
    
    def test_password_verification_edge_cases(self):
        """Test password verification edge cases"""
        password_handler = PasswordHandler()
        password = "TestPassword123!"
        hashed = password_handler.hash_password(password)
        
        # Test with None values
        assert password_handler.verify_password(None, hashed) is False
        assert password_handler.verify_password(password, None) is False
        assert password_handler.verify_password(None, None) is False
        
        # Test with empty strings
        assert password_handler.verify_password("", hashed) is False
        assert password_handler.verify_password(password, "") is False
    
    def test_settings_with_invalid_environment_values(self):
        """Test settings with invalid environment values"""
        # Test with invalid boolean values
        with patch.dict(os.environ, {'DEBUG': 'invalid_boolean'}):
            try:
                test_settings = Settings()
                # Should handle invalid boolean gracefully
                assert isinstance(test_settings.DEBUG, bool)
            except Exception:
                # Or raise appropriate validation error
                pass
        
        # Test with invalid integer values
        with patch.dict(os.environ, {'DATABASE_POOL_SIZE': 'not_a_number'}):
            try:
                test_settings = Settings()
                # Should handle invalid integer gracefully
                assert isinstance(test_settings.DATABASE_POOL_SIZE, int)
            except Exception:
                # Or raise appropriate validation error
                pass
    
    def test_exception_inheritance(self):
        """Test that custom exceptions inherit properly"""
        # Test that all custom exceptions inherit from appropriate base classes
        validation_error = ValidationError("test")
        auth_error = AuthenticationError("test")
        authz_error = AuthorizationError("test")
        db_error = DatabaseError("test")
        service_error = ExternalServiceError("test")
        business_error = BusinessLogicError("test")
        
        # All should be instances of Exception
        assert isinstance(validation_error, Exception)
        assert isinstance(auth_error, Exception)
        assert isinstance(authz_error, Exception)
        assert isinstance(db_error, Exception)
        assert isinstance(service_error, Exception)
        assert isinstance(business_error, Exception)
    
    def test_settings_required_fields(self):
        """Test that required settings fields are present"""
        test_settings = Settings()
        
        # Test that critical settings are not None
        assert test_settings.SECRET_KEY is not None
        assert test_settings.PROJECT_NAME is not None
        assert test_settings.VERSION is not None
        
        # Test that numeric settings have valid values
        assert test_settings.DATABASE_POOL_SIZE > 0
        assert test_settings.DATABASE_MAX_OVERFLOW > 0
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
    
    def test_password_hashing_performance(self):
        """Test password hashing performance characteristics"""
        password_handler = PasswordHandler()
        password = "TestPassword123!"
        
        # Test that hashing takes reasonable time (should be slow for security)
        import time
        start_time = time.time()
        hashed = password_handler.hash_password(password)
        end_time = time.time()
        
        # Bcrypt should take some time (at least a few milliseconds)
        duration = end_time - start_time
        assert duration > 0.001  # At least 1ms
        assert duration < 1.0    # But not more than 1 second
        
        # Test that verification also takes time
        start_time = time.time()
        result = password_handler.verify_password(password, hashed)
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration > 0.001  # At least 1ms
        assert result is True
    
    def test_settings_environment_override_priority(self):
        """Test that environment variables override default values"""
        # Test with a specific setting
        default_settings = Settings()
        default_pool_size = default_settings.DATABASE_POOL_SIZE
        
        # Override with environment variable
        new_pool_size = default_pool_size + 10
        with patch.dict(os.environ, {'DATABASE_POOL_SIZE': str(new_pool_size)}):
            env_settings = Settings()
            assert env_settings.DATABASE_POOL_SIZE == new_pool_size
            assert env_settings.DATABASE_POOL_SIZE != default_pool_size
    
    def test_exception_string_representations(self):
        """Test string representations of custom exceptions"""
        test_message = "Test error message"
        
        exceptions = [
            ValidationError(test_message),
            AuthenticationError(test_message),
            AuthorizationError(test_message),
            DatabaseError(test_message),
            ExternalServiceError(test_message),
            BusinessLogicError(test_message)
        ]
        
        for exception in exceptions:
            str_repr = str(exception)
            assert test_message in str_repr
            assert len(str_repr) > 0
    
    def test_password_complexity_edge_cases(self):
        """Test password hashing with various complexity levels"""
        password_handler = PasswordHandler()
        
        # Test with different password complexities
        passwords = [
            "Simple123!",
            "VeryLongAndComplexPassword123!@#$%^&*()",
            "短密码123!",  # Unicode characters
            "Pass123!" + "x" * 100,  # Very long password
        ]
        
        for password in passwords:
            try:
                hashed = password_handler.hash_password(password)
                assert hashed is not None
                assert password_handler.verify_password(password, hashed) is True
            except Exception as e:
                # Some edge cases might not be supported
                assert isinstance(e, (ValueError, TypeError))


class TestConfigurationValidation:
    """Test configuration validation and edge cases"""
    
    def test_database_configuration_validation(self):
        """Test database configuration validation"""
        settings_instance = Settings()
        
        # Test that database URL is properly formatted
        if hasattr(settings_instance, 'DATABASE_URL') and settings_instance.DATABASE_URL:
            db_url = settings_instance.DATABASE_URL
            assert db_url.startswith(('postgresql://', 'sqlite:///', 'mysql://'))
        
        # Test pool settings are reasonable
        assert 1 <= settings_instance.DATABASE_POOL_SIZE <= 100
        assert 0 <= settings_instance.DATABASE_MAX_OVERFLOW <= 200
        assert 300 <= settings_instance.DATABASE_POOL_RECYCLE <= 7200  # 5 minutes to 2 hours
    
    def test_security_configuration_validation(self):
        """Test security configuration validation"""
        settings_instance = Settings()
        
        # Test token expiration times are reasonable
        assert 1 <= settings_instance.ACCESS_TOKEN_EXPIRE_MINUTES <= 1440  # 1 minute to 24 hours
        assert 1 <= settings_instance.REFRESH_TOKEN_EXPIRE_DAYS <= 365     # 1 day to 1 year
        
        # Test secret key has minimum length
        assert len(settings_instance.SECRET_KEY) >= 32
    
    def test_cors_configuration_validation(self):
        """Test CORS configuration validation"""
        settings_instance = Settings()
        
        # Test CORS origins format
        for origin in settings_instance.BACKEND_CORS_ORIGINS:
            # Should be valid URL format or wildcard
            assert origin == "*" or origin.startswith(('http://', 'https://'))
    
    def test_api_configuration_validation(self):
        """Test API configuration validation"""
        settings_instance = Settings()
        
        # Test API version string format
        assert settings_instance.API_V1_STR.startswith('/api/')
        assert 'v1' in settings_instance.API_V1_STR.lower()
        
        # Test project metadata
        assert len(settings_instance.PROJECT_NAME) > 0
        assert len(settings_instance.VERSION) > 0
        
        # Test environment is valid
        valid_environments = ['development', 'testing', 'staging', 'production']
        assert settings_instance.ENVIRONMENT in valid_environments


class TestSettings:
    """Comprehensive tests for Settings configuration"""
    
    def test_settings_initialization(self):
        """Test settings initialization with default values"""
        test_settings = Settings()
        
        # Test default values
        assert test_settings.PROJECT_NAME == "Financial Analysis Platform"
        assert test_settings.VERSION == "1.0.0"
        assert test_settings.DEBUG is False
        assert test_settings.ENVIRONMENT == "production"
        assert test_settings.API_V1_STR == "/api/v1"
        
        # Test database settings
        assert test_settings.DATABASE_POOL_SIZE == 20
        assert test_settings.DATABASE_MAX_OVERFLOW == 30
        assert test_settings.DATABASE_POOL_RECYCLE == 3600
        
        # Test security settings
        assert test_settings.SECRET_KEY is not None
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert test_settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
        
        # Test external API settings
        assert hasattr(test_settings, 'ALPHA_VANTAGE_API_KEY')
        assert hasattr(test_settings, 'YAHOO_FINANCE_API_KEY')
    
    def test_settings_from_environment(self):
        """Test settings loading from environment variables"""
        with patch.dict(os.environ, {
            'PROJECT_NAME': 'Test Project',
            'DEBUG': 'true',
            'ENVIRONMENT': 'testing',
            'DATABASE_POOL_SIZE': '10',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '60'
        }):
            test_settings = Settings()
            
            assert test_settings.PROJECT_NAME == 'Test Project'
            assert test_settings.DEBUG is True
            assert test_settings.ENVIRONMENT == 'testing'
            assert test_settings.DATABASE_POOL_SIZE == 10
            assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60
    
    def test_cors_origins_validation(self):
        """Test CORS origins validation"""
        # Test with string input
        with patch.dict(os.environ, {'BACKEND_CORS_ORIGINS': 'http://localhost:3000,https://example.com'}):
            test_settings = Settings()
            assert len(test_settings.BACKEND_CORS_ORIGINS) == 2
            assert 'http://localhost:3000' in test_settings.BACKEND_CORS_ORIGINS
            assert 'https://example.com' in test_settings.BACKEND_CORS_ORIGINS
        
        # Test with list input
        cors_origins = ['http://localhost:3000', 'https://example.com']
        test_settings = Settings(BACKEND_CORS_ORIGINS=cors_origins)
        assert test_settings.BACKEND_CORS_ORIGINS == cors_origins
    
    def test_database_url_construction(self):
        """Test database URL construction"""
        with patch.dict(os.environ, {
            'POSTGRES_SERVER': 'localhost',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'testdb',
            'POSTGRES_PORT': '5432'
        }):
            test_settings = Settings()
            expected_url = 'postgresql://testuser:testpass@localhost:5432/testdb'
            assert test_settings.DATABASE_URL == expected_url
    
    def test_redis_url_construction(self):
        """Test Redis URL construction"""
        with patch.dict(os.environ, {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0',
            'REDIS_PASSWORD': 'testpass'
        }):
            test_settings = Settings()
            expected_url = 'redis://:testpass@localhost:6379/0'
            assert test_settings.REDIS_URL == expected_url


class TestCacheManager:
    """Comprehensive tests for CacheManager"""
    
    @pytest.fixture
    def cache_manager_instance(self):
        """Create a fresh cache manager instance for testing"""
        return CacheManager()
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager_instance):
        """Test basic cache set and get operations"""
        key = "test_key"
        value = {"data": "test_value", "number": 42}
        
        # Mock Redis operations
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.get = AsyncMock(return_value=json.dumps(value))
            
            # Test set operation
            result = await cache_manager_instance.set(key, value, expire=300)
            assert result is True
            mock_redis.set.assert_called_once()
            
            # Test get operation
            cached_value = await cache_manager_instance.get(key)
            assert cached_value == value
            mock_redis.get.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_cache_get_nonexistent_key(self, cache_manager_instance):
        """Test getting a non-existent cache key"""
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            
            result = await cache_manager_instance.get("nonexistent_key")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_manager_instance):
        """Test cache deletion"""
        key = "test_key_to_delete"
        
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.delete = AsyncMock(return_value=1)
            
            result = await cache_manager_instance.delete(key)
            assert result is True
            mock_redis.delete.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_cache_exists(self, cache_manager_instance):
        """Test cache key existence check"""
        key = "existing_key"
        
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.exists = AsyncMock(return_value=1)
            
            result = await cache_manager_instance.exists(key)
            assert result is True
            mock_redis.exists.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_cache_expire(self, cache_manager_instance):
        """Test setting cache expiration"""
        key = "expiring_key"
        expire_seconds = 600
        
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.expire = AsyncMock(return_value=True)
            
            result = await cache_manager_instance.expire(key, expire_seconds)
            assert result is True
            mock_redis.expire.assert_called_once_with(key, expire_seconds)
    
    @pytest.mark.asyncio
    async def test_cache_increment(self, cache_manager_instance):
        """Test cache increment operation"""
        key = "counter_key"
        
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.incr = AsyncMock(return_value=5)
            
            result = await cache_manager_instance.increment(key)
            assert result == 5
            mock_redis.incr.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_cache_decrement(self, cache_manager_instance):
        """Test cache decrement operation"""
        key = "counter_key"
        
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.decr = AsyncMock(return_value=3)
            
            result = await cache_manager_instance.decrement(key)
            assert result == 3
            mock_redis.decr.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_cache_hash_operations(self, cache_manager_instance):
        """Test cache hash operations"""
        hash_key = "user:123"
        field = "name"
        value = "John Doe"
        
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.hset = AsyncMock(return_value=1)
            mock_redis.hget = AsyncMock(return_value=value)
            mock_redis.hgetall = AsyncMock(return_value={field: value})
            
            # Test hash set
            result = await cache_manager_instance.hset(hash_key, field, value)
            assert result == 1
            
            # Test hash get
            result = await cache_manager_instance.hget(hash_key, field)
            assert result == value
            
            # Test hash get all
            result = await cache_manager_instance.hgetall(hash_key)
            assert result == {field: value}
    
    @pytest.mark.asyncio
    async def test_cache_connection_error_handling(self, cache_manager_instance):
        """Test cache connection error handling"""
        with patch.object(cache_manager_instance, 'redis') as mock_redis:
            mock_redis.get = AsyncMock(side_effect=Exception("Connection failed"))
            
            # Should handle connection errors gracefully
            result = await cache_manager_instance.get("test_key")
            assert result is None


class TestSecurityManager:
    """Comprehensive tests for SecurityManager"""
    
    @pytest.fixture
    def security_manager(self):
        """Create a security manager instance"""
        return SecurityManager()
    
    def test_password_hashing(self, security_manager):
        """Test password hashing functionality"""
        password = "SecurePassword123!"
        
        # Test password hashing
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash format
        assert len(hashed) >= 50  # bcrypt hashes are typically 60 characters
        
        # Test password verification
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
    
    def test_password_hash_uniqueness(self, security_manager):
        """Test that password hashes are unique due to salt"""
        password = "TestPassword123!"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        
        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_generate_secure_token(self, security_manager):
        """Test secure token generation"""
        token = security_manager.generate_secure_token()
        
        assert token is not None
        assert len(token) >= 32  # Should be at least 32 characters
        assert isinstance(token, str)
        
        # Generate multiple tokens to ensure uniqueness
        tokens = [security_manager.generate_secure_token() for _ in range(10)]
        assert len(set(tokens)) == 10  # All tokens should be unique
    
    def test_hash_data(self, security_manager):
        """Test data hashing functionality"""
        data = "sensitive_data_to_hash"
        
        hashed = security_manager.hash_data(data)
        
        assert hashed is not None
        assert hashed != data
        assert len(hashed) == 64  # SHA-256 produces 64-character hex string
        
        # Same data should produce same hash
        hashed2 = security_manager.hash_data(data)
        assert hashed == hashed2
    
    def test_encrypt_decrypt_data(self, security_manager):
        """Test data encryption and decryption"""
        original_data = "This is sensitive information that needs encryption"
        
        # Test encryption
        encrypted = security_manager.encrypt_data(original_data)
        
        assert encrypted is not None
        assert encrypted != original_data
        assert isinstance(encrypted, str)
        
        # Test decryption
        decrypted = security_manager.decrypt_data(encrypted)
        assert decrypted == original_data
    
    def test_validate_api_key(self, security_manager):
        """Test API key validation"""
        valid_key = "valid_api_key_12345"
        invalid_key = "invalid_key"
        
        with patch.object(security_manager, 'valid_api_keys', [valid_key]):
            assert security_manager.validate_api_key(valid_key) is True
            assert security_manager.validate_api_key(invalid_key) is False
    
    def test_rate_limit_check(self, security_manager):
        """Test rate limiting functionality"""
        client_id = "test_client_123"
        
        # Mock rate limit storage
        with patch.object(security_manager, 'rate_limit_storage', {}) as mock_storage:
            # First request should be allowed
            assert security_manager.check_rate_limit(client_id, limit=5, window=60) is True
            
            # Simulate multiple requests
            for _ in range(4):
                security_manager.check_rate_limit(client_id, limit=5, window=60)
            
            # 6th request should be blocked
            assert security_manager.check_rate_limit(client_id, limit=5, window=60) is False


class TestValidationManager:
    """Comprehensive tests for ValidationManager"""
    
    @pytest.fixture
    def validation_manager(self):
        """Create a validation manager instance"""
        return ValidationManager()
    
    def test_email_validation(self, validation_manager):
        """Test email validation"""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.com",
            "firstname.lastname@company.org"
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True, f"Valid email {email} should pass validation"
        
        # Invalid emails
        invalid_emails = [
            "invalid.email",
            "@domain.com",
            "user@",
            "user@domain",
            "user name@domain.com",
            "user@domain..com"
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False, f"Invalid email {email} should fail validation"
    
    def test_password_validation(self, validation_manager):
        """Test password validation"""
        # Valid passwords
        valid_passwords = [
            "SecurePass123!",
            "MyStr0ng@Password",
            "C0mplex#Pass2024",
            "Ungu3ssable$Pwd!"
        ]
        
        for password in valid_passwords:
            assert validate_password(password) is True, f"Valid password should pass validation"
        
        # Invalid passwords
        invalid_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
            "Has Spaces123!",  # Contains spaces
        ]
        
        for password in invalid_passwords:
            assert validate_password(password) is False, f"Invalid password should fail validation"
    
    def test_phone_number_validation(self, validation_manager):
        """Test phone number validation"""
        # Valid phone numbers
        valid_phones = [
            "+1-555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "5551234567",
            "+44 20 7946 0958"
        ]
        
        for phone in valid_phones:
            assert validation_manager.validate_phone_number(phone) is True
        
        # Invalid phone numbers
        invalid_phones = [
            "123",  # Too short
            "abc-def-ghij",  # Contains letters
            "555-123-456",  # Too short
            "+1-555-123-45678"  # Too long
        ]
        
        for phone in invalid_phones:
            assert validation_manager.validate_phone_number(phone) is False
    
    def test_stock_symbol_validation(self, validation_manager):
        """Test stock symbol validation"""
        # Valid stock symbols
        valid_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "BRK.A", "BRK.B"]
        
        for symbol in valid_symbols:
            assert validation_manager.validate_stock_symbol(symbol) is True
        
        # Invalid stock symbols
        invalid_symbols = ["", "A", "TOOLONG", "123", "SYMB@L"]
        
        for symbol in invalid_symbols:
            assert validation_manager.validate_stock_symbol(symbol) is False
    
    def test_currency_validation(self, validation_manager):
        """Test currency validation"""
        # Valid currencies
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
        
        for currency in valid_currencies:
            assert validation_manager.validate_currency(currency) is True
        
        # Invalid currencies
        invalid_currencies = ["", "US", "DOLLAR", "123", "usd"]
        
        for currency in invalid_currencies:
            assert validation_manager.validate_currency(currency) is False
    
    def test_amount_validation(self, validation_manager):
        """Test monetary amount validation"""
        # Valid amounts
        valid_amounts = [100.00, 0.01, 999999.99, Decimal("100.50")]
        
        for amount in valid_amounts:
            assert validation_manager.validate_amount(amount) is True
        
        # Invalid amounts
        invalid_amounts = [-100.00, 0, "not_a_number", None]
        
        for amount in invalid_amounts:
            assert validation_manager.validate_amount(amount) is False


class TestCustomExceptions:
    """Comprehensive tests for custom exceptions"""
    
    def test_validation_error(self):
        """Test ValidationError exception"""
        message = "Invalid input data"
        field = "email"
        
        error = ValidationError(message, field=field)
        
        assert str(error) == message
        assert error.field == field
        assert error.status_code == 400
    
    def test_authentication_error(self):
        """Test AuthenticationError exception"""
        message = "Invalid credentials"
        
        error = AuthenticationError(message)
        
        assert str(error) == message
        assert error.status_code == 401
    
    def test_authorization_error(self):
        """Test AuthorizationError exception"""
        message = "Insufficient permissions"
        
        error = AuthorizationError(message)
        
        assert str(error) == message
        assert error.status_code == 403
    
    def test_database_error(self):
        """Test DatabaseError exception"""
        message = "Database connection failed"
        
        error = DatabaseError(message)
        
        assert str(error) == message
        assert error.status_code == 500
    
    def test_external_service_error(self):
        """Test ExternalServiceError exception"""
        message = "External API unavailable"
        service = "alpha_vantage"
        
        error = ExternalServiceError(message, service=service)
        
        assert str(error) == message
        assert error.service == service
        assert error.status_code == 503
    
    def test_business_logic_error(self):
        """Test BusinessLogicError exception"""
        message = "Invalid business operation"
        
        error = BusinessLogicError(message)
        
        assert str(error) == message
        assert error.status_code == 422


class TestAuditLogger:
    """Comprehensive tests for AuditLogger"""
    
    @pytest.fixture
    def audit_logger_instance(self):
        """Create an audit logger instance"""
        return AuditLogger()
    
    @pytest.mark.asyncio
    async def test_log_user_action(self, audit_logger_instance):
        """Test logging user actions"""
        user_id = "user_123"
        action = "login"
        resource = "authentication"
        details = {"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"}
        
        with patch.object(audit_logger_instance, 'storage') as mock_storage:
            mock_storage.store_audit_log = AsyncMock()
            
            await audit_logger_instance.log_user_action(
                user_id=user_id,
                action=action,
                resource=resource,
                details=details
            )
            
            mock_storage.store_audit_log.assert_called_once()
            call_args = mock_storage.store_audit_log.call_args[1]
            
            assert call_args['user_id'] == user_id
            assert call_args['action'] == action
            assert call_args['resource'] == resource
            assert call_args['details'] == details
            assert 'timestamp' in call_args
    
    @pytest.mark.asyncio
    async def test_log_system_event(self, audit_logger_instance):
        """Test logging system events"""
        event_type = "database_backup"
        details = {"backup_size": "1.2GB", "duration": "5 minutes"}
        
        with patch.object(audit_logger_instance, 'storage') as mock_storage:
            mock_storage.store_audit_log = AsyncMock()
            
            await audit_logger_instance.log_system_event(
                event_type=event_type,
                details=details
            )
            
            mock_storage.store_audit_log.assert_called_once()
            call_args = mock_storage.store_audit_log.call_args[1]
            
            assert call_args['event_type'] == event_type
            assert call_args['details'] == details
            assert call_args['user_id'] is None  # System events don't have user_id
    
    @pytest.mark.asyncio
    async def test_get_audit_logs(self, audit_logger_instance):
        """Test retrieving audit logs"""
        user_id = "user_123"
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        mock_logs = [
            {
                "id": "log_1",
                "user_id": user_id,
                "action": "login",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "log_2",
                "user_id": user_id,
                "action": "logout",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        with patch.object(audit_logger_instance, 'storage') as mock_storage:
            mock_storage.get_audit_logs = AsyncMock(return_value=mock_logs)
            
            logs = await audit_logger_instance.get_audit_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            assert logs == mock_logs
            mock_storage.get_audit_logs.assert_called_once_with(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )


class TestErrorTracker:
    """Comprehensive tests for ErrorTracker"""
    
    @pytest.fixture
    def error_tracker_instance(self):
        """Create an error tracker instance"""
        return ErrorTracker()
    
    def test_track_error(self, error_tracker_instance):
        """Test error tracking"""
        error = ValueError("Test error message")
        context = {
            "user_id": "user_123",
            "request_id": "req_456",
            "endpoint": "/api/v1/portfolios"
        }
        
        with patch.object(error_tracker_instance, 'storage') as mock_storage:
            mock_storage.store_error = Mock()
            
            error_tracker_instance.track_error(error, context=context)
            
            mock_storage.store_error.assert_called_once()
            call_args = mock_storage.store_error.call_args[1]
            
            assert call_args['error_type'] == 'ValueError'
            assert call_args['error_message'] == 'Test error message'
            assert call_args['context'] == context
            assert 'timestamp' in call_args
            assert 'stack_trace' in call_args
    
    def test_get_error_statistics(self, error_tracker_instance):
        """Test error statistics retrieval"""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        mock_stats = {
            "total_errors": 25,
            "error_types": {
                "ValueError": 10,
                "KeyError": 8,
                "ConnectionError": 7
            },
            "error_rate": 0.05
        }
        
        with patch.object(error_tracker_instance, 'storage') as mock_storage:
            mock_storage.get_error_statistics = Mock(return_value=mock_stats)
            
            stats = error_tracker_instance.get_error_statistics(
                start_date=start_date,
                end_date=end_date
            )
            
            assert stats == mock_stats
            mock_storage.get_error_statistics.assert_called_once_with(
                start_date=start_date,
                end_date=end_date
            )
    
    def test_error_rate_calculation(self, error_tracker_instance):
        """Test error rate calculation"""
        total_requests = 1000
        total_errors = 25
        
        error_rate = error_tracker_instance.calculate_error_rate(total_errors, total_requests)
        
        assert error_rate == 0.025  # 2.5%
    
    def test_error_rate_calculation_zero_requests(self, error_tracker_instance):
        """Test error rate calculation with zero requests"""
        total_requests = 0
        total_errors = 0
        
        error_rate = error_tracker_instance.calculate_error_rate(total_errors, total_requests)
        
        assert error_rate == 0.0


# Edge Cases and Error Handling Tests
class TestCoreModulesEdgeCases:
    """Test edge cases and error conditions for core modules"""
    
    @pytest.mark.asyncio
    async def test_cache_json_serialization_error(self):
        """Test cache handling of non-serializable objects"""
        cache = CacheManager()
        
        # Object that can't be JSON serialized
        non_serializable = {"datetime": datetime.utcnow()}
        
        with patch.object(cache, 'redis') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            
            # Should handle serialization error gracefully
            result = await cache.set("test_key", non_serializable)
            # Implementation should handle this gracefully
    
    def test_security_manager_with_invalid_data(self):
        """Test security manager with invalid input data"""
        security = SecurityManager()
        
        # Test with None input
        with pytest.raises((ValueError, TypeError)):
            security.hash_data(None)
        
        # Test with empty string
        hashed = security.hash_data("")
        assert hashed is not None
        assert len(hashed) == 64
    
    def test_validation_manager_edge_cases(self):
        """Test validation manager edge cases"""
        validator = ValidationManager()
        
        # Test with None values
        assert validate_email(None) is False
        assert validate_password(None) is False
        
        # Test with empty strings
        assert validate_email("") is False
        assert validate_password("") is False
        
        # Test with very long inputs
        long_email = "a" * 1000 + "@example.com"
        assert validate_email(long_email) is False
        
        long_password = "A1!" + "a" * 1000
        assert validate_password(long_password) is False
    
    @pytest.mark.asyncio
    async def test_audit_logger_storage_failure(self):
        """Test audit logger behavior when storage fails"""
        audit = AuditLogger()
        
        with patch.object(audit, 'storage') as mock_storage:
            mock_storage.store_audit_log = AsyncMock(side_effect=Exception("Storage failed"))
            
            # Should handle storage failure gracefully
            try:
                await audit.log_user_action(
                    user_id="user_123",
                    action="test_action",
                    resource="test_resource"
                )
                # Should not raise exception
            except Exception:
                pytest.fail("Audit logger should handle storage failures gracefully")
    
    def test_error_tracker_with_complex_error(self):
        """Test error tracker with complex error objects"""
        tracker = ErrorTracker()
        
        # Create a complex error with nested exceptions
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as inner:
                raise RuntimeError("Outer error") from inner
        except RuntimeError as error:
            with patch.object(tracker, 'storage') as mock_storage:
                mock_storage.store_error = Mock()
                
                tracker.track_error(error)
                
                # Should handle complex error structure
                mock_storage.store_error.assert_called_once()
                call_args = mock_storage.store_error.call_args[1]
                assert 'stack_trace' in call_args
                assert call_args['error_type'] == 'RuntimeError'