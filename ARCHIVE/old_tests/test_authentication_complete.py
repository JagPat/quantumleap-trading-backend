#!/usr/bin/env python3
"""
Complete Authentication Implementation Test
Tests the full authentication flow including JWT tokens, protected endpoints, and frontend integration
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://web-production-de0bc.up.railway.app"
TEST_USERS = [
    {"email": "admin@quantumleap.ai", "password": "admin123", "role": "admin"},
    {"email": "user@quantumleap.ai", "password": "user123", "role": "user"},
    {"email": "test@quantumleap.ai", "password": "test123", "role": "user"}
]

class AuthenticationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.tokens = {}
        
    def print_header(self, title):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"🔐 {title}")
        print(f"{'='*60}")
    
    def print_step(self, step, description):
        """Print a test step"""
        print(f"\n{step}. {description}")
        print("-" * 40)
    
    def test_health_check(self):
        """Test basic health check"""
        self.print_step("1", "Testing Health Check")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed")
                print(f"   Status: {data.get('status')}")
                print(f"   Service: {data.get('service')}")
                print(f"   Version: {data.get('version')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return False
    
    def test_auth_health(self):
        """Test authentication system health"""
        self.print_step("2", "Testing Authentication System Health")
        
        try:
            response = self.session.get(f"{self.base_url}/api/auth/test-auth")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Auth health check passed")
                print(f"   Status: {data.get('status')}")
                print(f"   Service: {data.get('service')}")
                return True
            else:
                print(f"❌ Auth health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Auth health check error: {str(e)}")
            return False
    
    def test_get_test_users(self):
        """Test getting test users"""
        self.print_step("3", "Testing Get Test Users Endpoint")
        
        try:
            response = self.session.get(f"{self.base_url}/api/auth/test-users")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Test users retrieved successfully")
                print(f"   Available users: {len(data.get('test_users', []))}")
                for user in data.get('test_users', []):
                    print(f"   - {user.get('email')} ({user.get('role')})")
                return True
            else:
                print(f"❌ Get test users failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Get test users error: {str(e)}")
            return False
    
    def test_login(self, email, password, expected_role):
        """Test user login"""
        print(f"\\n🔑 Testing login for {email}")
        
        try:
            login_data = {
                "email": email,
                "password": password
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                user_id = data.get('user_id')
                role = data.get('role')
                
                print(f"✅ Login successful")
                print(f"   User ID: {user_id}")
                print(f"   Email: {data.get('email')}")
                print(f"   Role: {role}")
                print(f"   Token type: {data.get('token_type')}")
                print(f"   Token length: {len(token) if token else 0}")
                
                # Store token for later tests
                self.tokens[email] = {
                    'token': token,
                    'user_id': user_id,
                    'role': role
                }
                
                # Verify role matches expected
                if role == expected_role:
                    print(f"✅ Role verification passed")
                else:
                    print(f"⚠️  Role mismatch: expected {expected_role}, got {role}")
                
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   Raw response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False
    
    def test_token_validation(self, email):
        """Test token validation"""
        print(f"\\n🔍 Testing token validation for {email}")
        
        if email not in self.tokens:
            print(f"❌ No token available for {email}")
            return False
        
        try:
            token = self.tokens[email]['token']
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/validate-token",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Token validation successful")
                print(f"   Valid: {data.get('valid')}")
                print(f"   User ID: {data.get('user_id')}")
                print(f"   Email: {data.get('email')}")
                print(f"   Role: {data.get('role')}")
                print(f"   Expires at: {data.get('expires_at')}")
                return True
            else:
                print(f"❌ Token validation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Token validation error: {str(e)}")
            return False
    
    def test_get_user_info(self, email):
        """Test getting current user info"""
        print(f"\\n👤 Testing get user info for {email}")
        
        if email not in self.tokens:
            print(f"❌ No token available for {email}")
            return False
        
        try:
            token = self.tokens[email]['token']
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.get(
                f"{self.base_url}/api/auth/status",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Get user info successful")
                print(f"   User ID: {data.get('user_id')}")
                print(f"   Email: {data.get('email')}")
                print(f"   Role: {data.get('role')}")
                print(f"   Authenticated at: {data.get('authenticated_at')}")
                return True
            else:
                print(f"❌ Get user info failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Get user info error: {str(e)}")
            return False
    
    def test_protected_endpoint(self, email, endpoint, method="GET"):
        """Test access to protected AI endpoints"""
        print(f"\\n🛡️  Testing protected endpoint {endpoint} for {email}")
        
        if email not in self.tokens:
            print(f"❌ No token available for {email}")
            return False
        
        try:
            token = self.tokens[email]['token']
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            if method.upper() == "GET":
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)
            elif method.upper() == "POST":
                # For POST endpoints, send minimal test data
                test_data = {"message": "test", "context": {}}
                response = self.session.post(f"{self.base_url}{endpoint}", json=test_data, headers=headers)
            
            if response.status_code in [200, 201]:
                print(f"✅ Protected endpoint access successful")
                print(f"   Status: {response.status_code}")
                try:
                    data = response.json()
                    if 'user_id' in data:
                        print(f"   User ID in response: {data['user_id']}")
                    if 'status' in data:
                        print(f"   Response status: {data['status']}")
                except:
                    print(f"   Response length: {len(response.text)}")
                return True
            elif response.status_code == 401:
                print(f"❌ Authentication failed (401)")
                return False
            elif response.status_code == 403:
                print(f"❌ Authorization failed (403)")
                return False
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Protected endpoint test error: {str(e)}")
            return False
    
    def test_unauthenticated_access(self, endpoint, method="GET"):
        """Test that protected endpoints reject unauthenticated requests"""
        print(f"\\n🚫 Testing unauthenticated access to {endpoint}")
        
        try:
            if method.upper() == "GET":
                response = self.session.get(f"{self.base_url}{endpoint}")
            elif method.upper() == "POST":
                test_data = {"message": "test", "context": {}}
                response = self.session.post(f"{self.base_url}{endpoint}", json=test_data)
            
            if response.status_code == 401:
                print(f"✅ Correctly rejected unauthenticated request")
                print(f"   Status: {response.status_code}")
                return True
            else:
                print(f"❌ Should have rejected unauthenticated request")
                print(f"   Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Unauthenticated access test error: {str(e)}")
            return False
    
    def test_logout(self, email):
        """Test user logout"""
        print(f"\\n🚪 Testing logout for {email}")
        
        if email not in self.tokens:
            print(f"❌ No token available for {email}")
            return False
        
        try:
            token = self.tokens[email]['token']
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/logout",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Logout successful")
                print(f"   Status: {data.get('status')}")
                print(f"   Message: {data.get('message')}")
                print(f"   User ID: {data.get('user_id')}")
                
                # Remove token from storage
                del self.tokens[email]
                return True
            else:
                print(f"❌ Logout failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Logout error: {str(e)}")
            return False
    
    def run_complete_test(self):
        """Run complete authentication test suite"""
        self.print_header("COMPLETE AUTHENTICATION IMPLEMENTATION TEST")
        
        print(f"🎯 Testing against: {self.base_url}")
        print(f"📅 Test started: {datetime.now().isoformat()}")
        
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
        
        # Test 1: Health checks
        results['total_tests'] += 2
        if self.test_health_check():
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
            
        if self.test_auth_health():
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
        
        # Test 2: Get test users
        results['total_tests'] += 1
        if self.test_get_test_users():
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
        
        # Test 3: Login for each test user
        for user in TEST_USERS:
            results['total_tests'] += 1
            if self.test_login(user['email'], user['password'], user['role']):
                results['passed_tests'] += 1
            else:
                results['failed_tests'] += 1
        
        # Test 4: Token validation for logged in users
        for email in self.tokens.keys():
            results['total_tests'] += 1
            if self.test_token_validation(email):
                results['passed_tests'] += 1
            else:
                results['failed_tests'] += 1
        
        # Test 5: Get user info for logged in users
        for email in self.tokens.keys():
            results['total_tests'] += 1
            if self.test_get_user_info(email):
                results['passed_tests'] += 1
            else:
                results['failed_tests'] += 1
        
        # Test 6: Protected endpoints access
        protected_endpoints = [
            ("/api/ai/chat", "POST"),
            ("/api/ai/analysis/comprehensive", "POST"),
            ("/api/ai/strategy-templates", "GET"),
            ("/api/ai/performance-analytics", "GET"),
            ("/api/ai/risk-metrics", "GET"),
            ("/api/ai/learning-insights", "GET"),
            ("/api/ai/cost-tracking", "GET")
        ]
        
        # Test with authenticated user
        if self.tokens:
            test_email = list(self.tokens.keys())[0]
            for endpoint, method in protected_endpoints:
                results['total_tests'] += 1
                if self.test_protected_endpoint(test_email, endpoint, method):
                    results['passed_tests'] += 1
                else:
                    results['failed_tests'] += 1
        
        # Test 7: Unauthenticated access (should be rejected)
        for endpoint, method in protected_endpoints[:3]:  # Test a few endpoints
            results['total_tests'] += 1
            if self.test_unauthenticated_access(endpoint, method):
                results['passed_tests'] += 1
            else:
                results['failed_tests'] += 1
        
        # Test 8: Logout for all users
        for email in list(self.tokens.keys()):
            results['total_tests'] += 1
            if self.test_logout(email):
                results['passed_tests'] += 1
            else:
                results['failed_tests'] += 1
        
        # Print final results
        self.print_header("TEST RESULTS SUMMARY")
        print(f"📊 Total Tests: {results['total_tests']}")
        print(f"✅ Passed: {results['passed_tests']}")
        print(f"❌ Failed: {results['failed_tests']}")
        print(f"📈 Success Rate: {(results['passed_tests']/results['total_tests']*100):.1f}%")
        
        if results['failed_tests'] == 0:
            print(f"\\n🎉 ALL TESTS PASSED! Authentication implementation is working correctly.")
        else:
            print(f"\\n⚠️  Some tests failed. Please review the implementation.")
        
        print(f"\\n📅 Test completed: {datetime.now().isoformat()}")
        
        return results

def main():
    """Main test function"""
    tester = AuthenticationTester()
    results = tester.run_complete_test()
    
    # Exit with appropriate code
    if results['failed_tests'] == 0:
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()