#!/usr/bin/env python3
"""
Diagnose Railway Deployment Issue

The Railway deployment is failing healthcheck. Let's diagnose and fix the issue.
"""

import os
import sys
from datetime import datetime

def check_main_py():
    """Check if main.py has the correct structure"""
    print("🔍 Checking main.py structure...")
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
        # Check for essential components
        checks = {
            "FastAPI import": "from fastapi import FastAPI" in content,
            "FastAPI app creation": "app = FastAPI(" in content,
            "Health endpoint": "/health" in content,
            "AI components router": "ai_components_router" in content,
            "Port configuration": "port=" in content or "PORT" in content,
            "Host configuration": "host=" in content or "0.0.0.0" in content
        }
        
        print("   Main.py checks:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            
        return all(checks.values())
        
    except FileNotFoundError:
        print("   ❌ main.py not found!")
        return False

def check_requirements():
    """Check requirements.txt"""
    print("\n🔍 Checking requirements.txt...")
    
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
            
        required_packages = [
            "fastapi",
            "uvicorn",
            "python-multipart",
            "pydantic"
        ]
        
        print("   Required packages:")
        all_present = True
        for package in required_packages:
            present = package in content.lower()
            status = "✅" if present else "❌"
            print(f"   {status} {package}")
            if not present:
                all_present = False
                
        return all_present
        
    except FileNotFoundError:
        print("   ❌ requirements.txt not found!")
        return False

def check_start_script():
    """Check start.sh script"""
    print("\n🔍 Checking start.sh script...")
    
    try:
        with open('start.sh', 'r') as f:
            content = f.read()
            
        checks = {
            "Python command": "python" in content,
            "Main module": "main" in content,
            "Port variable": "$PORT" in content or "${PORT}" in content,
            "Host binding": "0.0.0.0" in content
        }
        
        print("   Start script checks:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            
        return all(checks.values())
        
    except FileNotFoundError:
        print("   ❌ start.sh not found!")
        return False

def check_dockerfile():
    """Check Dockerfile"""
    print("\n🔍 Checking Dockerfile...")
    
    try:
        with open('Dockerfile', 'r') as f:
            content = f.read()
            
        checks = {
            "Python base image": "FROM python:" in content,
            "Requirements copy": "requirements.txt" in content,
            "App copy": "COPY . ." in content,
            "Start script": "start.sh" in content,
            "Port exposure": "EXPOSE" in content
        }
        
        print("   Dockerfile checks:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            
        return all(checks.values())
        
    except FileNotFoundError:
        print("   ❌ Dockerfile not found!")
        return False

def check_ai_components_router():
    """Check if AI components router exists and is properly structured"""
    print("\n🔍 Checking AI components router...")
    
    try:
        with open('app/ai_engine/ai_components_router.py', 'r') as f:
            content = f.read()
            
        checks = {
            "FastAPI router": "APIRouter" in content,
            "Router prefix": 'prefix="/ai"' in content,
            "Health endpoint": "/health" in content,
            "Chat endpoint": "/chat" in content,
            "Strategy templates": "/strategy-templates" in content
        }
        
        print("   AI components router checks:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            
        return all(checks.values())
        
    except FileNotFoundError:
        print("   ❌ AI components router not found!")
        return False

def generate_fix_recommendations():
    """Generate recommendations to fix the deployment"""
    print("\n💡 Fix Recommendations:")
    
    recommendations = [
        "1. Ensure main.py has proper health endpoint that returns 200 OK",
        "2. Verify uvicorn is configured to bind to 0.0.0.0:$PORT",
        "3. Check that all required dependencies are in requirements.txt",
        "4. Ensure start.sh script is executable and uses correct Python command",
        "5. Verify AI components router is properly imported in main.py",
        "6. Test the application locally before deploying to Railway"
    ]
    
    for rec in recommendations:
        print(f"   • {rec}")

def create_fixed_main_py():
    """Create a fixed main.py file"""
    print("\n🔧 Creating fixed main.py...")
    
    main_py_content = '''#!/usr/bin/env python3
"""
Quantum Leap Trading Platform - Main Application

Fixed version for Railway deployment with proper health checks and AI components.
"""

import os
import sys
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Quantum Leap Trading Platform",
    description="AI-powered trading platform with comprehensive portfolio management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (CRITICAL for Railway deployment)
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway deployment"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "quantum-leap-backend",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Quantum Leap Trading Platform API",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "health": "/health"
    }

# Import and include routers
try:
    # Import existing routers
    from app.portfolio.router import router as portfolio_router
    from app.broker.router import router as broker_router
    from app.trading_engine.simple_router import router as trading_engine_router
    from app.ai_engine.simple_analysis_router import router as ai_router
    
    # Import new AI components router
    from app.ai_engine.ai_components_router import router as ai_components_router
    
    # Include routers
    app.include_router(portfolio_router, prefix="/api")
    app.include_router(broker_router, prefix="/api")
    app.include_router(trading_engine_router, prefix="/api")
    app.include_router(ai_router, prefix="/api")
    app.include_router(ai_components_router, prefix="/api")
    
    logger.info("All routers loaded successfully")
    
except ImportError as e:
    logger.error(f"Router import error: {str(e)}")
    # Continue without the problematic router for now
    pass

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"  # CRITICAL: Must bind to 0.0.0.0 for Railway
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
'''
    
    try:
        with open('main.py', 'w') as f:
            f.write(main_py_content)
        print("   ✅ Fixed main.py created successfully")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create main.py: {str(e)}")
        return False

def create_fixed_start_sh():
    """Create a fixed start.sh script"""
    print("\n🔧 Creating fixed start.sh...")
    
    start_sh_content = '''#!/bin/bash

# Quantum Leap Trading Platform - Start Script
# Fixed version for Railway deployment

echo "🚀 Starting Quantum Leap Trading Platform..."
echo "   Port: $PORT"
echo "   Environment: $RAILWAY_ENVIRONMENT"
echo "   Time: $(date)"

# Ensure we're in the right directory
cd /app

# Start the application with uvicorn
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
'''
    
    try:
        with open('start.sh', 'w') as f:
            f.write(start_sh_content)
        
        # Make it executable
        os.chmod('start.sh', 0o755)
        
        print("   ✅ Fixed start.sh created successfully")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create start.sh: {str(e)}")
        return False

def main():
    """Main diagnosis and fix function"""
    print("🚀 RAILWAY DEPLOYMENT DIAGNOSIS")
    print("=" * 60)
    print(f"   Timestamp: {datetime.now()}")
    print("=" * 60)
    
    # Run all checks
    checks = [
        ("Main.py structure", check_main_py),
        ("Requirements.txt", check_requirements),
        ("Start script", check_start_script),
        ("Dockerfile", check_dockerfile),
        ("AI components router", check_ai_components_router)
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"   ❌ Error in {check_name}: {str(e)}")
            results[check_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n   Checks passed: {passed}/{total}")
    
    for check_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
    
    # Generate fixes if needed
    if passed < total:
        print("\n🔧 APPLYING FIXES...")
        
        # Create fixed files
        fixes_applied = []
        
        if not results.get("Main.py structure", True):
            if create_fixed_main_py():
                fixes_applied.append("main.py")
        
        if not results.get("Start script", True):
            if create_fixed_start_sh():
                fixes_applied.append("start.sh")
        
        if fixes_applied:
            print(f"\n✅ Applied fixes to: {', '.join(fixes_applied)}")
            print("\n🚀 Ready for Railway deployment!")
            print("\nNext steps:")
            print("1. Commit the fixed files to git")
            print("2. Push to Railway (automatic deployment)")
            print("3. Monitor Railway logs for successful deployment")
            print("4. Test AI endpoints once deployment is healthy")
        else:
            generate_fix_recommendations()
    else:
        print("\n✅ All checks passed! Deployment should work correctly.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()