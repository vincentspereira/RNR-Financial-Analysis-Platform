"""
Test password hashing directly
"""
from app.services.auth.password_handler import password_handler

def test_password_hashing():
    """Test password hashing directly"""
    password = "Test123!"
    print(f"Testing password: '{password}'")
    print(f"Password length: {len(password)} chars, {len(password.encode('utf-8'))} bytes")
    
    try:
        hashed = password_handler.hash_password(password)
        print(f"✅ Password hashed successfully: {hashed[:50]}...")
        
        # Test verification
        is_valid = password_handler.verify_password(password, hashed)
        print(f"✅ Password verification: {is_valid}")
        
    except Exception as e:
        print(f"❌ Password hashing failed: {e}")

if __name__ == "__main__":
    test_password_hashing()