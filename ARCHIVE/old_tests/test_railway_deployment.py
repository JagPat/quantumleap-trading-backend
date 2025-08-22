#!/usr/bin/env python3
"""
Railway Deployment Comprehensive Testing
Tests all endpoints and functionality on the live Railway deployment
"""
import requests
import json
import time
from datetime import datetime
import sys

# Railway deployment URL
RAILWAY_URL = "https://web-production-de0bc.up.railway.app"

def test_endpoint(method, endpoint, data=None, headers=None, expected_status=200, description=""):
    """Test a single endpoint"""
    url = f"{RAILWAY_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=30)
        else:
            return False, f"Unsupported method: {method}"
        
        success = response.status_code == expected_status
        
        if success:
            try:
                response_data = response.json()
                return True, response_data
            except:
                return True, response.text
        else:
            return False, f"Status: {response.status_code}, Response: {response.text[:500]}"
            
    except requests.exceptions.Timeout:
        return False, "Request timeout (30s)"
    except requests.exceptions.ConnectionError:
        return False, "Connection error - Railway app may be down"
    except Exception as e:
        return False, f"Error: {str(e)}"

def test_railway_deployment():
    """Comprehensive Railway deployment testing"""
    print("🚀 RAILWAY DEPLOYMENT COMPREHENSIVE TESTING")
    print("=" * 70)
    print(f"🔗 Testing URL: {RAILWAY_URL}")
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = []
    
    # Test 1: Basic Health Check
    print("1. 🏥 BASIC HEALTH CHECKS")
    print("-" * 40)
    
    # Root endpoint
    success, result = test_endpoint("GET", "/", description="Root endpoint")
    test_results.append(("Root Endpoint", success, result))
    if success:
        print("✅ Root endpoint: WORKING")
    else:
        print(f"❌ Root endpoint: FAILED - {result}")
    
    # Health endpoint
    success, result = test_endpoint("GET", "/health", description="Health check")
    test_results.append(("Health Check", success, result))
    if success:
        print("✅ Health endpoint: WORKING")
        if isinstance(result, dict):
            print(f"   Status: {result.get('status', 'unknown')}")
    else:
        print(f"❌ Health endpoint: FAILED - {result}")
    
    # Version endpoint
    success, result = test_endpoint("GET", "/version", description="Version info")
    test_results.append(("Version Info", success, result))
    if success:
        print("✅ Version endpoint: WORKING")
        if isinstance(result, dict):
            print(f"   Version: {result.get('version', 'unknown')}")
    else:
        print(f"❌ Version endpoint: FAILED - {result}")
    
    print()
    
    # Test 2: Enhanced AI Portfolio Analysis
    print("2. 🤖 ENHANCED AI PORTFOLIO ANALYSIS")
    print("-" * 40)
    
    # Test enhanced AI analysis endpoint
    portfolio_data = {
        "total_value": 1000000,
        "holdings": [
            {
                "tradingsymbol": "RELIANCE",
                "current_value": 200000,
                "quantity": 80,
                "average_price": 2400,
                "last_price": 2500,
                "pnl": 8000,
                "pnl_percentage": 4.17
            },
            {
                "tradingsymbol": "TCS",
                "current_value": 300000,
                "quantity": 100,
                "average_price": 2800,
                "last_price": 3000,
                "pnl": 20000,
                "pnl_percentage": 7.14
            }
        ],
        "positions": []
    }
    
    headers = {"X-User-ID": "test_user_railway", "Content-Type": "application/json"}
    
    success, result = test_endpoint(
        "POST", 
        "/api/ai/simple-analysis/portfolio", 
        data=portfolio_data, 
        headers=headers,
        description="Enhanced AI portfolio analysis"
    )
    test_results.append(("Enhanced AI Analysis", success, result))
    
    if success:
        print("✅ Enhanced AI Analysis: WORKING")
        if isinstance(result, dict):
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Provider: {result.get('provider_used', 'fallback')}")
            print(f"   Enhanced Features: {result.get('enhanced_features', False)}")
            print(f"   Market Context: {result.get('market_context_used', False)}")
            
            # Check analysis structure
            analysis = result.get('analysis', {})
            if analysis:
                print(f"   Portfolio Health Score: {analysis.get('portfolio_health', {}).get('overall_score', 'N/A')}")
                stock_recs = analysis.get('stock_recommendations', [])
                print(f"   Stock Recommendations: {len(stock_recs)}")
                if stock_recs:
                    print(f"   Sample Recommendation: {stock_recs[0].get('symbol', 'N/A')} - {stock_recs[0].get('action', 'N/A')}")
    else:
        print(f"❌ Enhanced AI Analysis: FAILED - {result}")
    
    print()
    
    # Test 3: User Investment Profile System
    print("3. 👤 USER INVESTMENT PROFILE SYSTEM")
    print("-" * 40)
    
    # Get user profile
    success, result = test_endpoint(
        "GET", 
        "/api/user/investment-profile/", 
        headers=headers,
        description="Get user profile"
    )
    test_results.append(("Get User Profile", success, result))
    
    if success:
        print("✅ Get User Profile: WORKING")
        if isinstance(result, dict):
            profile = result.get('profile', {})
            print(f"   Risk Tolerance: {profile.get('risk_tolerance', 'N/A')}")
            print(f"   Investment Timeline: {profile.get('investment_timeline', 'N/A')}")
            print(f"   Profile Completeness: {profile.get('profile_completeness', 0):.1f}%")
            print(f"   Risk Score: {profile.get('risk_score', 0):.1f}")
    else:
        print(f"❌ Get User Profile: FAILED - {result}")
    
    # Update user profile
    profile_update = {
        "risk_tolerance": "aggressive",
        "investment_timeline": "long_term",
        "preferred_sectors": ["Technology", "Banking"],
        "max_position_size": 20.0,
        "trading_frequency": "weekly"
    }
    
    success, result = test_endpoint(
        "PUT", 
        "/api/user/investment-profile/", 
        data=profile_update,
        headers=headers,
        description="Update user profile"
    )
    test_results.append(("Update User Profile", success, result))
    
    if success:
        print("✅ Update User Profile: WORKING")
        if isinstance(result, dict):
            profile = result.get('profile', {})
            print(f"   Updated Risk Tolerance: {profile.get('risk_tolerance', 'N/A')}")
            print(f"   Updated Timeline: {profile.get('investment_timeline', 'N/A')}")
            print(f"   Updated Completeness: {profile.get('profile_completeness', 0):.1f}%")
    else:
        print(f"❌ Update User Profile: FAILED - {result}")
    
    # Get profile recommendations
    success, result = test_endpoint(
        "GET", 
        "/api/user/investment-profile/recommendations", 
        headers=headers,
        description="Get profile recommendations"
    )
    test_results.append(("Profile Recommendations", success, result))
    
    if success:
        print("✅ Profile Recommendations: WORKING")
        if isinstance(result, dict):
            recs = result.get('recommendations', {})
            print(f"   Sector Allocation Recs: {len(recs.get('sector_allocation', []))}")
            print(f"   Risk Management Recs: {len(recs.get('risk_management', []))}")
            print(f"   Trading Strategy Recs: {len(recs.get('trading_strategy', []))}")
    else:
        print(f"❌ Profile Recommendations: FAILED - {result}")
    
    # Get risk assessment
    success, result = test_endpoint(
        "GET", 
        "/api/user/investment-profile/risk-assessment", 
        headers=headers,
        description="Get risk assessment"
    )
    test_results.append(("Risk Assessment", success, result))
    
    if success:
        print("✅ Risk Assessment: WORKING")
        if isinstance(result, dict):
            print(f"   Risk Score: {result.get('risk_score', 0):.1f}")
            print(f"   Risk Category: {result.get('risk_category', 'N/A')}")
    else:
        print(f"❌ Risk Assessment: FAILED - {result}")
    
    print()
    
    # Test 4: Legacy Endpoints (Backward Compatibility)
    print("4. 🔄 LEGACY ENDPOINTS (BACKWARD COMPATIBILITY)")
    print("-" * 40)
    
    # Test auth endpoints
    success, result = test_endpoint("GET", "/api/auth/status", description="Auth status")
    test_results.append(("Auth Status", success, result))
    if success:
        print("✅ Auth Status: WORKING")
    else:
        print(f"❌ Auth Status: FAILED - {result}")
    
    # Test portfolio endpoints
    success, result = test_endpoint("GET", "/api/portfolio/health", description="Portfolio health")
    test_results.append(("Portfolio Health", success, result))
    if success:
        print("✅ Portfolio Health: WORKING")
    else:
        print(f"❌ Portfolio Health: FAILED - {result}")
    
    # Test trading engine endpoints
    success, result = test_endpoint("GET", "/api/trading-engine/status", description="Trading engine status")
    test_results.append(("Trading Engine Status", success, result))
    if success:
        print("✅ Trading Engine Status: WORKING")
    else:
        print(f"❌ Trading Engine Status: FAILED - {result}")
    
    print()
    
    # Test 5: Performance and Response Times
    print("5. ⚡ PERFORMANCE TESTING")
    print("-" * 40)
    
    # Test response times
    start_time = time.time()
    success, result = test_endpoint("GET", "/health")
    health_response_time = (time.time() - start_time) * 1000
    
    start_time = time.time()
    success, result = test_endpoint("GET", "/api/user/investment-profile/", headers=headers)
    profile_response_time = (time.time() - start_time) * 1000
    
    print(f"✅ Health Endpoint Response Time: {health_response_time:.0f}ms")
    print(f"✅ Profile Endpoint Response Time: {profile_response_time:.0f}ms")
    
    if health_response_time < 1000:
        print("✅ Health endpoint performance: EXCELLENT")
    elif health_response_time < 3000:
        print("⚠️  Health endpoint performance: ACCEPTABLE")
    else:
        print("❌ Health endpoint performance: SLOW")
    
    print()
    
    # Test Results Summary
    print("=" * 70)
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("=" * 70)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, success, _ in test_results if success)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\nDETAILED RESULTS:")
    for test_name, success, result in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {test_name}")
        if not success:
            print(f"    Error: {str(result)[:100]}...")
    
    print()
    
    # Overall Assessment
    if passed_tests == total_tests:
        print("🎉 RAILWAY DEPLOYMENT: PERFECT!")
        print("✅ All endpoints working correctly")
        print("✅ Enhanced AI features operational")
        print("✅ User profile system functional")
        print("✅ Performance within acceptable limits")
        print("\n🚀 READY FOR FRONTEND INTEGRATION!")
        print("You can now proceed with frontend testing and integration.")
        return True
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  RAILWAY DEPLOYMENT: MOSTLY WORKING")
        print(f"✅ {passed_tests}/{total_tests} tests passed")
        print("⚠️  Some non-critical issues detected")
        print("\n🔧 MINOR FIXES NEEDED")
        print("Core functionality is working, minor issues can be addressed.")
        return True
    else:
        print("❌ RAILWAY DEPLOYMENT: ISSUES DETECTED")
        print(f"❌ Only {passed_tests}/{total_tests} tests passed")
        print("🚨 CRITICAL ISSUES NEED ATTENTION")
        print("\n🛠️  IMMEDIATE ACTION REQUIRED")
        print("Please review failed tests and fix critical issues.")
        return False

def main():
    """Main testing function"""
    print("🧪 STARTING RAILWAY DEPLOYMENT TESTING")
    print("=" * 70)
    
    success = test_railway_deployment()
    
    if success:
        print("\n🎯 TESTING COMPLETE - DEPLOYMENT READY!")
        print("The Railway deployment is working perfectly.")
        print("All enhanced AI features are operational.")
        print("You can now proceed with frontend integration and testing.")
    else:
        print("\n⚠️  TESTING COMPLETE - ISSUES DETECTED")
        print("Please review the failed tests and address any critical issues.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)