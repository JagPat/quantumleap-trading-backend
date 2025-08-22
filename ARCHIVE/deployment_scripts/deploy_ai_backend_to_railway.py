#!/usr/bin/env python3
"""
Deploy AI Backend to Railway

This script deploys the fixed backend with AI components to Railway.
"""

import subprocess
import sys
import time
from datetime import datetime

def run_command(command, description=""):
    """Run a shell command and return success status"""
    print(f"\n🔧 {description}")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()[:200]}")
            return True
        else:
            print(f"   ❌ Failed (exit code: {result.returncode})")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout after 5 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        return False

def check_git_status():
    """Check git status and stage changes"""
    print("📋 Checking git status...")
    
    # Check if we have changes
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    
    if result.stdout.strip():
        print("   📝 Changes detected:")
        for line in result.stdout.strip().split('\n'):
            print(f"      {line}")
        return True
    else:
        print("   ✅ No changes to commit")
        return False

def deploy_to_railway():
    """Deploy the backend to Railway"""
    print("🚀 DEPLOYING AI BACKEND TO RAILWAY")
    print("=" * 60)
    print(f"   Timestamp: {datetime.now()}")
    print("=" * 60)
    
    # Check git status
    has_changes = check_git_status()
    
    if has_changes:
        # Stage all changes
        if not run_command("git add .", "Staging all changes"):
            return False
        
        # Commit changes
        commit_message = f"Fix Railway deployment with AI components - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not run_command(f'git commit -m "{commit_message}"', "Committing changes"):
            return False
    
    # Push to Railway (this triggers automatic deployment)
    if not run_command("git push", "Pushing to Railway"):
        return False
    
    print("\n✅ Deployment initiated successfully!")
    print("\n📋 Next Steps:")
    print("   1. Monitor Railway deployment logs")
    print("   2. Wait for health check to pass")
    print("   3. Test AI endpoints once deployment is healthy")
    print("   4. Run AI features integration tests")
    
    return True

def main():
    """Main deployment function"""
    try:
        success = deploy_to_railway()
        
        if success:
            print("\n🎉 AI Backend deployment to Railway initiated!")
            print("\n🔗 Monitor deployment at:")
            print("   https://railway.app/project/your-project-id")
            
            print("\n⏳ Waiting for deployment to complete...")
            print("   This may take 2-3 minutes...")
            
            # Wait a bit for deployment to start
            time.sleep(30)
            
            print("\n🧪 You can now test the deployment with:")
            print("   python3 test_ai_features_integration.py")
            
            sys.exit(0)
        else:
            print("\n💥 AI Backend deployment failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during deployment: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()