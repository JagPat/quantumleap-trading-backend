#!/usr/bin/env python3
"""
Deploy AI Service Fix to Railway
"""
import subprocess
import time

def deploy_fix():
    """Deploy the AI service fix to Railway"""
    print("🚀 Deploying AI Service Fix to Railway")
    print("=" * 50)
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(['git', 'status'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Not in a git repository")
            return False
        
        # Add the changed file
        print("1. Adding changed files...")
        subprocess.run(['git', 'add', 'app/ai_engine/service.py'], check=True)
        
        # Commit the changes
        print("2. Committing changes...")
        commit_message = "Fix AIService import issue - add alias for backward compatibility"
        result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ Changes committed successfully")
        else:
            print(f"   ⚠️ Commit result: {result.stdout}")
            if "nothing to commit" in result.stdout:
                print("   No changes to commit")
            else:
                print("   Proceeding with deployment...")
        
        # Push to Railway (assuming main branch)
        print("3. Pushing to Railway...")
        result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ Pushed to Railway successfully")
            print("   🔄 Railway will automatically deploy the changes")
            
            # Wait for deployment
            print("\\n4. Waiting for deployment to complete...")
            for i in range(30):
                print(f"   Waiting... {i+1}/30 seconds", end='\\r')
                time.sleep(1)
            print("\\n   ⏰ Deployment should be complete")
            
            return True
        else:
            print(f"   ❌ Push failed: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_deployment():
    """Test if the deployment worked"""
    print("\\n🧪 Testing Deployment")
    print("=" * 30)
    
    import requests
    import json
    
    try:
        # Test the portfolio analysis endpoint
        response = requests.post(
            "https://web-production-de0bc.up.railway.app/api/ai/simple-analysis/portfolio",
            headers={
                "Content-Type": "application/json",
                "X-User-ID": "EBW183"
            },
            json={
                "total_value": 1000000,
                "holdings": [
                    {
                        "symbol": "RELIANCE",
                        "quantity": 100,
                        "current_value": 250000
                    }
                ]
            },
            timeout=10
        )
        
        result = response.json()
        print(f"Status: {result.get('status')}")
        print(f"Fallback mode: {result.get('fallback_mode')}")
        print(f"Provider used: {result.get('provider_used')}")
        print(f"Message: {result.get('message')}")
        
        if result.get('fallback_mode') == False:
            print("\\n🎉 SUCCESS! Real AI analysis is now working!")
            return True
        else:
            print("\\n⚠️ Still using fallback mode - may need more debugging")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("This script will deploy the AI service fix to Railway")
    print("Make sure you have:")
    print("1. Git configured with Railway remote")
    print("2. Proper access to push to the repository")
    print()
    
    confirm = input("Continue with deployment? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Deployment cancelled")
        exit(0)
    
    # Deploy the fix
    if deploy_fix():
        # Test the deployment
        test_deployment()
    else:
        print("\\n❌ Deployment failed")