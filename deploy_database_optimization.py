"""
Deploy Database Optimization to Railway

This script deploys the optimized database system to Railway with
proper configuration and health checks.
"""

import os
import sys
import subprocess
import json
import time
import requests
from typing import Dict, Any, List

def check_railway_cli():
    """Check if Railway CLI is available"""
    try:
        result = subprocess.run(['railway', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Railway CLI available: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Railway CLI not found. Please install it first:")
        print("   npm install -g @railway/cli")
        return False

def check_git_status():
    """Check git status and ensure changes are committed"""
    try:
        # Check if there are uncommitted changes
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print("⚠️  Uncommitted changes detected:")
            print(result.stdout)
            
            response = input("Do you want to commit these changes? (y/n): ")
            if response.lower() == 'y':
                # Add all changes
                subprocess.run(['git', 'add', '.'], check=True)
                
                # Commit with automated message
                commit_message = "Deploy database optimization system to Railway"
                subprocess.run(['git', 'commit', '-m', commit_message], check=True)
                print("✅ Changes committed")
            else:
                print("❌ Please commit your changes before deploying")
                return False
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")
        return False

def update_requirements():
    """Update requirements.txt with database optimization dependencies"""
    requirements = [
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "psycopg2-binary>=2.9.7",  # For Railway PostgreSQL
        "python-multipart>=0.0.6",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
        "pytest>=7.4.3",
        "pytest-asyncio>=0.21.1"
    ]
    
    try:
        with open('requirements.txt', 'w') as f:
            f.write('\n'.join(requirements))
        
        print("✅ Updated requirements.txt with database dependencies")
        return True
    except Exception as e:
        print(f"❌ Failed to update requirements.txt: {e}")
        return False

def create_railway_config():
    """Create Railway-specific configuration files"""
    
    # Create railway.json for deployment configuration
    railway_config = {
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
            "healthcheckPath": "/health",
            "healthcheckTimeout": 300,
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 3
        }
    }
    
    try:
        with open('railway.json', 'w') as f:
            json.dump(railway_config, f, indent=2)
        
        print("✅ Created railway.json configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create railway.json: {e}")
        return False

def update_main_app():
    """Update main.py to include database optimization routes"""
    
    main_app_addition = '''
# Database Optimization Routes
from app.database.optimized_manager import get_database_manager
from app.database.railway_config import RailwayDatabaseUtils

@app.get("/api/database/health")
async def database_health():
    """Get database health status"""
    try:
        return RailwayDatabaseUtils.check_railway_database_health()
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/database/metrics")
async def database_metrics():
    """Get database performance metrics"""
    try:
        db_manager = get_database_manager()
        return db_manager.get_performance_metrics()
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/database/optimize")
async def optimize_database():
    """Run database optimization"""
    try:
        success = RailwayDatabaseUtils.optimize_for_railway()
        return {"status": "success" if success else "failed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
'''
    
    try:
        # Read current main.py
        with open('main.py', 'r') as f:
            content = f.read()
        
        # Check if database routes already exist
        if '/api/database/health' not in content:
            # Add database routes before the last line
            lines = content.split('\n')
            
            # Find a good place to insert (before any existing route definitions end)
            insert_index = len(lines)
            for i, line in enumerate(lines):
                if line.strip() == '' and i > len(lines) - 10:
                    insert_index = i
                    break
            
            # Insert the new routes
            lines.insert(insert_index, main_app_addition)
            
            # Write back to file
            with open('main.py', 'w') as f:
                f.write('\n'.join(lines))
            
            print("✅ Added database optimization routes to main.py")
        else:
            print("✅ Database routes already exist in main.py")
        
        return True
    except Exception as e:
        print(f"❌ Failed to update main.py: {e}")
        return False

def run_tests():
    """Run database optimization tests"""
    print("🧪 Running database optimization tests...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'test_database_optimization.py', 
            '-v', '--tb=short'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out")
        return False
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def deploy_to_railway():
    """Deploy to Railway"""
    print("🚀 Deploying to Railway...")
    
    try:
        # Push to Railway
        result = subprocess.run(['railway', 'up'], 
                              capture_output=True, text=True, check=True)
        
        print("✅ Deployment initiated")
        print(result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Railway deployment failed: {e}")
        print(e.stdout)
        print(e.stderr)
        return False

def wait_for_deployment():
    """Wait for deployment to complete and check health"""
    print("⏳ Waiting for deployment to complete...")
    
    # Get Railway service URL
    try:
        result = subprocess.run(['railway', 'status'], 
                              capture_output=True, text=True, check=True)
        
        # Extract URL from status (this is a simplified approach)
        lines = result.stdout.split('\n')
        service_url = None
        
        for line in lines:
            if 'https://' in line and 'railway.app' in line:
                # Extract URL
                parts = line.split()
                for part in parts:
                    if part.startswith('https://') and 'railway.app' in part:
                        service_url = part
                        break
                break
        
        if not service_url:
            print("⚠️  Could not extract service URL from Railway status")
            return False
        
        print(f"🌐 Service URL: {service_url}")
        
        # Wait for service to be ready
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{service_url}/health", timeout=10)
                if response.status_code == 200:
                    print("✅ Service is healthy")
                    
                    # Test database health endpoint
                    db_response = requests.get(f"{service_url}/api/database/health", timeout=10)
                    if db_response.status_code == 200:
                        db_health = db_response.json()
                        print("✅ Database optimization system is healthy")
                        print(f"   Database type: {db_health.get('connection_info', {}).get('type', 'unknown')}")
                        return True
                    else:
                        print(f"⚠️  Database health check failed: {db_response.status_code}")
                        return False
                        
            except requests.RequestException:
                pass
            
            print(f"⏳ Waiting for service... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(10)
        
        print("❌ Service did not become healthy within timeout")
        return False
        
    except Exception as e:
        print(f"❌ Failed to check deployment status: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Railway Database Optimization Deployment")
    print("=" * 50)
    
    # Pre-deployment checks
    if not check_railway_cli():
        return False
    
    if not check_git_status():
        return False
    
    # Update configuration files
    if not update_requirements():
        return False
    
    if not create_railway_config():
        return False
    
    if not update_main_app():
        return False
    
    # Run tests
    if not run_tests():
        response = input("Tests failed. Continue with deployment? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # Commit configuration changes
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add Railway database optimization configuration'], check=True)
        print("✅ Configuration changes committed")
    except subprocess.CalledProcessError:
        print("ℹ️  No new changes to commit")
    
    # Deploy to Railway
    if not deploy_to_railway():
        return False
    
    # Wait for deployment and verify
    if not wait_for_deployment():
        print("⚠️  Deployment may have issues, please check Railway dashboard")
        return False
    
    print("\n🎉 Database Optimization Deployment Complete!")
    print("\n📊 Available Endpoints:")
    print("   GET  /api/database/health   - Database health status")
    print("   GET  /api/database/metrics  - Performance metrics")
    print("   POST /api/database/optimize - Run optimization")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)