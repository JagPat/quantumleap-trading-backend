#!/usr/bin/env python3
"""
Test Portfolio Frontend-Backend Integration
Tests the exact endpoints that the frontend is calling
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://web-production-de0bc.up.railway.app"
TEST_USER_ID = "test_user_123"

class PortfolioIntegrationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        
    def print_header(self, title):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"📊 {title}")
        print(f"{'='*60}")
    
    def print_step(self, step, description):
        """Print a test step"""
        print(f"\n{step}. {description}")
        print("-" * 40)
    
    def test_portfolio_endpoint(self, endpoint, description):
        """Test a specific portfolio endpoint"""
        print(f"\n🔍 Testing: {description}")
        print(f"   Endpoint: {endpoint}")
        
        try:
            response = self.session.get(f"{self.base_url}{endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ SUCCESS - Response received")
                    
                    # Show key data fields
                    if isinstance(data, dict):
                        if 'data' in data and data['data']:
                            portfolio_data = data['data']
                            if 'total_value' in portfolio_data:
                                print(f"   💰 Total Value: ₹{portfolio_data['total_value']:,.2f}")
                            if 'day_pnl' in portfolio_data:
                                print(f"   📈 Day P&L: ₹{portfolio_data['day_pnl']:,.2f}")
                            if 'holdings' in portfolio_data:
                                holdings_count = len(portfolio_data['holdings']) if portfolio_data['holdings'] else 0
                                print(f"   📋 Holdings: {holdings_count} stocks")
                        elif 'status' in data:
                            print(f"   📊 Status: {data['status']}")
                    
                    return True
                except json.JSONDecodeError:
                    print(f"   ⚠️  Response not JSON: {response.text[:100]}...")
                    return False
            elif response.status_code == 404:
                print(f"   ❌ ENDPOINT NOT FOUND (404)")
                return False
            else:
                print(f"   ❌ ERROR - Status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   Raw error: {response.text[:100]}...")
                return False
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            return False
    
    def test_backend_status(self):
        """Test backend status and router loading"""
        self.print_step("1", "Testing Backend Status")
        
        try:
            response = self.session.get(f"{self.base_url}/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Backend Status: {data.get('status')}")
                print(f"📊 Total Routers: {data.get('total_routers')}")
                print(f"🔧 Loaded Routers: {', '.join(data.get('routers_loaded', []))}")
                
                # Check if Portfolio router is loaded
                routers_loaded = data.get('routers_loaded', [])
                if 'Portfolio' in routers_loaded:
                    print(f"✅ Portfolio router is LOADED")
                    return True
                else:
                    print(f"❌ Portfolio router is NOT LOADED")
                    print(f"   This means the portfolio endpoints will return 404")
                    return False
            else:
                print(f"❌ Backend status check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend status error: {str(e)}")
            return False
    
    def test_all_frontend_endpoints(self):
        """Test all endpoints that the frontend is calling"""
        self.print_step("2", "Testing Frontend-Called Portfolio Endpoints")
        
        # These are the exact endpoints from railwayApiClient.js
        endpoints = [
            (f"/api/portfolio/fetch-live-simple?user_id={TEST_USER_ID}", "Fetch Live Portfolio"),
            (f"/api/portfolio/latest-simple?user_id={TEST_USER_ID}", "Get Latest Portfolio"),
            (f"/api/portfolio/mock?user_id={TEST_USER_ID}", "Get Mock Portfolio"),
            (f"/api/portfolio/summary?user_id={TEST_USER_ID}", "Get Portfolio Summary"),
            (f"/api/portfolio/performance?user_id={TEST_USER_ID}&timeframe=1M", "Get Portfolio Performance"),
            ("/api/portfolio/status", "Portfolio Service Status")
        ]
        
        results = []
        for endpoint, description in endpoints:
            success = self.test_portfolio_endpoint(endpoint, description)
            results.append((description, success))
        
        return results
    
    def test_ai_portfolio_integration(self):
        """Test AI portfolio analysis endpoint"""
        self.print_step("3", "Testing AI Portfolio Analysis Integration")
        
        # Test the AI portfolio analysis endpoint that the frontend uses
        endpoint = "/api/ai/analysis/portfolio"
        print(f"\n🤖 Testing: AI Portfolio Analysis")
        print(f"   Endpoint: {endpoint}")
        
        try:
            # Sample portfolio data that frontend would send
            portfolio_data = {
                "user_id": TEST_USER_ID,
                "holdings": [
                    {"symbol": "RELIANCE", "quantity": 100, "avg_price": 2450.50},
                    {"symbol": "TCS", "quantity": 50, "avg_price": 3850.25}
                ],
                "total_value": 125000.00,
                "day_pnl": 2500.00
            }
            
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=portfolio_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ AI Portfolio Analysis endpoint is working")
                return True
            elif response.status_code == 404:
                print(f"   ❌ AI Portfolio Analysis endpoint NOT FOUND")
                return False
            else:
                print(f"   ⚠️  AI endpoint returned: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ AI endpoint test error: {str(e)}")
            return False
    
    def run_complete_integration_test(self):
        """Run complete frontend-backend integration test"""
        self.print_header("PORTFOLIO FRONTEND-BACKEND INTEGRATION TEST")
        
        print(f"🎯 Testing against: {self.base_url}")
        print(f"👤 Test User ID: {TEST_USER_ID}")
        print(f"📅 Test started: {datetime.now().isoformat()}")
        
        # Test 1: Backend status and router loading
        backend_healthy = self.test_backend_status()
        
        # Test 2: All frontend portfolio endpoints
        endpoint_results = self.test_all_frontend_endpoints()
        
        # Test 3: AI portfolio integration
        ai_working = self.test_ai_portfolio_integration()
        
        # Summary
        self.print_header("INTEGRATION TEST RESULTS")
        
        print(f"🔧 Backend Status: {'✅ Healthy' if backend_healthy else '❌ Issues'}")
        print(f"🤖 AI Integration: {'✅ Working' if ai_working else '❌ Issues'}")
        
        print(f"\n📊 Portfolio Endpoints Results:")
        working_endpoints = 0
        total_endpoints = len(endpoint_results)
        
        for description, success in endpoint_results:
            status = "✅ Working" if success else "❌ Failed"
            print(f"   {description}: {status}")
            if success:
                working_endpoints += 1
        
        success_rate = (working_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
        
        print(f"\n📈 Overall Results:")
        print(f"   Working Endpoints: {working_endpoints}/{total_endpoints}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100 and backend_healthy:
            print(f"\n🎉 INTEGRATION TEST PASSED!")
            print(f"   All portfolio endpoints are working correctly.")
            print(f"   Frontend can successfully connect to backend portfolio services.")
        elif success_rate > 0:
            print(f"\n⚠️  PARTIAL SUCCESS")
            print(f"   Some endpoints are working, but issues remain.")
            print(f"   Check the failed endpoints above.")
        else:
            print(f"\n❌ INTEGRATION TEST FAILED")
            print(f"   Portfolio router is likely not loaded due to missing dependencies.")
            print(f"   Check requirements.txt and redeploy to Railway.")
        
        print(f"\n📅 Test completed: {datetime.now().isoformat()}")
        
        return {
            'backend_healthy': backend_healthy,
            'ai_working': ai_working,
            'endpoint_results': endpoint_results,
            'success_rate': success_rate,
            'working_endpoints': working_endpoints,
            'total_endpoints': total_endpoints
        }

def main():
    """Main test function"""
    tester = PortfolioIntegrationTester()
    results = tester.run_complete_integration_test()
    
    # Exit with appropriate code
    if results['success_rate'] == 100 and results['backend_healthy']:
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()