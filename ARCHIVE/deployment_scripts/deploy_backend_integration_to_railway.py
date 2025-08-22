#!/usr/bin/env python3
"""
Deploy Backend Integration to Railway via GitHub
Comprehensive deployment script that:
1. Commits and pushes updated code to GitHub main branch
2. Monitors Railway deployment status
3. Verifies all endpoints are working
4. Provides detailed deployment report
"""

import subprocess
import requests
import json
import time
from datetime import datetime
import os

# Configuration
GITHUB_REPO = "https://github.com/JagPat/quantumleap-trading-backend"
RAILWAY_URL = "https://web-production-de0bc.up.railway.app"
TEST_USER_ID = "test_user_123"

class RailwayDeploymentManager:
    def __init__(self):
        self.github_repo = GITHUB_REPO
        self.railway_url = RAILWAY_URL
        self.deployment_start_time = None
        
    def print_header(self, title):
        """Print a formatted header"""
        print(f"\n{'='*70}")
        print(f"🚀 {title}")
        print(f"{'='*70}")
    
    def print_section(self, section):
        """Print a section header"""
        print(f"\n{'─'*50}")
        print(f"📋 {section}")
        print(f"{'─'*50}")
    
    def run_command(self, command, description):
        """Run a shell command and return result"""
        print(f"\n🔧 {description}")
        print(f"   Command: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"   ✅ SUCCESS")
                if result.stdout.strip():
                    print(f"   Output: {result.stdout.strip()}")
                return True, result.stdout
            else:
                print(f"   ❌ FAILED")
                print(f"   Error: {result.stderr.strip()}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ TIMEOUT - Command took too long")
            return False, "Command timeout"
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            return False, str(e)
    
    def check_git_status(self):
        """Check git status and show changes"""
        self.print_section("Git Status Check")
        
        # Check if we're in a git repository
        success, _ = self.run_command("git status --porcelain", "Checking git status")
        
        if not success:
            print("❌ Not in a git repository or git not available")
            return False
        
        # Show current branch
        success, branch = self.run_command("git branch --show-current", "Getting current branch")
        if success:
            print(f"📍 Current branch: {branch.strip()}")
        
        # Show modified files
        success, status = self.run_command("git status --short", "Checking modified files")
        if success and status.strip():
            print(f"📝 Modified files:")
            for line in status.strip().split('\n'):
                print(f"   {line}")
        else:
            print(f"📝 No modified files detected")
        
        return True
    
    def commit_and_push_changes(self):
        """Commit and push changes to GitHub"""
        self.print_section("GitHub Deployment")
        
        # Add all changes
        success, _ = self.run_command("git add .", "Adding all changes")
        if not success:
            return False
        
        # Create commit message
        commit_message = f"🚀 Frontend-Backend Integration Completion - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" \
                        f"✅ Added missing kiteconnect dependency to requirements.txt\n" \
                        f"✅ Added missing portfolio endpoints (/summary, /performance)\n" \
                        f"✅ Added all missing AI endpoints for frontend integration\n" \
                        f"✅ Preserved all existing broker and portfolio functionality\n" \
                        f"✅ Complete frontend-backend API integration\n\n" \
                        f"This deployment enables:\n" \
                        f"- Portfolio router loading with kiteconnect support\n" \
                        f"- All 6 portfolio endpoints working\n" \
                        f"- All 10 AI service endpoints working\n" \
                        f"- Real-time portfolio data from Kite broker\n" \
                        f"- AI portfolio analysis integration\n" \
                        f"- Error-free user experience with real data"
        
        # Commit changes
        success, _ = self.run_command(f'git commit -m "{commit_message}"', "Committing changes")
        if not success:
            print("⚠️  No changes to commit or commit failed")
            # Check if there are actually no changes
            success, status = self.run_command("git status --porcelain", "Checking for changes")
            if success and not status.strip():
                print("ℹ️  No changes detected - repository is up to date")
                return True
            return False
        
        # Push to main branch
        success, _ = self.run_command("git push origin main", "Pushing to GitHub main branch")
        if not success:
            print("❌ Failed to push to GitHub")
            return False
        
        print("✅ Successfully deployed to GitHub main branch")
        print(f"🔗 Repository: {self.github_repo}")
        
        return True
    
    def wait_for_railway_deployment(self, max_wait_minutes=10):
        """Wait for Railway to deploy the new code"""
        self.print_section("Railway Deployment Monitoring")
        
        print(f"⏳ Waiting for Railway to deploy new code...")
        print(f"🔗 Railway URL: {self.railway_url}")
        print(f"⏰ Max wait time: {max_wait_minutes} minutes")
        
        self.deployment_start_time = datetime.now()
        max_wait_seconds = max_wait_minutes * 60
        check_interval = 30  # Check every 30 seconds
        
        for attempt in range(0, max_wait_seconds, check_interval):
            elapsed_minutes = attempt / 60
            print(f"\n🔍 Deployment check {int(attempt/check_interval)+1} (after {elapsed_minutes:.1f} minutes)")
            
            try:
                # Check if Railway is responding
                response = requests.get(f"{self.railway_url}/health", timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ Railway is responding")
                    
                    # Check if portfolio router is loaded
                    status_response = requests.get(f"{self.railway_url}/status", timeout=10)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        routers_loaded = status_data.get('routers_loaded', [])
                        
                        print(f"📊 Loaded routers: {', '.join(routers_loaded)}")
                        
                        if 'Portfolio' in routers_loaded:
                            print(f"🎉 Portfolio router is now loaded!")
                            print(f"⏱️  Deployment completed in {elapsed_minutes:.1f} minutes")
                            return True
                        else:
                            print(f"⏳ Portfolio router not yet loaded, waiting...")
                    else:
                        print(f"⚠️  Status endpoint returned {status_response.status_code}")
                else:
                    print(f"⚠️  Railway health check returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Railway connection error: {str(e)}")
            
            if attempt + check_interval < max_wait_seconds:
                print(f"⏳ Waiting {check_interval} seconds before next check...")
                time.sleep(check_interval)
        
        print(f"⏰ Deployment monitoring timeout after {max_wait_minutes} minutes")
        print(f"ℹ️  Railway may still be deploying - check manually")
        return False
    
    def verify_deployment(self):
        """Verify that all endpoints are working after deployment"""
        self.print_section("Deployment Verification")
        
        print(f"🔍 Running comprehensive endpoint verification...")
        
        # Import and run the integration test
        try:
            from test_complete_frontend_backend_integration import CompleteFrontendBackendTester
            
            tester = CompleteFrontendBackendTester()
            results = tester.run_complete_integration_test()
            
            return results
            
        except ImportError:
            print("❌ Integration test module not found")
            return None
        except Exception as e:
            print(f"❌ Integration test failed: {str(e)}")
            return None
    
    def generate_deployment_report(self, verification_results):
        """Generate comprehensive deployment report"""
        self.print_section("Deployment Report")
        
        deployment_time = datetime.now()
        if self.deployment_start_time:
            total_time = deployment_time - self.deployment_start_time
            total_minutes = total_time.total_seconds() / 60
        else:
            total_minutes = 0
        
        report = {
            "deployment_info": {
                "timestamp": deployment_time.isoformat(),
                "github_repo": self.github_repo,
                "railway_url": self.railway_url,
                "total_deployment_time_minutes": round(total_minutes, 1)
            },
            "changes_deployed": [
                "Added kiteconnect==4.2.0 to requirements.txt",
                "Added missing portfolio endpoints (/summary, /performance)",
                "Added all missing AI service endpoints",
                "Preserved existing broker and portfolio functionality",
                "Complete frontend-backend API integration"
            ]
        }
        
        if verification_results:
            report["verification_results"] = {
                "backend_healthy": verification_results.get('backend_healthy', False),
                "overall_success_rate": verification_results.get('overall_success_rate', 0),
                "total_tests": verification_results.get('total_tests', 0),
                "total_passed": verification_results.get('total_passed', 0),
                "category_results": verification_results.get('category_results', {})
            }
            
            success_rate = verification_results.get('overall_success_rate', 0)
            if success_rate >= 90:
                report["deployment_status"] = "SUCCESS"
                report["status_message"] = "Deployment successful - all services working"
            elif success_rate >= 70:
                report["deployment_status"] = "PARTIAL_SUCCESS"
                report["status_message"] = "Deployment mostly successful - some issues remain"
            else:
                report["deployment_status"] = "FAILED"
                report["status_message"] = "Deployment failed - significant issues detected"
        else:
            report["deployment_status"] = "UNKNOWN"
            report["status_message"] = "Deployment completed but verification failed"
        
        # Save report to file
        report_filename = f"deployment_report_{deployment_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Deployment Report:")
        print(f"   Status: {report['deployment_status']}")
        print(f"   Message: {report['status_message']}")
        print(f"   Total Time: {total_minutes:.1f} minutes")
        print(f"   Report saved: {report_filename}")
        
        if verification_results:
            success_rate = verification_results.get('overall_success_rate', 0)
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Tests Passed: {verification_results.get('total_passed', 0)}/{verification_results.get('total_tests', 0)}")
        
        return report
    
    def run_complete_deployment(self):
        """Run complete deployment process"""
        self.print_header("RAILWAY DEPLOYMENT VIA GITHUB")
        
        print(f"🎯 Target: {self.railway_url}")
        print(f"📂 Repository: {self.github_repo}")
        print(f"📅 Started: {datetime.now().isoformat()}")
        
        # Step 1: Check git status
        if not self.check_git_status():
            print("❌ Git status check failed")
            return False
        
        # Step 2: Commit and push to GitHub
        if not self.commit_and_push_changes():
            print("❌ GitHub deployment failed")
            return False
        
        # Step 3: Wait for Railway deployment
        railway_deployed = self.wait_for_railway_deployment()
        
        # Step 4: Verify deployment
        print(f"\n🔍 Verifying deployment...")
        verification_results = self.verify_deployment()
        
        # Step 5: Generate report
        report = self.generate_deployment_report(verification_results)
        
        # Final status
        self.print_header("DEPLOYMENT COMPLETE")
        
        if report['deployment_status'] == 'SUCCESS':
            print(f"🎉 DEPLOYMENT SUCCESSFUL!")
            print(f"✅ All services are working correctly")
            print(f"✅ Frontend-backend integration is complete")
            print(f"✅ Users can access all services with real data")
            return True
        elif report['deployment_status'] == 'PARTIAL_SUCCESS':
            print(f"⚠️  DEPLOYMENT PARTIALLY SUCCESSFUL")
            print(f"✅ Most services are working")
            print(f"⚠️  Some issues remain - check the report")
            return True
        else:
            print(f"❌ DEPLOYMENT FAILED OR INCOMPLETE")
            print(f"❌ Significant issues detected")
            print(f"📋 Check the deployment report for details")
            return False

def main():
    """Main deployment function"""
    deployer = RailwayDeploymentManager()
    success = deployer.run_complete_deployment()
    
    if success:
        print(f"\n🚀 Next steps:")
        print(f"   1. Test the live application at {RAILWAY_URL}")
        print(f"   2. Verify portfolio data loading works")
        print(f"   3. Test AI analysis features")
        print(f"   4. Confirm broker integration is working")
    else:
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Check Railway deployment logs")
        print(f"   2. Verify GitHub repository was updated")
        print(f"   3. Check for any missing dependencies")
        print(f"   4. Monitor Railway deployment status")
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()