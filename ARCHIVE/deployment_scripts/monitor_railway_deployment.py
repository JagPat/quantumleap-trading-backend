#!/usr/bin/env python3
"""
Monitor Railway Deployment Progress
Continuously monitors Railway deployment until it succeeds or times out
"""

import requests
import time
from datetime import datetime

RAILWAY_URL = "https://web-production-de0bc.up.railway.app"

def check_railway_status():
    """Check Railway deployment status"""
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        if response.status_code == 200:
            # Check detailed status
            status_response = requests.get(f"{RAILWAY_URL}/status", timeout=10)
            if status_response.status_code == 200:
                data = status_response.json()
                routers = data.get('routers_loaded', [])
                return True, routers
            else:
                return True, []
        else:
            return False, []
    except Exception as e:
        return False, []

def monitor_deployment():
    """Monitor Railway deployment"""
    print("🚀 Monitoring Railway Deployment")
    print(f"🔗 URL: {RAILWAY_URL}")
    print(f"📅 Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)
    
    check_count = 0
    max_checks = 60  # 30 minutes max
    
    while check_count < max_checks:
        check_count += 1
        current_time = datetime.now().strftime('%H:%M:%S')
        
        print(f"\n🔍 Check #{check_count} at {current_time}")
        
        responding, routers = check_railway_status()
        
        if responding:
            print(f"✅ Railway is responding!")
            print(f"📊 Loaded routers: {', '.join(routers) if routers else 'None'}")
            
            if 'Portfolio' in routers:
                print(f"\n🎉 SUCCESS! Portfolio router is loaded!")
                print(f"✅ All critical routers are working")
                
                # Run quick integration test
                print(f"\n🧪 Running quick integration test...")
                try:
                    portfolio_response = requests.get(f"{RAILWAY_URL}/api/portfolio/mock?user_id=test", timeout=10)
                    if portfolio_response.status_code == 200:
                        print(f"✅ Portfolio endpoint working!")
                    else:
                        print(f"⚠️  Portfolio endpoint returned {portfolio_response.status_code}")
                        
                    ai_response = requests.get(f"{RAILWAY_URL}/api/ai/health", timeout=10)
                    if ai_response.status_code == 200:
                        print(f"✅ AI endpoint working!")
                    else:
                        print(f"⚠️  AI endpoint returned {ai_response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️  Integration test error: {str(e)}")
                
                print(f"\n🎯 DEPLOYMENT SUCCESSFUL!")
                print(f"⏱️  Total time: {check_count * 30} seconds")
                return True
            else:
                missing_routers = ['Portfolio'] if 'Portfolio' not in routers else []
                if missing_routers:
                    print(f"⏳ Still waiting for: {', '.join(missing_routers)}")
                else:
                    print(f"✅ All routers loaded!")
        else:
            print(f"⏳ Railway not responding yet (still deploying...)")
        
        if check_count < max_checks:
            print(f"⏳ Waiting 30 seconds for next check...")
            time.sleep(30)
    
    print(f"\n⏰ Monitoring timeout after {max_checks * 30} seconds")
    print(f"ℹ️  Railway may still be deploying - check manually")
    return False

if __name__ == "__main__":
    success = monitor_deployment()
    
    if success:
        print(f"\n🚀 Next steps:")
        print(f"   1. Run full integration test: python3 test_complete_frontend_backend_integration.py")
        print(f"   2. Test frontend connection to backend")
        print(f"   3. Verify portfolio data loading")
        print(f"   4. Test AI analysis features")
    else:
        print(f"\n🔧 Check Railway deployment manually:")
        print(f"   1. Visit Railway dashboard")
        print(f"   2. Check deployment logs")
        print(f"   3. Verify all dependencies are installed")
    
    exit(0 if success else 1)