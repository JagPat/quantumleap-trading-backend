#!/usr/bin/env python3
"""
Diagnose Railway Deployment Issues
Comprehensive diagnosis of Railway deployment status
"""

import requests
import json
import time
from datetime import datetime

RAILWAY_URL = "https://quantum-leap-backend-production.up.railway.app"

def check_railway_status():
    """Check Railway deployment status"""
    print("🔍 Diagnosing Railway Deployment Issues")
    print("=" * 60)
    
    # Test basic connectivity
    print("\n1️⃣ Testing Basic Connectivity...")
    try:
        response = requests.get(RAILWAY_URL, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Response: {response.text[:500]}...")
        
        if response.status_code == 404:
            print("   ⚠️ Getting 404 - This suggests:")
            print("      - Railway deployment is still in progress")
            print("      - Application failed to start")
            print("      - Routing configuration issue")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - Railway service may be down")
    except requests.exceptions.Timeout:
        print("   ⏱️ Request timed out - Service may be starting")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    
    # Check if it's a routing issue
    print("\n2️⃣ Testing Alternative Endpoints...")
    test_paths = [
        "/",
        "/health",
        "/api",
        "/docs",
        "/openapi.json"
    ]
    
    for path in test_paths:
        try:
            response = requests.get(f"{RAILWAY_URL}{path}", timeout=5)
            print(f"   {path}: {response.status_code}")
        except Exception as e:
            print(f"   {path}: Error - {e}")
    
    # Check Railway-specific headers
    print("\n3️⃣ Checking Railway-Specific Information...")
    try:
        response = requests.get(RAILWAY_URL, timeout=10)
        railway_headers = {k: v for k, v in response.headers.items() if 'railway' in k.lower()}
        if railway_headers:
            print(f"   Railway Headers: {railway_headers}")
        else:
            print("   No Railway-specific headers found")
    except Exception as e:
        print(f"   Error checking headers: {e}")
    
    # Provide troubleshooting steps
    print("\n4️⃣ Troubleshooting Steps:")
    print("   📋 Check Railway Dashboard:")
    print("      https://railway.com/project/925c1cba-ce50-4be3-b5f9-a6bcb7dac747")
    print("   📋 Common Issues:")
    print("      - Build still in progress (check build logs)")
    print("      - Application startup failure (check runtime logs)")
    print("      - Port configuration issue (should use PORT env var)")
    print("      - Dependencies missing (check requirements.txt)")
    print("   📋 Expected Behavior:")
    print("      - Build should complete successfully")
    print("      - Application should start on $PORT")
    print("      - Health endpoint should return 200")
    
    return response.status_code if 'response' in locals() else None

def create_railway_diagnostic_report():
    """Create a diagnostic report"""
    print("\n📄 Creating Diagnostic Report...")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "railway_url": RAILWAY_URL,
        "diagnosis": "Railway deployment returning 404 errors",
        "possible_causes": [
            "Deployment still in progress",
            "Application failed to start",
            "Port configuration issue",
            "Routing configuration problem",
            "Build failure"
        ],
        "recommended_actions": [
            "Check Railway dashboard for build/deployment status",
            "Review Railway build logs for errors",
            "Verify main.py starts correctly locally",
            "Check PORT environment variable usage",
            "Ensure all dependencies are in requirements.txt"
        ],
        "next_steps": [
            "Wait 5-10 minutes for deployment to complete",
            "Check Railway logs for specific error messages",
            "Test local deployment to verify code works",
            "Consider manual Railway redeploy if needed"
        ]
    }
    
    with open("railway_diagnostic_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("   ✅ Report saved to: railway_diagnostic_report.json")

def main():
    """Main diagnostic function"""
    status_code = check_railway_status()
    create_railway_diagnostic_report()
    
    print("\n" + "=" * 60)
    if status_code == 404:
        print("🔧 DIAGNOSIS: Railway deployment needs attention")
        print("⏱️ RECOMMENDATION: Wait 5-10 minutes and check Railway dashboard")
        print("📊 DASHBOARD: https://railway.com/project/925c1cba-ce50-4be3-b5f9-a6bcb7dac747")
    elif status_code == 200:
        print("✅ DIAGNOSIS: Railway deployment is working!")
    else:
        print(f"⚠️ DIAGNOSIS: Unexpected status code: {status_code}")
    
    print("\n💡 TIP: Railway deployments can take 5-15 minutes depending on:")
    print("   - Build complexity")
    print("   - Dependency installation")
    print("   - Application startup time")

if __name__ == "__main__":
    main()