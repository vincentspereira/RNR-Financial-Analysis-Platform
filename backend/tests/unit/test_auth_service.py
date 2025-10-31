"""
Unit tests for Authentication Service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from app.services.auth.auth_service import AuthService
from app.services.auth.password_handler import PasswordHandler
from app.services.auth.jwt_handler import JWTHandler
from app.models.user import User, UserSession


class TestAuthService:
    """Unit tests for AuthService class"""
    
    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance for testing"""
        return AuthService()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing"""
        return User(
            id=uuid4(),
            email='test@example.com',
            name='Test User',
            password_hash='hashed_password',
            is_active=True,
            is_verified=False,
            subscription_tier='basic'
        )
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_register_user_success(self, auth_service, mock_db):
        """Test successful user registration"""
        # Mock that user doesn't exist
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch.object(PasswordHandler, 'hash_password') as mock_hash:
            mock_hash.return_value = 'hashed_password'
            
            result = await auth_service.register_user(
                email='test@example.com',
                password='password123',
                name='Test User',
                db=mock_db
            )
            
            assert result is not None
            assert result['email'] == 'test@example.com'
            assert result['name'] == 'Test User'
            assert mock_db.add.called
            assert mock_db.commit.called
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_register_user_already_exists(self, auth_service, mock_db, mock_user):
        """Test user registration when user already exists"""
        # Mock that user exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        result = await auth_service.register_user(
            email='test@example.com',
            password='password123',
            name='Test User',
            db=mock_db
        )
        
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_authenticate_user_success(self, auth_service, mock_db, mock_user):
        """Test successful user authentication"""
        # Mock user exists and password is correct
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        with patch.object(PasswordHandler, 'verify_password') as mock_verify:
            mock_verify.return_value = True
            
            result = await auth_service.authenticate_user(
                email='test@example.com',
                password='password123',
                db=mock_db
            )
            
            assert result is not None
            assert result.email == 'test@example.com'
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_authenticate_user_invalid_password(self, auth_service, mock_db, mock_user):
        """Test user authentication with invalid password"""
        # Mock user exists but password is incorrect
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        with patch.object(PasswordHandler, 'verify_password') as mock_verify:
            mock_verify.return_value = False
            
            result = await auth_service.authenticate_user(
                email='test@example.com',
                password='wrong_password',
                db=mock_db
            )
            
            assert result is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_authenticate_user_not_found(self, auth_service, mock_db):
        """Test user authentication when user doesn't exist"""
        # Mock user doesn't exist
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await auth_service.authenticate_user(
            email='nonexistent@example.com',
            password='password123',
            db=mock_db
        )
        
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_create_session_success(self, auth_service, mock_db, mock_user):
        """Test successful session creation"""
        with patch.object(JWTHandler, 'create_access_token') as mock_create_token:
            mock_create_token.return_value = 'access_token'
            
            with patch.object(JWTHandler, 'create_refresh_token') as mock_create_refresh:
                mock_create_refresh.return_value = 'refresh_token'
                
                result = await auth_service.create_session(
                    user=mock_user,
                    db=mock_db
                )
                
                assert result is not None
                assert result['access_token'] == 'access_token'
                assert result['refresh_token'] == 'refresh_token'
                assert result['token_type'] == 'bearer'
                assert mock_db.add.called
                assert mock_db.commit.called
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_refresh_token_success(self, auth_service, mock_db):
        """Test successful token refresh"""
        refresh_token = 'valid_refresh_token'
        
        # Mock session exists and is valid
        mock_session = UserSession(
            id=uuid4(),
            user_id=uuid4(),
            refresh_token=refresh_token,
            expires_at=datetime.now() + timedelta(days=7),
            is_active=True
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result
        
        with patch.object(JWTHandler, 'create_access_token') as mock_create_token:
            mock_create_token.return_value = 'new_access_token'
            
            result = await auth_service.refresh_token(
                refresh_token=refresh_token,
                db=mock_db
            )
            
            assert result is not None
            assert result['access_token'] == 'new_access_token'
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_refresh_token_invalid(self, auth_service, mock_db):
        """Test token refresh with invalid token"""
        refresh_token = 'invalid_refresh_token'
        
        # Mock session doesn't exist
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await auth_service.refresh_token(
            refresh_token=refresh_token,
            db=mock_db
        )
        
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_logout_user_success(self, auth_service, mock_db):
        """Test successful user logout"""
        access_token = 'valid_access_token'
        
        # Mock session exists
        mock_session = UserSession(
            id=uuid4(),
            user_id=uuid4(),
            access_token=access_token,
            is_active=True
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result
        
        result = await auth_service.logout_user(
            access_token=access_token,
            db=mock_db
        )
        
        assert result is True
        assert mock_db.commit.called
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_verify_session_success(self, auth_service, mock_db, mock_user):
        """Test successful session verification"""
        access_token = 'valid_access_token'
        
        # Mock session exists and is valid
        mock_session = UserSession(
            id=uuid4(),
            user_id=mock_user.id,
            access_token=access_token,
            expires_at=datetime.now() + timedelta(hours=1),
            is_active=True
        )
        mock_session.user = mock_user
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result
        
        result = await auth_service.verify_session(
            access_token=access_token,
            db=mock_db
        )
        
        assert result is not None
        assert result.email == mock_user.email
    
    @pytest.mark.unit
    @pytest.mark.security
    async def test_verify_session_expired(self, auth_service, mock_db, mock_user):
        """Test session verification with expired token"""
        access_token = 'expired_access_token'
        
        # Mock session exists but is expired
        mock_session = UserSession(
            id=uuid4(),
            user_id=mock_user.id,
            access_token=access_token,
            expires_at=datetime.now() - timedelta(hours=1),  # Expired
            is_active=True
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result
        
        result = await auth_service.verify_session(
            access_token=access_token,
            db=mock_db
        )
        
        assert result is None


class TestPasswordHandler:
    """Unit tests for PasswordHandler class"""
    
    @pytest.fixture
    def password_handler(self):
        """Create PasswordHandler instance for testing"""
        return PasswordHandler()
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_hash_password_success(self, password_handler):
        """Test successful password hashing"""
        password = 'test_password_123'
        
        hashed = password_handler.hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_verify_password_success(self, password_handler):
        """Test successful password verification"""
        password = 'test_password_123'
        
        hashed = password_handler.hash_password(password)
        
        is_valid = password_handler.verify_password(password, hashed)
        
        assert is_valid is True
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_verify_password_invalid(self, password_handler):
        """Test password verification with wrong password"""
        password = 'test_password_123'
        wrong_password = 'wrong_password'
        
        hashed = password_handler.hash_password(password)
        
        is_valid = password_handler.verify_password(wrong_password, hashed)
        
        assert is_valid is False
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_hash_password_different_results(self, password_handler):
        """Test that same password produces different hashes (salt)"""
        password = 'test_password_123'
        
        hash1 = password_handler.hash_password(password)
        hash2 = password_handler.hash_password(password)
        
        assert hash1 != hash2  # Different due to salt
        
        # But both should verify correctly
        assert password_handler.verify_password(password, hash1)
        assert password_handler.verify_password(password, hash2)


class TestJWTHandler:
    """Unit tests for JWTHandler class"""
    
    @pytest.fixture
    def jwt_handler(self):
        """Create JWTHandler instance for testing"""
        return JWTHandler()
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_create_access_token_success(self, jwt_handler):
        """Test successful access token creation"""
        user_id = uuid4()
        
        token = jwt_handler.create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_create_refresh_token_success(self, jwt_handler):
        """Test successful refresh token creation"""
        user_id = uuid4()
        
        token = jwt_handler.create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_decode_token_success(self, jwt_handler):
        """Test successful token decoding"""
        user_id = uuid4()
        
        token = jwt_handler.create_access_token(user_id)
        decoded = jwt_handler.decode_token(token)
        
        assert decoded is not None
        assert 'sub' in decoded
        assert decoded['sub'] == str(user_id)
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_decode_token_invalid(self, jwt_handler):
        """Test token decoding with invalid token"""
        invalid_token = 'invalid.jwt.token'
        
        decoded = jwt_handler.decode_token(invalid_token)
        
        assert decoded is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.security
    def test_token_expiration(self, jwt_handler):
        """Test token expiration handling"""
        user_id = uuid4()
        
        # Create token with very short expiration
        with patch('app.services.auth.jwt_handler.datetime') as mock_datetime:
            # Mock current time
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            token = jwt_handler.create_access_token(user_id, expires_delta=timedelta(seconds=1))
            
            # Mock time after expiration
            mock_datetime.now.return_value = mock_now + timedelta(seconds=2)
            
            decoded = jwt_handler.decode_token(token)
            
            # Token should be expired and return None
            assert decoded is None


# Integration tests for authentication flow
class TestAuthenticationFlow:
    """Integration tests for complete authentication flow"""
    
    @pytest.mark.unit
    @pytest.mark.integration
    @pytest.mark.security
    async def test_complete_auth_flow(self):
        """Test complete authentication flow"""
        auth_service = AuthService()
        mock_db = AsyncMock()
        
        # Mock user registration
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch.object(PasswordHandler, 'hash_password') as mock_hash:
            mock_hash.return_value = 'hashed_password'
            
            # Register user
            user_data = await auth_service.register_user(
                email='test@example.com',
                password='password123',
                name='Test User',
                db=mock_db
            )
            
            assert user_data is not None
            
            # Mock user for authentication
            mock_user = User(
                id=uuid4(),
                email='test@example.com',
                name='Test User',
                password_hash='hashed_password',
                is_active=True
            )
            
            mock_result.scalar_one_or_none.return_value = mock_user
            
            with patch.object(PasswordHandler, 'verify_password') as mock_verify:
                mock_verify.return_value = True
                
                # Authenticate user
                authenticated_user = await auth_service.authenticate_user(
                    email='test@example.com',
                    password='password123',
                    db=mock_db
                )
                
                assert authenticated_user is not None
                assert authenticated_user.email == 'test@example.com'