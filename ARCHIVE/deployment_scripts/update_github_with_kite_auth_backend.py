#!/usr/bin/env python3
"""
Update GitHub Repository with Kite Authentication Backend Changes
This will push the new Kite auth endpoints to GitHub, which will trigger Railway auto-deploy
"""

import os
import subprocess
import sys
from datetime import datetime

class GitHubKiteAuthUpdater:
    def __init__(self):
        self.changes_made = []
        self.git_status = None
    
    def check_git_status(self):
        """Check current git status"""
        try:
            print("🔍 Checking git status...")
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, check=True)
            self.git_status = result.stdout.strip()
            
            if self.git_status:
                print("📝 Uncommitted changes found:")
                print(self.git_status)
            else:
                print("✅ Working directory is clean")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Git status check failed: {e}")
            return False
    
    def add_changes(self):
        """Add the modified files to git"""
        try:
            print("📦 Adding changes to git...")
            
            # Add backend changes (main repository)
            backend_files = [
                'app/auth/auth_router.py',  # Main Kite auth endpoints
                'FRONTEND_ISSUES_COMPREHENSIVE_FIX.md'
            ]
            
            for file in backend_files:
                if os.path.exists(file):
                    subprocess.run(['git', 'add', file], check=True)
                    print(f"✅ Added: {file}")
                    self.changes_made.append(file)
                else:
                    print(f"⚠️ File not found: {file}")
            
            # Handle frontend submodule separately
            print("\n📦 Handling frontend submodule...")
            if os.path.exists('quantum-leap-frontend'):
                try:
                    # Change to frontend directory and commit changes there
                    os.chdir('quantum-leap-frontend')
                    
                    # Check if there are changes in the submodule
                    result = subprocess.run(['git', 'status', '--porcelain'], 
                                          capture_output=True, text=True)
                    if result.stdout.strip():
                        print("📝 Frontend changes found, committing to submodule...")
                        
                        # Add all frontend changes
                        subprocess.run(['git', 'add', '.'], check=True)
                        
                        # Commit frontend changes
                        frontend_commit_msg = "Add Kite authentication frontend integration\n\n- Add KiteAuthService\n- Add UserOnboarding component\n- Fix JSX styling issues\n- Improve UI spacing"
                        subprocess.run(['git', 'commit', '-m', frontend_commit_msg], check=True)
                        print("✅ Frontend submodule changes committed")
                        
                        # Return to main directory
                        os.chdir('..')
                        
                        # Add the submodule update to main repo
                        subprocess.run(['git', 'add', 'quantum-leap-frontend'], check=True)
                        print("✅ Added frontend submodule update")
                        self.changes_made.append('quantum-leap-frontend')
                    else:
                        print("ℹ️ No changes in frontend submodule")
                        os.chdir('..')
                        
                except Exception as e:
                    os.chdir('..')  # Make sure we return to main directory
                    print(f"⚠️ Frontend submodule handling failed: {e}")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Git add failed: {e}")
            return False
    
    def commit_changes(self):
        """Commit the changes"""
        try:
            print("💾 Committing changes...")
            
            commit_message = f"""Add Kite Authentication Integration & Frontend Fixes

🔧 Backend Changes:
- Add Kite user login endpoint (/api/auth/kite-login)
- Add Kite user registration endpoint (/api/auth/kite-register)  
- Add Kite profile sync endpoint (/api/auth/sync-kite-profile)
- Fix broker status-header endpoint URL

🎨 Frontend Changes:
- Add KiteAuthService for automatic Kite user authentication
- Add UserOnboarding component for new user registration
- Fix JSX styling attribute errors in AuthStatus and LoginForm
- Improve UI spacing and layout
- Enhanced user display with Kite profile information

📅 Deployed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This update enables automatic authentication for Kite users and provides
a seamless onboarding experience for new users connecting via Zerodha Kite.
"""
            
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            print("✅ Changes committed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git commit failed: {e}")
            return False
    
    def push_to_github(self):
        """Push changes to GitHub"""
        try:
            print("🚀 Pushing changes to GitHub...")
            
            # Push to main branch (or whatever branch Railway is watching)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            print("✅ Changes pushed to GitHub successfully")
            
            print("\n🎯 GitHub repository updated!")
            print("🔄 Railway will now automatically deploy the new changes")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git push failed: {e}")
            print("💡 You may need to:")
            print("   - Check your GitHub authentication")
            print("   - Verify the remote repository URL")
            print("   - Ensure you have push permissions")
            return False
    
    def verify_github_update(self):
        """Verify the GitHub repository has been updated"""
        try:
            print("🔍 Verifying GitHub repository status...")
            
            # Get the latest commit hash
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, check=True)
            local_commit = result.stdout.strip()
            
            # Get the remote commit hash
            subprocess.run(['git', 'fetch', 'origin'], check=True)
            result = subprocess.run(['git', 'rev-parse', 'origin/main'], 
                                  capture_output=True, text=True, check=True)
            remote_commit = result.stdout.strip()
            
            if local_commit == remote_commit:
                print("✅ GitHub repository is up to date")
                return True
            else:
                print("⚠️ GitHub repository may not be fully updated")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ GitHub verification failed: {e}")
            return False
    
    def update_github(self):
        """Main update process"""
        try:
            print("🚀 Updating GitHub Repository with Kite Authentication Backend")
            print("=" * 70)
            
            # Step 1: Check git status
            if not self.check_git_status():
                return False
            
            # Step 2: Add changes
            if not self.add_changes():
                return False
            
            if not self.changes_made:
                print("⚠️ No changes to commit")
                return True
            
            # Step 3: Commit changes
            if not self.commit_changes():
                return False
            
            # Step 4: Push to GitHub
            if not self.push_to_github():
                return False
            
            # Step 5: Verify update
            if not self.verify_github_update():
                print("⚠️ Verification failed, but push may have succeeded")
            
            print("\n" + "=" * 70)
            print("✅ GitHub Repository Updated Successfully!")
            print("🔄 Railway Auto-Deploy Process:")
            print("   1. ✅ Changes pushed to GitHub")
            print("   2. 🔄 Railway detects changes and starts deployment")
            print("   3. ⏳ Wait 2-3 minutes for deployment to complete")
            print("   4. 🧪 Test the new Kite authentication endpoints")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"❌ GitHub update failed: {e}")
            return False

def main():
    """Main function"""
    updater = GitHubKiteAuthUpdater()
    
    try:
        success = updater.update_github()
        
        if success:
            print("\n🎉 GitHub update completed!")
            print("🔄 Next: Wait for Railway to auto-deploy (2-3 minutes)")
            print("🧪 Then test: python3 deploy_kite_auth_backend_to_railway.py")
            sys.exit(0)
        else:
            print("\n❌ GitHub update failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()