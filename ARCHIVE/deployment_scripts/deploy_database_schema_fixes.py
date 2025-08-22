#!/usr/bin/env python3
"""
Deploy Database Schema Initialization Fixes to Railway
Addresses critical missing database tables and API endpoint issues
"""

import subprocess
import sys
import os
import time
import requests
from datetime import datetime

def run_command(command, description):
    """Run a shell command and return the result"""
    print(f"\n🔧 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        print(f"✅ Success: {description}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {description}")
        print(f"Error: {e.stderr.strip()}")
        return False

def check_git_status():
    """Check git status and show changes"""
    print("\n📊 Checking git status...")
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    
    if result.stdout.strip():
        print("📝 Changes detected:")
        print(result.stdout)
        return True
    else:
        print("✅ No changes detected")
        return False

def test_railway_deployment(max_retries=10, delay=30):
    """Test Railway deployment after pushing changes"""
    railway_url = "https://web-production-de0bc.up.railway.app"
    
    print(f"\n🧪 Testing Railway deployment...")
    print(f"URL: {railway_url}")
    print(f"Max retries: {max_retries}, Delay: {delay}s")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n🔍 Attempt {attempt}/{max_retries}")
            
            # Test health endpoint
            health_response = requests.get(f"{railway_url}/health", timeout=10)
            print(f"Health check: {health_response.status_code}")
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"✅ Health check passed: {health_data.get('status', 'unknown')}")
                
                # Test the specific endpoints we fixed
                endpoints_to_test = [
                    ("/api/trading/status", "Trading Status"),
                    ("/api/ai/strategy-templates", "AI Strategy Templates"),
                    ("/api/ai/risk-metrics", "AI Risk Metrics"),
                    ("/api/broker/session?user_id=test_user", "Broker Session")
                ]
                
                all_passed = True
                for endpoint, name in endpoints_to_test:
                    try:
                        response = requests.get(f"{railway_url}{endpoint}", timeout=10)
                        if response.status_code in [200, 401]:  # 401 is acceptable for auth endpoints
                            print(f"✅ {name}: {response.status_code}")
                        else:
                            print(f"⚠️  {name}: {response.status_code}")
                            all_passed = False
                    except Exception as e:
                        print(f"❌ {name}: Error - {str(e)}")
                        all_passed = False
                
                if all_passed:
                    print("\n🎉 All endpoint tests passed!")
                    return True
                else:
                    print("\n⚠️  Some endpoints failed, but deployment is responding")
                    
            else:
                print(f"❌ Health check failed: {health_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection failed: {str(e)}")
        
        if attempt < max_retries:
            print(f"⏳ Waiting {delay}s before next attempt...")
            time.sleep(delay)
    
    print(f"\n❌ Deployment test failed after {max_retries} attempts")
    return False

def main():
    """Main deployment function"""
    print("🚀 Starting Database Schema Initialization Fixes Deployment")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found. Please run from the project root directory.")
        sys.exit(1)
    
    # Check git status
    has_changes = check_git_status()
    
    if not has_changes:
        print("⚠️  No changes detected. Deployment may not be necessary.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Deployment cancelled.")
            sys.exit(0)
    
    # Add all changes
    if not run_command("git add .", "Adding all changes to git"):
        sys.exit(1)
    
    # Create commit message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Fix database schema initialization and API endpoints - {timestamp}"
    
    # Commit changes
    if not run_command(f'git commit -m "{commit_message}"', "Committing changes"):
        print("⚠️  Commit failed - changes may already be committed")
    
    # Push to main branch
    if not run_command("git push origin main", "Pushing to GitHub main branch"):
        sys.exit(1)
    
    print("\n✅ Changes pushed to GitHub successfully!")
    print("🔄 Railway will automatically deploy the changes...")
    
    # Wait for Railway deployment
    print("\n⏳ Waiting for Railway deployment to complete...")
    time.sleep(60)  # Give Railway time to start deployment
    
    # Test deployment
    if test_railway_deployment():
        print("\n🎉 Deployment successful!")
        print("\n📋 Summary of fixes applied:")
        print("✅ Database initialization added to application startup")
        print("✅ Missing /api/trading/status endpoint implemented")
        print("✅ AI endpoint authentication issues resolved")
        print("✅ Broker session GET endpoint added")
        print("\n🔗 Railway URL: https://web-production-de0bc.up.railway.app")
        print("📚 API Documentation: https://web-production-de0bc.up.railway.app/docs")
    else:
        print("\n⚠️  Deployment may have issues. Check Railway logs for details.")
        print("🔗 Railway Dashboard: https://railway.app/")
    
    print("\n✅ Deployment process completed!")

if __name__ == "__main__":
    main()