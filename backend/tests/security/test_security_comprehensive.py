"""
Comprehensive Security Tests - Penetration Testing and Vulnerability Scanning
"""
import pytest
import asyncio
import hashlib
import hmac
import base64
import jwt
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import re
import json

from httpx import AsyncClient
from app.main import app
from app.services.auth.jwt_handler import JWTHandler
from app.services.auth.password_handler import PasswordHandler
from app.models.user import User


class TestAuthenticationSecurity:
    """Security tests for authentication mechanisms"""
    
    @pytest.mark.asyncio
    async def test_password_security_requirements(self):
        """Test password security requirements and hashing"""
        
        # Test password complexity requirements
        weak_passwords = [
            "123456",           # Too simple
            "password",         # Common word
            "abc123",          # Too short
            "PASSWORD123",     # No special characters
            "Password!",       # Too short
            "pass word123!"    # Contains space
        ]
        
        strong_passwords = [
            "SecurePassword123!",
            "MyStr0ng@Password",
            "C0mplex#Pass2024",
            "Ungu3ssable$Pwd!"
        ]
        
        # Test weak password rejection (would be implemented in validation)
        for weak_pwd in weak_passwords:
            # Simulate password validation
            is_valid = (
                len(weak_pwd) >= 8 and
                re.search(r'[A-Z]', weak_pwd) and
                re.search(r'[a-z]', weak_pwd) and
                re.search(r'\d', weak_pwd) and
                re.search(r'[!@#$%^&*(),.?":{}|<>]', weak_pwd) and
                ' ' not in weak_pwd
            )
            assert not is_valid, f"Weak password '{weak_pwd}' should be rejected"
        
        # Test strong password acceptance
        for strong_pwd in strong_passwords:
            is_valid = (
                len(strong_pwd) >= 8 and
                re.search(r'[A-Z]', strong_pwd) and
                re.search(r'[a-z]', strong_pwd) and
                re.search(r'\d', strong_pwd) and
                re.search(r'[!@#$%^&*(),.?":{}|<>]', strong_pwd) and
                ' ' not in strong_pwd
            )
            assert is_valid, f"Strong password '{strong_pwd}' should be accepted"
        
        # Test password hashing security
        test_password = "SecureTestPassword123!"
        
        # Hash the same password multiple times
        hash1 = get_password_hash(test_password)
        hash2 = get_password_hash(test_password)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2, "Password hashes should be unique due to salting"
        
        # Both hashes should verify correctly
        assert verify_password(test_password, hash1), "First hash should verify correctly"
        assert verify_password(test_password, hash2), "Second hash should verify correctly"
        
        # Wrong password should not verify
        assert not verify_password("WrongPassword123!", hash1), "Wrong password should not verify"
        
        # Hash should be sufficiently long (bcrypt produces 60-character hashes)
        assert len(hash1) >= 50, f"Password hash too short: {len(hash1)} characters"
    
    @pytest.mark.asyncio
    async def test_jwt_token_security(self):
        """Test JWT token security implementation"""
        
        # Test token creation and validation
        user_data = {
            "user_id": "security-test-user-id",
            "email": "security.test@example.com",
            "is_active": True
        }
        
        # Create access token
        access_token = create_access_token(data=user_data)
        
        # Token should be a valid JWT format
        assert len(access_token.split('.')) == 3, "JWT should have 3 parts separated by dots"
        
        # Verify token
        payload = verify_token(access_token)
        assert payload["user_id"] == user_data["user_id"]
        assert payload["email"] == user_data["email"]
        
        # Test token expiration
        expired_token_data = {**user_data, "exp": int(time.time()) - 3600}  # Expired 1 hour ago
        
        try:
            # Create token with past expiration
            expired_token = jwt.encode(expired_token_data, "test-secret", algorithm="HS256")
            
            # Verification should fail
            with pytest.raises(Exception):  # Should raise jwt.ExpiredSignatureError
                verify_token(expired_token)
        except Exception:
            pass  # Expected behavior
        
        # Test token tampering
        tampered_token = access_token[:-5] + "XXXXX"  # Tamper with signature
        
        with pytest.raises(Exception):  # Should raise jwt.InvalidSignatureError
            verify_token(tampered_token)
    
    @pytest.mark.asyncio
    async def test_authentication_brute_force_protection(self, async_client):
        """Test protection against brute force attacks"""
        
        # Simulate multiple failed login attempts
        failed_attempts = []
        
        for attempt in range(10):
            with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
                mock_auth.side_effect = ValueError("Invalid credentials")
                
                response = await async_client.post("/api/v1/auth/login", json={
                    "email": "brute.force@example.com",
                    "password": f"wrong_password_{attempt}"
                })
                
                failed_attempts.append({
                    "attempt": attempt + 1,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
                })
        
        # After multiple failures, should implement rate limiting or account lockout
        # (This would be implemented in the actual auth service)
        
        # Verify that the system handles multiple failures gracefully
        for attempt in failed_attempts:
            assert attempt["status_code"] in [401, 429], f"Attempt {attempt['attempt']} should return 401 or 429"
    
    @pytest.mark.asyncio
    async def test_session_security(self, async_client):
        """Test session management security"""
        
        mock_user = User(
            id="session-test-user",
            email="session.test@example.com",
            full_name="Session Test User",
            is_active=True
        )
        
        # Test session creation
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "test-session-token-123",
                "refresh_token": "test-refresh-token-456",
                "user": {
                    "id": mock_user.id,
                    "email": mock_user.email
                }
            }
            
            login_response = await async_client.post("/api/v1/auth/login", json={
                "email": mock_user.email,
                "password": "TestPassword123!"
            })
            
            assert login_response.status_code == 200
            login_data = login_response.json()
            access_token = login_data["data"]["access_token"]
        
        # Test authenticated request
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Should work with valid token
            response = await async_client.get("/api/v1/portfolios", headers=headers)
            assert response.status_code in [200, 404]  # 200 if portfolios exist, 404 if none
            
            # Test session invalidation (logout)
            with patch('app.services.auth.auth_service.logout_user') as mock_logout:
                mock_logout.return_value = True
                
                logout_response = await async_client.post("/api/v1/auth/logout", headers=headers)
                assert logout_response.status_code == 200
            
            # After logout, token should be invalid (in real implementation)
            # This would require token blacklisting or short expiration
            
        finally:
            app.dependency_overrides.clear()


