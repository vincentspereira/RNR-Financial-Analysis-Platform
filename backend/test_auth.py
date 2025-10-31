"""
Simple test script to verify authentication endpoints
"""
import asyncio
import json
from typing import Dict, Any

import httpx


async def test_authentication_flow():
    """Test the complete authentication flow"""
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        print("🚀 Testing Financial Analysis Platform Authentication API")
        print("=" * 60)
        
        # Test health check
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                print(f"   Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return
        
        # Test user registration
        print("\n2. Testing user registration...")
        user_data = {
            "email": "test@example.com",
            "password": "Test123!",  # Simple 8-character password
            "first_name": "Test",
            "last_name": "User"
        }
        
        print(f"   Password: '{user_data['password']}'")
        print(f"   Password length: {len(user_data['password'])} chars, {len(user_data['password'].encode('utf-8'))} bytes")
        
        try:
            response = await client.post(f"{base_url}/auth/register", json=user_data)
            if response.status_code == 201:
                print("✅ User registration successful")
                user_info = response.json()
                print(f"   User ID: {user_info['id']}")
                print(f"   Email: {user_info['email']}")
                print(f"   Name: {user_info['first_name']} {user_info['last_name']}")
            elif response.status_code == 409:
                print("ℹ️  User already exists (expected if running multiple times)")
            else:
                print(f"❌ Registration failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return
        
        # Test user login
        print("\n3. Testing user login...")
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        try:
            response = await client.post(f"{base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                print("✅ User login successful")
                login_response = response.json()
                access_token = login_response["access_token"]
                refresh_token = login_response["refresh_token"]
                print(f"   Token type: {login_response['token_type']}")
                print(f"   Expires in: {login_response['expires_in']} seconds")
                print(f"   User: {login_response['user']['first_name']} {login_response['user']['last_name']}")
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return
        except Exception as e:
            print(f"❌ Login error: {e}")
            return
        
        # Test getting current user
        print("\n4. Testing get current user...")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = await client.get(f"{base_url}/auth/me", headers=headers)
            if response.status_code == 200:
                print("✅ Get current user successful")
                user_info = response.json()
                print(f"   User: {user_info['first_name']} {user_info['last_name']}")
                print(f"   Email: {user_info['email']}")
                print(f"   Verified: {user_info['is_verified']}")
                print(f"   Subscription: {user_info['subscription_tier']}")
            else:
                print(f"❌ Get current user failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return
        except Exception as e:
            print(f"❌ Get current user error: {e}")
            return
        
        # Test token refresh
        print("\n5. Testing token refresh...")
        refresh_data = {"refresh_token": refresh_token}
        
        try:
            response = await client.post(f"{base_url}/auth/refresh", json=refresh_data)
            if response.status_code == 200:
                print("✅ Token refresh successful")
                refresh_response = response.json()
                new_access_token = refresh_response["access_token"]
                print(f"   New token received")
                print(f"   Expires in: {refresh_response['expires_in']} seconds")
            else:
                print(f"❌ Token refresh failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return
        except Exception as e:
            print(f"❌ Token refresh error: {e}")
            return
        
        # Test logout
        print("\n6. Testing user logout...")
        headers = {"Authorization": f"Bearer {new_access_token}"}
        
        try:
            response = await client.post(f"{base_url}/auth/logout", headers=headers)
            if response.status_code == 200:
                print("✅ User logout successful")
                logout_response = response.json()
                print(f"   Message: {logout_response['message']}")
            else:
                print(f"❌ Logout failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return
        except Exception as e:
            print(f"❌ Logout error: {e}")
            return
        
        # Test using revoked token (should fail)
        print("\n7. Testing revoked token (should fail)...")
        try:
            response = await client.get(f"{base_url}/auth/me", headers=headers)
            if response.status_code == 401:
                print("✅ Revoked token correctly rejected")
            else:
                print(f"❌ Revoked token not rejected: {response.status_code}")
        except Exception as e:
            print(f"❌ Revoked token test error: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 All authentication tests completed successfully!")
        print("🔗 API Documentation: http://localhost:8000/docs")
        print("🔗 Alternative Docs: http://localhost:8000/redoc")


if __name__ == "__main__":
    asyncio.run(test_authentication_flow())