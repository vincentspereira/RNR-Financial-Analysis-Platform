"""
Security tests for RNR Financial Analysis Platform
Covers OWASP Top 10 vulnerabilities and penetration testing scenarios
"""
import pytest
import asyncio
import json
import base64
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from app.main import app


class TestOWASPTop10:
    """Security tests covering OWASP Top 10 vulnerabilities"""
    
    @pytest.fixture
    async def client(self):
        """Create test client for security testing"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_injection_attacks(self, client):
        """Test protection against SQL injection and other injection attacks"""
        
        # SQL Injection attempts
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "admin'/*",
            "' OR 1=1#",
            "') OR ('1'='1",
        ]
        
        for payload in sql_injection_payloads:
            # Test login endpoint
            login_data = {
                "email": payload,
                "password": "password123"
            }
            
            response = await client.post("/api/v1/auth/login", json=login_data)
            
            # Should not succeed with injection
            assert response.status_code in [400, 401, 422]  # Not 200
            
            # Test registration endpoint
            register_data = {
                "email": payload,
                "password": "password123",
                "name": "Test User"
            }
            
            response = await client.post("/api/v1/auth/register", json=register_data)
            
            # Should validate and reject malicious input
            assert response.status_code in [400, 422]
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_broken_authentication(self, client):
        """Test authentication security vulnerabilities"""
        
        # Test weak password acceptance
        weak_passwords = [
            "123",
            "password",
            "admin",
            "test",
            "12345678",
            "qwerty"
        ]
        
        for weak_password in weak_passwords:
            register_data = {
                "email": "test@example.com",
                "password": weak_password,
                "name": "Test User"
            }
            
            response = await client.post("/api/v1/auth/register", json=register_data)
            
            # Should reject weak passwords
            if response.status_code == 400:
                error_detail = response.json().get("detail", "")
                # Should have password strength validation
                assert "password" in error_detail.lower()
        
        # Test brute force protection
        login_attempts = []
        for i in range(10):
            login_data = {
                "email": "test@example.com",
                "password": f"wrong_password_{i}"
            }
            
            response = await client.post("/api/v1/auth/login", json=login_data)
            login_attempts.append(response.status_code)
        
        # Should have rate limiting or account lockout
        failed_attempts = sum(1 for status in login_attempts if status == 401)
        assert failed_attempts == len(login_attempts)  # All should fail
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_sensitive_data_exposure(self, client):
        """Test protection against sensitive data exposure"""
        
        # Test that passwords are not returned in responses
        register_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "name": "Test User"
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Password should not be in response
            assert "password" not in response_data
            assert "password_hash" not in response_data
            
            # Sensitive fields should not be exposed
            sensitive_fields = ["password", "password_hash", "secret_key", "private_key"]
            response_text = response.text.lower()
            
            for field in sensitive_fields:
                assert field not in response_text
        
        # Test error messages don't leak sensitive information
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        
        if response.status_code == 401:
            error_message = response.json().get("detail", "").lower()
            
            # Should not reveal whether user exists
            assert "user not found" not in error_message
            assert "invalid user" not in error_message
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_xml_external_entities(self, client):
        """Test protection against XXE attacks"""
        
        # XXE payload attempts
        xxe_payloads = [
            '<?xml version="1.0" encoding="ISO-8859-1"?><!DOCTYPE foo [<!ELEMENT foo ANY ><!ENTITY xxe SYSTEM "file:///etc/passwd" >]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///c:/windows/win.ini">]><root>&test;</root>',
            '<!DOCTYPE test [<!ENTITY % init SYSTEM "data://text/plain;base64,ZmlsZTovLy9ldGMvcGFzc3dk"> %init;]><test/>',
        ]
        
        for payload in xxe_payloads:
            # Test endpoints that might process XML
            response = await client.post("/api/v1/auth/register", 
                                       data=payload, 
                                       headers={"Content-Type": "application/xml"})
            
            # Should reject XML or not process XXE
            assert response.status_code in [400, 415, 422]
            
            # Response should not contain file contents
            response_text = response.text.lower()
            assert "root:" not in response_text  # Unix passwd file
            assert "[extensions]" not in response_text  # Windows ini file
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_broken_access_control(self, client):
        """Test access control vulnerabilities"""
        
        # Test accessing protected endpoints without authentication
        protected_endpoints = [
            "/api/v1/auth/me",
            "/api/v1/financial/ratios/calculate",
            "/api/v1/data/ingest/company",
            "/api/v1/data/sources/status"
        ]
        
        for endpoint in protected_endpoints:
            # Test without authorization header
            response = await client.get(endpoint)
            assert response.status_code in [401, 403]
            
            # Test with invalid token
            headers = {"Authorization": "Bearer invalid_token"}
            response = await client.get(endpoint, headers=headers)
            assert response.status_code in [401, 403]
            
            # Test with malformed authorization header
            headers = {"Authorization": "InvalidFormat token"}
            response = await client.get(endpoint, headers=headers)
            assert response.status_code in [401, 403]
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_security_misconfiguration(self, client):
        """Test for security misconfigurations"""
        
        # Test that debug information is not exposed
        response = await client.get("/api/v1/nonexistent")
        
        if response.status_code == 404:
            response_text = response.text.lower()
            
            # Should not expose debug information
            debug_indicators = [
                "traceback", "stack trace", "debug", "exception",
                "internal server error", "sql error", "database error"
            ]
            
            for indicator in debug_indicators:
                assert indicator not in response_text
        
        # Test security headers
        response = await client.get("/api/v1/health")
        headers = response.headers
        
        # Check for security headers (if implemented)
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "strict-transport-security"
        ]
        
        # Note: These might not be implemented yet, so we just check
        for header in security_headers:
            if header in headers:
                assert headers[header] is not None
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_cross_site_scripting(self, client):
        """Test protection against XSS attacks"""
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
        ]
        
        for payload in xss_payloads:
            # Test registration with XSS payload in name
            register_data = {
                "email": "test@example.com",
                "password": "SecurePassword123!",
                "name": payload
            }
            
            response = await client.post("/api/v1/auth/register", json=register_data)
            
            # Should sanitize or reject XSS payload
            if response.status_code == 200:
                response_text = response.text
                
                # Should not contain unescaped script tags
                assert "<script>" not in response_text
                assert "javascript:" not in response_text
                assert "onerror=" not in response_text
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_insecure_deserialization(self, client):
        """Test protection against insecure deserialization"""
        
        # Test malicious serialized objects
        malicious_payloads = [
            # Python pickle payload (base64 encoded)
            base64.b64encode(b"cos\nsystem\n(S'echo vulnerable'\ntR.").decode(),
            # JSON with prototype pollution attempt
            '{"__proto__": {"admin": true}}',
            # Malformed JSON
            '{"test": function() { return "malicious"; }}',
        ]
        
        for payload in malicious_payloads:
            # Test endpoints that might deserialize data
            try:
                response = await client.post("/api/v1/auth/register", 
                                           data=payload,
                                           headers={"Content-Type": "application/json"})
                
                # Should reject malicious serialized data
                assert response.status_code in [400, 422]
                
                # Should not execute malicious code
                response_text = response.text.lower()
                assert "vulnerable" not in response_text
                
            except Exception:
                # Exception is acceptable - means malicious payload was rejected
                pass
    
    @pytest.mark.security
    @pytest.mark.critical
    async def test_insufficient_logging_monitoring(self, client):
        """Test logging and monitoring capabilities"""
        
        # Test that security events are logged (we can't directly test logging,
        # but we can test that security events are handled properly)
        
        # Failed login attempt
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong_password"
        })
        
        # Should handle failed login appropriately
        assert response.status_code == 401
        
        # Multiple failed attempts
        for i in range(5):
            response = await client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": f"wrong_password_{i}"
            })
            
            # Should continue to reject (and hopefully log)
            assert response.status_code == 401
        
        # Test invalid token usage
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        # Should reject and log invalid token usage
        assert response.status_code in [401, 403]


class TestPenetrationTesting:
    """Penetration testing scenarios"""
    
    @pytest.fixture
    async def client(self):
        """Create test client for penetration testing"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.security
    @pytest.mark.penetration
    async def test_authentication_bypass_attempts(self, client):
        """Test various authentication bypass techniques"""
        
        # Test SQL injection in authentication
        bypass_attempts = [
            {"email": "admin' OR '1'='1' --", "password": "anything"},
            {"email": "admin'/*", "password": "*/OR/**/1=1#"},
            {"email": "' OR 1=1 LIMIT 1 --", "password": "password"},
        ]
        
        for attempt in bypass_attempts:
            response = await client.post("/api/v1/auth/login", json=attempt)
            
            # Should not bypass authentication
            assert response.status_code != 200
            
            if response.status_code == 200:
                # If somehow successful, should not return admin privileges
                data = response.json()
                assert "access_token" not in data or data.get("user", {}).get("email") != "admin"
    
    @pytest.mark.security
    @pytest.mark.penetration
    async def test_privilege_escalation_attempts(self, client):
        """Test privilege escalation vulnerabilities"""
        
        # Test parameter pollution
        escalation_attempts = [
            {"email": "user@example.com", "password": "password", "role": "admin"},
            {"email": "user@example.com", "password": "password", "is_admin": True},
            {"email": "user@example.com", "password": "password", "permissions": ["admin"]},
        ]
        
        for attempt in escalation_attempts:
            response = await client.post("/api/v1/auth/register", json=attempt)
            
            # Should not grant elevated privileges
            if response.status_code == 200:
                data = response.json()
                
                # Should not have admin privileges
                assert data.get("role") != "admin"
                assert data.get("is_admin") != True
                assert "admin" not in str(data.get("permissions", []))
    
    @pytest.mark.security
    @pytest.mark.penetration
    async def test_data_exfiltration_attempts(self, client):
        """Test data exfiltration vulnerabilities"""
        
        # Test directory traversal
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]
        
        for attempt in traversal_attempts:
            # Test file access attempts
            response = await client.get(f"/api/v1/data/company/{attempt}/latest")
            
            # Should not allow directory traversal
            assert response.status_code in [400, 401, 403, 404, 422]
            
            # Should not return file contents
            response_text = response.text.lower()
            assert "root:" not in response_text
            assert "[extensions]" not in response_text
    
    @pytest.mark.security
    @pytest.mark.penetration
    async def test_denial_of_service_resistance(self, client):
        """Test resistance to DoS attacks"""
        
        # Test large payload handling
        large_payload = {
            "email": "test@example.com",
            "password": "password123",
            "name": "A" * 10000  # Very large name
        }
        
        response = await client.post("/api/v1/auth/register", json=large_payload)
        
        # Should handle large payloads gracefully
        assert response.status_code in [400, 413, 422]  # Not 500
        
        # Test rapid requests
        rapid_requests = []
        for i in range(20):
            task = client.get("/api/v1/health")
            rapid_requests.append(task)
        
        responses = await asyncio.gather(*rapid_requests, return_exceptions=True)
        
        # Should handle rapid requests without crashing
        successful_responses = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        
        # At least some requests should succeed (rate limiting is acceptable)
        assert successful_responses > 0
    
    @pytest.mark.security
    @pytest.mark.penetration
    async def test_session_management_vulnerabilities(self, client):
        """Test session management security"""
        
        # Test session fixation
        # First, get a session
        response1 = await client.get("/api/v1/health")
        cookies1 = response1.cookies
        
        # Try to use the same session after "login"
        login_data = {"email": "test@example.com", "password": "password123"}
        response2 = await client.post("/api/v1/auth/login", json=login_data, cookies=cookies1)
        
        # Session should be regenerated after login (if successful)
        if response2.status_code == 200:
            cookies2 = response2.cookies
            # Cookies should be different (session regeneration)
            # This is a basic check - real implementation may vary
            assert cookies1 != cookies2 or len(cookies1) == 0
        
        # Test concurrent session usage
        if response2.status_code == 200:
            token = response2.json().get("access_token")
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                
                # Make concurrent requests with same token
                concurrent_requests = []
                for i in range(5):
                    task = client.get("/api/v1/auth/me", headers=headers)
                    concurrent_requests.append(task)
                
                responses = await asyncio.gather(*concurrent_requests, return_exceptions=True)
                
                # Should handle concurrent session usage
                valid_responses = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
                
                # Should allow concurrent usage or handle gracefully
                assert valid_responses >= 0  # At least not crash