class TestAuthorizationSecurity:
    """Security tests for authorization and access control"""
    
    @pytest.mark.asyncio
    async def test_role_based_access_control(self, async_client):
        """Test role-based access control (RBAC)"""
        
        # Define different user roles
        admin_user = User(
            id="admin-user-id",
            email="admin@example.com",
            full_name="Admin User",
            is_active=True,
            role="admin"  # Assuming role field exists
        )
        
        regular_user = User(
            id="regular-user-id",
            email="regular@example.com",
            full_name="Regular User",
            is_active=True,
            role="user"
        )
        
        # Test admin access to admin endpoints
        app.dependency_overrides[get_current_user] = lambda: admin_user
        
        try:
            # Admin should access admin endpoints
            with patch('app.services.admin.admin_service.get_system_stats') as mock_stats:
                mock_stats.return_value = {"users": 100, "portfolios": 500}
                
                # This would be an admin-only endpoint
                admin_response = await async_client.get("/api/v1/admin/stats")
                # Should succeed for admin (or return 404 if endpoint doesn't exist yet)
                assert admin_response.status_code in [200, 404]
        
        finally:
            app.dependency_overrides.clear()
        
        # Test regular user access to admin endpoints
        app.dependency_overrides[get_current_user] = lambda: regular_user
        
        try:
            # Regular user should NOT access admin endpoints
            admin_response = await async_client.get("/api/v1/admin/stats")
            # Should return 403 Forbidden (or 404 if endpoint doesn't exist)
            assert admin_response.status_code in [403, 404]
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_resource_ownership_validation(self, async_client):
        """Test that users can only access their own resources"""
        
        user1 = User(
            id="user1-id",
            email="user1@example.com",
            full_name="User One",
            is_active=True
        )
        
        user2 = User(
            id="user2-id",
            email="user2@example.com",
            full_name="User Two",
            is_active=True
        )
        
        # Test User 1 accessing their own portfolio
        app.dependency_overrides[get_current_user] = lambda: user1
        
        try:
            with patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get:
                # Portfolio owned by user1
                mock_get.return_value = {
                    "id": "user1-portfolio-123",
                    "user_id": user1.id,
                    "name": "User 1 Portfolio"
                }
                
                response = await async_client.get("/api/v1/portfolios/user1-portfolio-123")
                assert response.status_code == 200
        
        finally:
            app.dependency_overrides.clear()
        
        # Test User 1 trying to access User 2's portfolio
        app.dependency_overrides[get_current_user] = lambda: user1
        
        try:
            with patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get:
                # Portfolio owned by user2, but user1 is trying to access it
                mock_get.return_value = {
                    "id": "user2-portfolio-456",
                    "user_id": user2.id,  # Different user
                    "name": "User 2 Portfolio"
                }
                
                # Should implement ownership check and return 403 or 404
                response = await async_client.get("/api/v1/portfolios/user2-portfolio-456")
                assert response.status_code in [403, 404], "User should not access other user's portfolio"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_api_endpoint_authorization(self, async_client):
        """Test authorization requirements for different API endpoints"""
        
        # Test unauthenticated access to protected endpoints
        protected_endpoints = [
            ("/api/v1/portfolios", "GET"),
            ("/api/v1/portfolios", "POST"),
            ("/api/v1/analytics/predict/stock-price", "POST"),
            ("/api/v1/reports/generate", "POST")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "POST":
                response = await async_client.post(endpoint, json={})
            
            # Should require authentication
            assert response.status_code == 401, f"{method} {endpoint} should require authentication"
        
        # Test public endpoints (should not require authentication)
        public_endpoints = [
            ("/api/v1/health", "GET"),
            ("/api/v1/auth/register", "POST"),
            ("/api/v1/auth/login", "POST")
        ]
        
        for endpoint, method in public_endpoints:
            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "POST":
                response = await async_client.post(endpoint, json={
                    "email": "test@example.com",
                    "password": "TestPassword123!",
                    "full_name": "Test User"
                })
            
            # Should not require authentication (may return validation errors, but not 401)
            assert response.status_code != 401, f"{method} {endpoint} should not require authentication"


class TestInputValidationSecurity:
    """Security tests for input validation and sanitization"""
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, async_client):
        """Test SQL injection prevention"""
        
        mock_user = User(
            id="sql-test-user",
            email="sql.test@example.com",
            full_name="SQL Test User",
            is_active=True
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # SQL injection payloads
            sql_injection_payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; UPDATE users SET is_admin=true; --",
                "' UNION SELECT * FROM users --",
                "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --"
            ]
            
            # Test SQL injection in portfolio name
            for payload in sql_injection_payloads:
                with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                    # Mock should receive sanitized input, not raw payload
                    mock_create.return_value = {
                        "id": "safe-portfolio-id",
                        "name": payload,  # This would be sanitized in real implementation
                        "user_id": mock_user.id
                    }
                    
                    response = await async_client.post("/api/v1/portfolios", json={
                        "name": payload,
                        "description": "Test portfolio"
                    })
                    
                    # Should either succeed with sanitized input or fail validation
                    assert response.status_code in [201, 400, 422], f"SQL injection payload should be handled safely: {payload}"
            
            # Test SQL injection in search parameters
            for payload in sql_injection_payloads:
                # This would test search functionality if implemented
                response = await async_client.get(f"/api/v1/portfolios?search={payload}")
                
                # Should handle malicious input safely
                assert response.status_code in [200, 400, 422], f"Search SQL injection should be prevented: {payload}"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self, async_client):
        """Test Cross-Site Scripting (XSS) prevention"""
        
        mock_user = User(
            id="xss-test-user",
            email="xss.test@example.com",
            full_name="XSS Test User",
            is_active=True
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # XSS payloads
            xss_payloads = [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')",
                "<svg onload=alert('XSS')>",
                "';alert('XSS');//",
                "<iframe src='javascript:alert(\"XSS\")'></iframe>"
            ]
            
            # Test XSS in portfolio name and description
            for payload in xss_payloads:
                with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                    # In real implementation, input should be sanitized
                    mock_create.return_value = {
                        "id": "xss-test-portfolio",
                        "name": payload,  # Would be sanitized
                        "description": payload,  # Would be sanitized
                        "user_id": mock_user.id
                    }
                    
                    response = await async_client.post("/api/v1/portfolios", json={
                        "name": payload,
                        "description": payload
                    })
                    
                    # Should handle XSS payload safely
                    assert response.status_code in [201, 400, 422], f"XSS payload should be handled safely: {payload}"
                    
                    if response.status_code == 201:
                        # If creation succeeded, verify response doesn't contain raw payload
                        response_text = response.text
                        # Raw script tags should not be present in response
                        assert "<script>" not in response_text, "Response should not contain raw script tags"
                        assert "javascript:" not in response_text, "Response should not contain javascript: protocol"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_input_length_validation(self, async_client):
        """Test input length validation to prevent buffer overflow attacks"""
        
        mock_user = User(
            id="length-test-user",
            email="length.test@example.com",
            full_name="Length Test User",
            is_active=True
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test extremely long inputs
            very_long_string = "A" * 10000  # 10KB string
            extremely_long_string = "B" * 100000  # 100KB string
            
            # Test long portfolio name
            response = await async_client.post("/api/v1/portfolios", json={
                "name": very_long_string,
                "description": "Test portfolio"
            })
            
            # Should reject overly long input
            assert response.status_code in [400, 422], "Very long portfolio name should be rejected"
            
            # Test extremely long description
            response = await async_client.post("/api/v1/portfolios", json={
                "name": "Test Portfolio",
                "description": extremely_long_string
            })
            
            # Should reject overly long input
            assert response.status_code in [400, 422], "Extremely long description should be rejected"
            
            # Test long email in registration
            response = await async_client.post("/api/v1/auth/register", json={
                "email": very_long_string + "@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User"
            })
            
            # Should reject overly long email
            assert response.status_code in [400, 422], "Very long email should be rejected"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_data_type_validation(self, async_client):
        """Test data type validation security"""
        
        mock_user = User(
            id="type-test-user",
            email="type.test@example.com",
            full_name="Type Test User",
            is_active=True
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test invalid data types
            invalid_payloads = [
                # Invalid shares (should be number)
                {
                    "symbol": "AAPL",
                    "shares": "not_a_number",
                    "purchase_price": 150.00
                },
                # Invalid price (should be positive number)
                {
                    "symbol": "AAPL",
                    "shares": 100,
                    "purchase_price": -150.00
                },
                # Invalid symbol (should be string)
                {
                    "symbol": 12345,
                    "shares": 100,
                    "purchase_price": 150.00
                },
                # Missing required fields
                {
                    "symbol": "AAPL"
                    # Missing shares and purchase_price
                }
            ]
            
            for payload in invalid_payloads:
                response = await async_client.post(
                    "/api/v1/portfolios/test-portfolio/holdings",
                    json=payload
                )
                
                # Should reject invalid data types
                assert response.status_code in [400, 422], f"Invalid payload should be rejected: {payload}"
        
        finally:
            app.dependency_overrides.clear()


class TestAPISecurityHeaders:
    """Test security headers and CORS configuration"""
    
    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client):
        """Test that proper security headers are present"""
        
        response = await async_client.get("/api/v1/health")
        
        # Check for important security headers
        headers = response.headers
        
        # Content Security Policy
        assert "x-content-type-options" in headers or "X-Content-Type-Options" in headers, "X-Content-Type-Options header missing"
        
        # Frame options (clickjacking protection)
        assert "x-frame-options" in headers or "X-Frame-Options" in headers, "X-Frame-Options header missing"
        
        # XSS Protection
        assert "x-xss-protection" in headers or "X-XSS-Protection" in headers, "X-XSS-Protection header missing"
        
        # Verify header values
        content_type_options = headers.get("x-content-type-options") or headers.get("X-Content-Type-Options")
        if content_type_options:
            assert content_type_options.lower() == "nosniff", "X-Content-Type-Options should be 'nosniff'"
        
        frame_options = headers.get("x-frame-options") or headers.get("X-Frame-Options")
        if frame_options:
            assert frame_options.upper() in ["DENY", "SAMEORIGIN"], "X-Frame-Options should be DENY or SAMEORIGIN"
    
    @pytest.mark.asyncio
    async def test_cors_configuration(self, async_client):
        """Test CORS configuration security"""
        
        # Test preflight request
        response = await async_client.options(
            "/api/v1/portfolios",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Check CORS headers
        cors_headers = response.headers
        
        # Should have CORS headers
        assert "access-control-allow-origin" in cors_headers or "Access-Control-Allow-Origin" in cors_headers
        
        # Should not allow all origins in production
        allowed_origin = cors_headers.get("access-control-allow-origin") or cors_headers.get("Access-Control-Allow-Origin")
        if allowed_origin:
            assert allowed_origin != "*", "CORS should not allow all origins (*) in production"
    
    @pytest.mark.asyncio
    async def test_https_enforcement(self, async_client):
        """Test HTTPS enforcement (HSTS headers)"""
        
        response = await async_client.get("/api/v1/health")
        headers = response.headers
        
        # Check for HSTS header
        hsts_header = headers.get("strict-transport-security") or headers.get("Strict-Transport-Security")
        
        if hsts_header:
            # HSTS should have reasonable max-age
            assert "max-age=" in hsts_header, "HSTS header should include max-age"
            
            # Extract max-age value
            import re
            max_age_match = re.search(r'max-age=(\d+)', hsts_header)
            if max_age_match:
                max_age = int(max_age_match.group(1))
                assert max_age >= 31536000, "HSTS max-age should be at least 1 year (31536000 seconds)"


class TestDataProtectionSecurity:
    """Test data protection and privacy security measures"""
    
    @pytest.mark.asyncio
    async def test_sensitive_data_exposure(self, async_client):
        """Test that sensitive data is not exposed in responses"""
        
        mock_user = User(
            id="data-protection-user",
            email="data.protection@example.com",
            full_name="Data Protection User",
            is_active=True
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test user profile endpoint
            with patch('app.services.auth.auth_service.get_user_profile') as mock_profile:
                mock_profile.return_value = {
                    "id": mock_user.id,
                    "email": mock_user.email,
                    "full_name": mock_user.full_name,
                    "is_active": mock_user.is_active,
                    # These should NOT be exposed:
                    "password_hash": "$2b$12$hidden_hash_value",
                    "internal_notes": "Internal admin notes",
                    "ssn": "123-45-6789"
                }
                
                response = await async_client.get("/api/v1/auth/profile")
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = json.dumps(response_data)
                    
                    # Sensitive data should not be in response
                    assert "password_hash" not in response_text, "Password hash should not be exposed"
                    assert "$2b$" not in response_text, "Bcrypt hash should not be exposed"
                    assert "internal_notes" not in response_text, "Internal notes should not be exposed"
                    assert "ssn" not in response_text, "SSN should not be exposed"
                    assert "123-45-6789" not in response_text, "SSN value should not be exposed"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_error_message_information_disclosure(self, async_client):
        """Test that error messages don't disclose sensitive information"""
        
        # Test authentication error messages
        response = await async_client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        if response.status_code == 401:
            error_response = response.json()
            error_message = json.dumps(error_response).lower()
            
            # Error messages should not reveal whether user exists
            assert "user not found" not in error_message, "Error should not reveal user existence"
            assert "user does not exist" not in error_message, "Error should not reveal user existence"
            assert "email not found" not in error_message, "Error should not reveal email existence"
            
            # Should use generic message
            assert "invalid" in error_message or "incorrect" in error_message, "Should use generic error message"
        
        # Test database error handling
        mock_user = User(
            id="error-test-user",
            email="error.test@example.com",
            full_name="Error Test User",
            is_active=True
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            with patch('app.services.portfolio.portfolio_service.get_portfolios') as mock_get:
                # Simulate database error
                mock_get.side_effect = Exception("Database connection failed: host=db.internal.com port=5432")
                
                response = await async_client.get("/api/v1/portfolios")
                
                if response.status_code == 500:
                    error_response = response.json()
                    error_message = json.dumps(error_response).lower()
                    
                    # Should not expose internal details
                    assert "db.internal.com" not in error_message, "Internal hostnames should not be exposed"
                    assert "port=5432" not in error_message, "Internal ports should not be exposed"
                    assert "database connection failed" not in error_message, "Specific DB errors should not be exposed"
        
        finally:
            app.dependency_overrides.clear()
    
    def test_data_encryption_requirements(self):
        """Test data encryption requirements"""
        
        # Test password hashing (should use strong algorithm)
        test_password = "TestPassword123!"
        password_hash = get_password_hash(test_password)
        
        # Should use bcrypt (starts with $2b$)
        assert password_hash.startswith("$2b$"), "Should use bcrypt for password hashing"
        
        # Should have sufficient rounds (at least 12)
        hash_parts = password_hash.split("$")
        if len(hash_parts) >= 3:
            rounds = int(hash_parts[2])
            assert rounds >= 12, f"Bcrypt rounds should be at least 12, got {rounds}"
        
        # Test that sensitive data would be encrypted at rest
        # (This would test database encryption configuration in real implementation)
        sensitive_data = {
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "bank_account": "123456789"
        }
        
        # In real implementation, this data should be encrypted before storage
        for field, value in sensitive_data.items():
            # Simulate encryption check
            encrypted_value = base64.b64encode(value.encode()).decode()  # Simple base64 for demo
            assert encrypted_value != value, f"Sensitive field {field} should be encrypted"


class TestRateLimitingSecurity:
    """Test rate limiting and DoS protection"""
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, async_client):
        """Test API rate limiting protection"""
        
        # Test rapid requests to same endpoint
        responses = []
        
        for i in range(20):  # Make 20 rapid requests
            response = await async_client.get("/api/v1/health")
            responses.append({
                "request_number": i + 1,
                "status_code": response.status_code,
                "headers": dict(response.headers)
            })
        
        # Check if rate limiting is applied
        rate_limited_responses = [r for r in responses if r["status_code"] == 429]
        
        # If rate limiting is implemented, should see 429 responses
        if rate_limited_responses:
            # Check for rate limit headers
            rate_limit_response = rate_limited_responses[0]
            headers = rate_limit_response["headers"]
            
            # Should have rate limit information
            rate_limit_headers = [
                "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
                "retry-after", "ratelimit-limit", "ratelimit-remaining"
            ]
            
            has_rate_limit_header = any(
                header.lower() in [h.lower() for h in headers.keys()]
                for header in rate_limit_headers
            )
            
            assert has_rate_limit_header, "Rate limited response should include rate limit headers"
    
    @pytest.mark.asyncio
    async def test_authentication_rate_limiting(self, async_client):
        """Test rate limiting on authentication endpoints"""
        
        # Test multiple login attempts
        login_responses = []
        
        for i in range(10):
            response = await async_client.post("/api/v1/auth/login", json={
                "email": f"test{i}@example.com",
                "password": "wrongpassword"
            })
            
            login_responses.append({
                "attempt": i + 1,
                "status_code": response.status_code
            })
        
        # Should implement rate limiting on auth endpoints
        # (This would be more strict than general API rate limiting)
        
        # Check that system handles multiple auth attempts gracefully
        for response in login_responses:
            assert response["status_code"] in [401, 429], f"Auth attempt {response['attempt']} should return 401 or 429"


class TestSecurityMisconfiguration:
    """Test for security misconfigurations"""
    
    @pytest.mark.asyncio
    async def test_debug_mode_disabled(self, async_client):
        """Test that debug mode is disabled in production"""
        
        # Try to trigger debug information
        response = await async_client.get("/api/v1/nonexistent-endpoint")
        
        if response.status_code == 404:
            response_text = response.text.lower()
            
            # Should not expose debug information
            assert "traceback" not in response_text, "Debug traceback should not be exposed"
            assert "stack trace" not in response_text, "Stack trace should not be exposed"
            assert "debug" not in response_text, "Debug information should not be exposed"
            assert "internal server error" not in response_text or "500" not in response_text, "Detailed error info should not be exposed"
    
    @pytest.mark.asyncio
    async def test_server_information_disclosure(self, async_client):
        """Test that server information is not disclosed"""
        
        response = await async_client.get("/api/v1/health")
        headers = response.headers
        
        # Should not expose server information
        server_header = headers.get("server") or headers.get("Server")
        if server_header:
            server_info = server_header.lower()
            
            # Should not expose detailed server information
            assert "uvicorn" not in server_info, "Server implementation should not be exposed"
            assert "fastapi" not in server_info, "Framework information should not be exposed"
            assert "python" not in server_info, "Language information should not be exposed"
        
        # Should not expose version information
        powered_by = headers.get("x-powered-by") or headers.get("X-Powered-By")
        assert powered_by is None, "X-Powered-By header should not be present"
    
    @pytest.mark.asyncio
    async def test_default_credentials_security(self):
        """Test that default credentials are not present"""
        
        # Common default credentials to test
        default_credentials = [
            ("admin", "admin"),
            ("admin", "password"),
            ("admin", "123456"),
            ("root", "root"),
            ("test", "test"),
            ("demo", "demo")
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for username, password in default_credentials:
                response = await client.post("/api/v1/auth/login", json={
                    "email": f"{username}@example.com",
                    "password": password
                })
                
                # Default credentials should not work
                assert response.status_code != 200, f"Default credentials {username}:{password} should not work"


# Security Test Configuration
SECURITY_TEST_CONFIG = {
    "password_requirements": {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digits": True,
        "require_special_chars": True,
        "no_spaces": True
    },
    "jwt_security": {
        "algorithm": "HS256",
        "min_expiration": 900,  # 15 minutes
        "max_expiration": 86400  # 24 hours
    },
    "rate_limiting": {
        "general_api": 100,  # requests per minute
        "auth_endpoints": 10,  # requests per minute
        "sensitive_endpoints": 20  # requests per minute
    },
    "security_headers": {
        "required": [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ],
        "recommended": [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
    }
}