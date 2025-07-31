#!/usr/bin/env python3
"""
Deploy CORS fix to Railway
"""
import subprocess
import sys
import time

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def test_cors_fix():
    """Test if CORS fix is working"""
    print("🧪 Testing CORS fix...")
    cmd = '''curl -X OPTIONS "https://web-production-de0bc.up.railway.app/api/ai/preferences" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: content-type,authorization,x-user-id" \
  -w "Status: %{http_code}" \
  -s'''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if "Status: 200" in result.stdout:
        print("✅ CORS fix is working!")
        return True
    else:
        print(f"❌ CORS fix not working yet. Response: {result.stdout}")
        return False

def main():
    print("🚀 Deploying CORS fix to Railway...")
    print("=" * 50)
    
    # Check if we have git changes
    if not run_command("git status --porcelain", "Checking for changes"):
        return False
    
    # Add changes
    if not run_command("git add main.py", "Adding main.py changes"):
        return False
    
    # Commit changes
    if not run_command('git commit -m "Fix CORS: Add X-User-ID header to allowed headers"', "Committing changes"):
        return False
    
    # Push to Railway (assuming Railway is connected to git)
    if not run_command("git push", "Pushing to repository"):
        return False
    
    print("\n⏳ Waiting for Railway deployment...")
    print("This may take 1-2 minutes...")
    
    # Wait and test
    for i in range(12):  # Wait up to 2 minutes
        time.sleep(10)
        print(f"   Testing attempt {i+1}/12...")
        if test_cors_fix():
            print("\n🎉 CORS fix deployed successfully!")
            return True
    
    print("\n⚠️ Deployment may still be in progress. Please test manually:")
    print("curl -X OPTIONS \"https://web-production-de0bc.up.railway.app/api/ai/preferences\" \\")
    print("  -H \"Origin: http://localhost:5173\" \\")
    print("  -H \"Access-Control-Request-Method: GET\" \\")
    print("  -H \"Access-Control-Request-Headers: content-type,authorization,x-user-id\" \\")
    print("  -w \"Status: %{http_code}\" -s")
    
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)