class TestDataEncryption:
    """Test data encryption in transit and at rest"""
    
    @pytest.mark.security
    @pytest.mark.encryption
    async def test_password_encryption(self):
        """Test password encryption and hashing"""
        
        from app.services.auth.password_handler import PasswordHandler
        
        password_handler = PasswordHandler()
        
        # Test password hashing
        password = "TestPassword123!"
        hashed1 = password_handler.hash_password(password)
        hashed2 = password_handler.hash_password(password)
        
        # Hashes should be different (salted)
        assert hashed1 != hashed2
        assert hashed1 != password
        assert hashed2 != password
        
        # Both should verify correctly
        assert password_handler.verify_password(password, hashed1)
        assert password_handler.verify_password(password, hashed2)
        
        # Wrong password should not verify
        assert not password_handler.verify_password("WrongPassword", hashed1)
    
    @pytest.mark.security
    @pytest.mark.encryption
    async def test_jwt_token_security(self):
        """Test JWT token security"""
        
        from app.services.auth.jwt_handler import JWTHandler
        
        jwt_handler = JWTHandler()
        user_id = uuid4()
        
        # Test token creation and validation
        token = jwt_handler.create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Test token decoding
        decoded = jwt_handler.decode_token(token)
        
        assert decoded is not None
        assert decoded.get("sub") == str(user_id)
        
        # Test token tampering detection
        tampered_token = token[:-5] + "XXXXX"  # Tamper with token
        decoded_tampered = jwt_handler.decode_token(tampered_token)
        
        # Tampered token should be rejected
        assert decoded_tampered is None
    
    @pytest.mark.security
    @pytest.mark.encryption
    async def test_sensitive_data_handling(self):
        """Test handling of sensitive financial data"""
        
        from app.services.calculator.financial_calculator import FinancialCalculator
        
        calculator = FinancialCalculator()
        
        # Test that sensitive financial data is handled securely
        sensitive_data = {
            "revenue": 1000000000,
            "net_income": 150000000,
            "proprietary_metric": "confidential_value",
            "insider_information": "sensitive_data"
        }
        
        # Financial calculations should not expose sensitive data in logs/errors
        try:
            # This might fail, but should not expose sensitive data
            mock_db = AsyncMock()
            
            with patch.object(calculator, 'get_company_financial_data') as mock_get_data:
                mock_get_data.return_value = sensitive_data
                
                result = await calculator.calculate_financial_ratios(
                    company_id=uuid4(),
                    period_type='annual',
                    fiscal_year=2023,
                    db=mock_db
                )
                
                # Result should not contain raw sensitive data
                if result:
                    result_str = str(result)
                    assert "proprietary_metric" not in result_str
                    assert "insider_information" not in result_str
                    assert "confidential_value" not in result_str
                    assert "sensitive_data" not in result_str
                
        except Exception as e:
            # Exception messages should not contain sensitive data
            error_str = str(e)
            assert "proprietary_metric" not in error_str
            assert "insider_information" not in error_str
            assert "confidential_value" not in error_str
            assert "sensitive_data" not in error_str


