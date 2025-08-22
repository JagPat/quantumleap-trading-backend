#!/usr/bin/env python3
"""
Trigger Railway Redeploy and Monitor
Forces Railway to redeploy by making a small change and monitoring the deployment
"""

import subprocess
import requests
import time
from datetime import datetime

RAILWAY_URL = "https://web-production-de0bc.up.railway.app"

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def check_railway_status():
    """Check current Railway deployment status"""
    try:
        response = requests.get(f"{RAILWAY_URL}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            routers = data.get('routers_loaded', [])
            print(f"✅ Railway responding - Routers: {', '.join(routers)}")
            return True, routers
        else:
            print(f"⚠️  Railway status: {response.status_code}")
            return False, []
    except Exception as e:
        print(f"❌ Railway connection error: {str(e)}")
        return False, []

def trigger_redeploy():
    """Trigger Railway redeploy by making a small change"""
    print_header("TRIGGERING RAILWAY REDEPLOY")
    
    # Create a small change to trigger redeploy
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add a comment to main.py to trigger redeploy
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        
        # Add a timestamp comment at the top
        new_content = f'# Last deployment trigger: {timestamp}\n' + content
        
        with open('main.py', 'w') as f:
            f.write(new_content)
        
        print(f"✅ Added deployment trigger comment to main.py")
        
        # Commit and push the change
        subprocess.run(['git', 'add', 'main.py'], check=True)
        subprocess.run(['git', 'commit', '-m', f'🔄 Trigger Railway redeploy - {timestamp}'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        
        print(f"✅ Pushed redeploy trigger to GitHub")
        return True
        
    except Exception as e:
        print(f"❌ Failed to trigger redeploy: {str(e)}")
        return False

def monitor_deployment(max_wait_minutes=15):
    """Monitor Railway deployment progress"""
    print_header("MONITORING RAILWAY DEPLOYMENT")
    
    print(f"⏳ Monitoring Railway deployment for up to {max_wait_minutes} minutes...")
    print(f"🔗 URL: {RAILWAY_URL}")
    
    start_time = datetime.now()
    check_interval = 30  # Check every 30 seconds
    
    for attempt in range(0, max_wait_minutes * 60, check_interval):
        elapsed_minutes = attempt / 60
        print(f"\n🔍 Check {int(attempt/check_interval)+1} (after {elapsed_minutes:.1f} minutes)")
        
        responding, routers = check_railway_status()
        
        if responding:
            if 'Portfolio' in routers:
                print(f"🎉 SUCCESS! Portfolio router is now loaded!")
                print(f"📊 All routers: {', '.join(routers)}")
                return True
            else:
                print(f"⏳ Still waiting for Portfolio router...")
                print(f"   Current routers: {', '.join(routers)}")
        else:
            print(f"⏳ Railway still deploying or having issues...")
        
        if attempt + check_interval < max_wait_minutes * 60:
            print(f"⏳ Waiting {check_interval} seconds...")
            time.sleep(check_interval)
    
    print(f"⏰ Monitoring timeout after {max_wait_minutes} minutes")
    return False

def main():
    print_header("RAILWAY REDEPLOY TRIGGER & MONITOR")
    
    print(f"📅 Started: {datetime.now().isoformat()}")
    
    # Check current status
    print(f"\n🔍 Checking current Railway status...")
    responding, current_routers = check_railway_status()
    
    if 'Portfolio' in current_routers:
        print(f"✅ Portfolio router is already loaded!")
        print(f"ℹ️  No redeploy needed")
        return True
    
    print(f"❌ Portfolio router missing. Current routers: {', '.join(current_routers)}")
    print(f"🔄 Triggering redeploy...")
    
    # Trigger redeploy
    if not trigger_redeploy():
        print(f"❌ Failed to trigger redeploy")
        return False
    
    # Monitor deployment
    success = monitor_deployment()
    
    if success:
        print_header("DEPLOYMENT SUCCESS")
        print(f"🎉 Railway redeploy completed successfully!")
        print(f"✅ Portfolio router is now loaded")
        print(f"✅ All integration endpoints should now be available")
        
        # Run integration test
        print(f"\n🧪 Running integration test to verify...")
        try:
            result = subprocess.run(['python3', 'test_complete_frontend_backend_integration.py'], 
                                  capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"✅ Integration test PASSED!")
            else:
                print(f"⚠️  Integration test had issues - check manually")
        except Exception as e:
            print(f"⚠️  Could not run integration test: {str(e)}")
        
    else:
        print_header("DEPLOYMENT TIMEOUT")
        print(f"⏰ Railway deployment monitoring timed out")
        print(f"ℹ️  Railway may still be deploying - check manually")
        print(f"🔗 Check Railway dashboard for deployment status")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)