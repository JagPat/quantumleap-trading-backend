#!/usr/bin/env python3
"""
Verify Railway Deployment Status
Tests the deployed backend endpoints to ensure everything is working
"""

import requests
import time
import json
from datetime import datetime

RAILWAY_URL = "https://quantum-leap-backend-production.up.railway.app"

def test_endpoint(endpoint, method="GET", data=None, timeout=10):
    """Test a single endpoint"""
    try:
        url = f"{RAILWAY_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "response_time": response.elapsed.total_seconds()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time": None
        }

def main():
    """Main verification function"""
    print("🔍 Verifying Railway Deployment")
    print("=" * 50)
    
    # Test endpoints
    endpoints_to_test = [
        ("/", "GET", None, "Root endpoint"),
        ("/health", "GET", None, "Health check"),
        ("/api/database/health", "GET", None, "Database health"),
        ("/api/database/metrics", "GET", None, "Database metrics"),
        ("/api/database/connection-info", "GET", None, "Database connection info"),
        ("/api/trading-engine/status", "GET", None, "Trading engine status"),
        ("/api/portfolio/holdings", "GET", None, "Portfolio holdings"),
        ("/api/ai/status", "GET", None, "AI engine status")
    ]
    
    results = []
    
    for endpoint, method, data, description in endpoints_to_test:
        print(f"\n🧪 Testing {description} ({endpoint})...")
        result = test_endpoint(endpoint, method, data)
        
        if result["success"]:
            print(f"✅ {description}: {result['status_code']} ({result['response_time']:.2f}s)")
            if result["status_code"] == 200:
                print(f"   Response: {str(result['response'])[:100]}...")
        else:
            print(f"❌ {description}: {result['error']}")
        
        results.append({
            "endpoint": endpoint,
            "description": description,
            "result": result
        })
        
        time.sleep(0.5)  # Small delay between requests
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Deployment Verification Summary")
    print("=" * 50)
    
    successful_tests = sum(1 for r in results if r["result"]["success"] and r["result"].get("status_code") == 200)
    total_tests = len(results)
    
    print(f"✅ Successful: {successful_tests}/{total_tests}")
    print(f"❌ Failed: {total_tests - successful_tests}/{total_tests}")
    
    if successful_tests >= total_tests * 0.7:  # 70% success rate
        print("\n🎉 Deployment verification PASSED!")
        print("🚀 Railway backend is operational")
    else:
        print("\n⚠️ Deployment verification needs attention")
        print("🔧 Some endpoints may still be starting up")
    
    # Save detailed results
    with open("railway_deployment_verification.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "railway_url": RAILWAY_URL,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests,
            "results": results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: railway_deployment_verification.json")
    print(f"🔗 Backend URL: {RAILWAY_URL}")

if __name__ == "__main__":
    main()