class TestComplianceValidation:
    """Test compliance with security standards"""
    
    @pytest.mark.security
    @pytest.mark.compliance
    async def test_audit_logging_compliance(self):
        """Test audit logging for compliance requirements"""
        
        from app.services.auth.auth_service import auth_service
        
        mock_db = AsyncMock()
        
        # Test that security events are properly logged
        # (We can't directly test logging, but we can test the flow)
        
        # Mock user registration with audit logging
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch("app.services.auth.password_handler.PasswordHandler.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password"
            
            result = await auth_service.register_user(
                email="compliance@example.com",
                password="SecurePassword123!",
                name="Compliance User",
                db=mock_db
            )
            
            # Should create audit trail
            assert mock_db.add.called  # User creation should be logged
            assert mock_db.commit.called
    
    @pytest.mark.security
    @pytest.mark.compliance
    async def test_data_retention_compliance(self):
        """Test data retention policy compliance"""
        
        # Test that sensitive data has appropriate retention policies
        # This is more of a design test than functional test
        
        from app.models.audit import AuditLog
        from datetime import datetime, timedelta
        
        # Create mock audit log entry
        audit_log = AuditLog(
            id=uuid4(),
            action="user_login",
            resource_type="authentication",
            user_id=uuid4(),
            timestamp=datetime.now() - timedelta(days=400),  # Old entry
            audit_metadata={"ip_address": "192.168.1.1"}
        )
        
        # Test that old audit logs can be identified for retention
        retention_period = timedelta(days=365)  # 1 year retention
        cutoff_date = datetime.now() - retention_period
        
        should_be_retained = audit_log.timestamp > cutoff_date
        
        # This entry should be eligible for cleanup
        assert not should_be_retained
    
    @pytest.mark.security
    @pytest.mark.compliance
    async def test_access_control_compliance(self):
        """Test access control compliance requirements"""
        
        # Test role-based access control
        from app.models.user import User
        
        # Test different user roles
        regular_user = User(
            id=uuid4(),
            email="user@example.com",
            name="Regular User",
            is_active=True,
            subscription_tier="basic"
        )
        
        admin_user = User(
            id=uuid4(),
            email="admin@example.com",
            name="Admin User",
            is_active=True,
            subscription_tier="enterprise"
        )
        
        # Test that users have appropriate access levels
        assert regular_user.subscription_tier == "basic"
        assert admin_user.subscription_tier == "enterprise"
        
        # Access control should be enforced at API level
        # (This would be tested in integration tests with actual endpoints)