#!/usr/bin/env python3
"""
Complete Frontend-Backend Integration Test
Tests all endpoints that the frontend is calling to ensure seamless integration
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://web-production-de0bc.up.railway.app"
TEST_USER_ID = "test_user_123"

class CompleteFrontendBackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        
    def print_header(self, title):
        """Print a formatted header"""
        print(f"\n{'='*70}")
        print(f"🚀 {title}")
        print(f"{'='*70}")
    
    def print_section(self, section):
        """Print a section header"""
        print(f"\n{'─'*50}")
        print(f"📋 {section}")
        print(f"{'─'*50}")
    
    def test_endpoint(self, method, endpoint, description, data=None, expected_status=200):
        """Test a specific endpoint"""
        print(f"\n🔍 {description}")
        print(f"   {method} {endpoint}")
        
        try:
            if method.upper() == "GET":
                response = self.session.get(f"{self.base_url}{endpoint}")
            elif method.upper() == "POST":
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json=data if data else {},
                    headers={"Content-Type": "application/json"}
                )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == expected_status:
                try:
                    response_data = response.json()
                    print(f"   ✅ SUCCESS")
                    
                    # Show key response data
                    if isinstance(response_data, dict):
                        if 'status' in response_data:
                            print(f"   📊 Status: {response_data['status']}")
                        if 'success' in response_data:
                            print(f"   ✅ Success: {response_data['success']}")
                        if 'data' in response_data and response_data['data']:
                            data_info = response_data['data']
                            if isinstance(data_info, dict):
                                if 'total_value' in data_info:
                                    print(f"   💰 Total Value: ₹{data_info['total_value']:,.2f}")
                                if 'user_id' in data_info:
                                    print(f"   👤 User ID: {data_info['user_id']}")
                    
                    return True, response_data
                except json.JSONDecodeError:
                    print(f"   ⚠️  Non-JSON response: {response.text[:100]}...")
                    return True, response.text
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   Raw error: {response.text[:100]}...")
                return False, None
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            return False, None
    
    def test_backend_status(self):
        """Test backend status and router loading"""
        self.print_section("Backend System Status")
        
        success, data = self.test_endpoint("GET", "/status", "Backend Status Check")
        
        if success and data:
            routers_loaded = data.get('routers_loaded', [])
            print(f"\n📊 Loaded Routers: {', '.join(routers_loaded)}")
            
            # Check critical routers
            critical_routers = ['Portfolio', 'AI Components', 'Broker', 'Trading Engine']
            missing_routers = [r for r in critical_routers if r not in routers_loaded]
            
            if missing_routers:
                print(f"❌ Missing Critical Routers: {', '.join(missing_routers)}")
                return False
            else:
                print(f"✅ All critical routers loaded")
                return True
        
        return False
    
    def test_portfolio_endpoints(self):
        """Test all portfolio endpoints that frontend calls"""
        self.print_section("Portfolio Integration")
        
        endpoints = [
            ("GET", f"/api/portfolio/fetch-live-simple?user_id={TEST_USER_ID}", "Fetch Live Portfolio"),
            ("GET", f"/api/portfolio/latest-simple?user_id={TEST_USER_ID}", "Get Latest Portfolio"),
            ("GET", f"/api/portfolio/mock?user_id={TEST_USER_ID}", "Get Mock Portfolio"),
            ("GET", f"/api/portfolio/summary?user_id={TEST_USER_ID}", "Get Portfolio Summary"),
            ("GET", f"/api/portfolio/performance?user_id={TEST_USER_ID}&timeframe=1M", "Get Portfolio Performance"),
            ("GET", "/api/portfolio/status", "Portfolio Service Status")
        ]
        
        results = []
        for method, endpoint, description in endpoints:
            success, _ = self.test_endpoint(method, endpoint, description)
            results.append((description, success))
        
        return results
    
    def test_ai_endpoints(self):
        """Test all AI endpoints that frontend calls"""
        self.print_section("AI Services Integration")
        
        # Test data for AI endpoints
        portfolio_data = {
            "user_id": TEST_USER_ID,
            "holdings": [
                {"symbol": "RELIANCE", "quantity": 100, "avg_price": 2450.50},
                {"symbol": "TCS", "quantity": 50, "avg_price": 3850.25}
            ],
            "total_value": 125000.00,
            "day_pnl": 2500.00
        }
        
        ai_preferences = {
            "default_provider": "openai",
            "risk_tolerance": "moderate"
        }
        
        validate_key_data = {
            "provider": "openai",
            "api_key": "sk-test123456789"
        }
        
        message_data = {
            "message": "Analyze my portfolio performance",
            "context": {"user_id": TEST_USER_ID}
        }
        
        strategy_params = {
            "strategy_type": "momentum",
            "risk_level": "moderate",
            "timeframe": "short_term"
        }
        
        endpoints = [
            ("GET", "/api/ai/health", "AI Health Check", None),
            ("GET", "/api/ai/status", "AI Status", None),
            ("GET", "/api/ai/preferences", "Get AI Preferences", None),
            ("POST", "/api/ai/preferences", "Save AI Preferences", ai_preferences),
            ("POST", "/api/ai/validate-key", "Validate AI Key", validate_key_data),
            ("POST", "/api/ai/analysis/portfolio", "Analyze Portfolio", portfolio_data),
            ("POST", "/api/ai/message", "Send AI Message", message_data),
            ("POST", "/api/ai/strategy/generate", "Generate Strategy", strategy_params),
            ("GET", "/api/ai/market/analyze?symbol=RELIANCE", "Market Analysis", None),
            ("GET", f"/api/ai/signals/get?user_id={TEST_USER_ID}", "Trading Signals", None)
        ]
        
        results = []
        for method, endpoint, description, data in endpoints:
            success, _ = self.test_endpoint(method, endpoint, description, data)
            results.append((description, success))
        
        return results
    
    def test_broker_endpoints(self):
        """Test broker endpoints that frontend calls"""
        self.print_section("Broker Integration")
        
        endpoints = [
            ("GET", f"/api/broker/status?user_id={TEST_USER_ID}", "Broker Status"),
            ("GET", f"/api/broker/session?user_id={TEST_USER_ID}", "Broker Session"),
            ("GET", "/api/broker/status-header", "Broker Status Header")
        ]
        
        results = []
        for method, endpoint, description in endpoints:
            success, _ = self.test_endpoint(method, endpoint, description)
            results.append((description, success))
        
        return results
    
    def test_trading_engine_endpoints(self):
        """Test trading engine endpoints that frontend calls"""
        self.print_section("Trading Engine Integration")
        
        endpoints = [
            ("GET", "/api/trading-engine/status", "Trading Engine Status"),
            ("GET", f"/api/trading-engine/strategies/active?user_id={TEST_USER_ID}", "Active Strategies"),
            ("GET", f"/api/trading-engine/performance?user_id={TEST_USER_ID}", "Performance Metrics"),
            ("GET", "/api/trading-engine/system-health", "System Health")
        ]
        
        results = []
        for method, endpoint, description in endpoints:
            success, _ = self.test_endpoint(method, endpoint, description)
            results.append((description, success))
        
        return results
    
    def run_complete_integration_test(self):
        """Run complete frontend-backend integration test"""
        self.print_header("COMPLETE FRONTEND-BACKEND INTEGRATION TEST")
        
        print(f"🎯 Testing against: {self.base_url}")
        print(f"👤 Test User ID: {TEST_USER_ID}")
        print(f"📅 Test started: {datetime.now().isoformat()}")
        
        # Test 1: Backend status
        backend_healthy = self.test_backend_status()
        
        # Test 2: Portfolio integration
        portfolio_results = self.test_portfolio_endpoints()
        
        # Test 3: AI services integration
        ai_results = self.test_ai_endpoints()
        
        # Test 4: Broker integration
        broker_results = self.test_broker_endpoints()
        
        # Test 5: Trading engine integration
        trading_results = self.test_trading_engine_endpoints()
        
        # Compile results
        all_results = {
            'Portfolio': portfolio_results,
            'AI Services': ai_results,
            'Broker': broker_results,
            'Trading Engine': trading_results
        }
        
        # Summary
        self.print_header("INTEGRATION TEST RESULTS SUMMARY")
        
        print(f"🔧 Backend Status: {'✅ Healthy' if backend_healthy else '❌ Issues'}")
        
        total_tests = 0
        total_passed = 0
        
        for category, results in all_results.items():
            passed = sum(1 for _, success in results if success)
            total = len(results)
            total_tests += total
            total_passed += passed
            
            print(f"\n📊 {category} Integration:")
            print(f"   Passed: {passed}/{total} ({(passed/total*100):.1f}%)")
            
            for description, success in results:
                status = "✅" if success else "❌"
                print(f"   {status} {description}")
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n🎯 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_tests - total_passed}")
        print(f"   Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 90:
            print(f"\n🎉 INTEGRATION TEST PASSED!")
            print(f"   Frontend-backend integration is working excellently.")
            print(f"   Users can access all services with real-life data.")
        elif overall_success_rate >= 70:
            print(f"\n⚠️  INTEGRATION TEST PARTIALLY PASSED")
            print(f"   Most services are working, but some issues remain.")
            print(f"   Check failed endpoints above.")
        else:
            print(f"\n❌ INTEGRATION TEST FAILED")
            print(f"   Significant integration issues detected.")
            print(f"   Multiple services are not accessible.")
        
        print(f"\n📅 Test completed: {datetime.now().isoformat()}")
        
        return {
            'backend_healthy': backend_healthy,
            'overall_success_rate': overall_success_rate,
            'total_tests': total_tests,
            'total_passed': total_passed,
            'category_results': all_results
        }

def main():
    """Main test function"""
    tester = CompleteFrontendBackendTester()
    results = tester.run_complete_integration_test()
    
    # Exit with appropriate code
    if results['overall_success_rate'] >= 90:
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()