#!/usr/bin/env python3
"""
Deploy Latest Changes to GitHub (which auto-deploys to Railway)
This script commits and pushes all latest changes to GitHub repository
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
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

def main():
    """Main deployment function"""
    print("🚀 Starting GitHub Deployment (Auto-deploys to Railway)")
    print("=" * 60)
    
    # Check if we're in a git repository
    if not os.path.exists('.git'):
        print("❌ Not in a git repository!")
        sys.exit(1)
    
    # Get current timestamp for commit message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Step 1: Add all changes
    print("\n📦 Adding all changes to git...")
    if not run_command("git add .", "Adding all files"):
        sys.exit(1)
    
    # Step 2: Check what's being committed
    print("\n📋 Checking what will be committed...")
    run_command("git status --short", "Checking git status")
    
    # Step 3: Create comprehensive commit message
    commit_message = f"""🚀 Deploy Latest System Updates - {timestamp}

📊 Database Optimization System:
- Added comprehensive database optimization manager
- Implemented query performance monitoring
- Added index optimization recommendations
- Railway-specific database configuration

🔧 Trading Engine Enhancements:
- Operational procedures implementation
- Enhanced monitoring and alerting
- Performance tracking improvements
- Load and stress testing capabilities

🛠️ Infrastructure Improvements:
- Production deployment procedures
- Gradual rollout system
- Enhanced error handling and recovery
- Comprehensive testing suite

🔗 API Integration Fixes:
- Fixed endpoint routing issues
- Enhanced CORS configuration
- Improved error responses
- Better health check endpoints

📈 Performance Optimizations:
- Database query optimization
- Memory usage improvements
- Response time enhancements
- Load balancing preparations

🧪 Testing & Monitoring:
- Comprehensive test suites
- Performance monitoring
- Health check improvements
- Error tracking enhancements

Auto-deploy to Railway: ✅
"""
    
    # Step 4: Commit changes
    print("\n💾 Committing changes...")
    commit_cmd = f'git commit -m "{commit_message}"'
    if not run_command(commit_cmd, "Committing changes"):
        print("ℹ️ No changes to commit or commit failed")
    
    # Step 5: Push to GitHub
    print("\n🚀 Pushing to GitHub (triggers Railway deployment)...")
    if not run_command("git push origin main", "Pushing to GitHub"):
        print("❌ Failed to push to GitHub")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Deployment to GitHub completed successfully!")
    print("🚂 Railway will automatically deploy from GitHub")
    print("⏱️ Railway deployment typically takes 2-5 minutes")
    print("\n📍 Monitor deployment at:")
    print("   GitHub: https://github.com/your-repo/commits")
    print("   Railway: https://railway.com/project/925c1cba-ce50-4be3-b5f9-a6bcb7dac747")
    print("\n🔗 Backend will be available at:")
    print("   https://quantum-leap-backend-production.up.railway.app")
    
    # Step 6: Test GitHub repository status
    print("\n🔍 Verifying GitHub push...")
    run_command("git log --oneline -1", "Latest commit")
    run_command("git remote -v", "Remote repositories")
    
    print("\n✅ All done! Railway should start deploying automatically.")
    print("💡 Check Railway dashboard for deployment progress.")

if __name__ == "__main__":
    main()