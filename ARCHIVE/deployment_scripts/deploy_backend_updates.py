#!/usr/bin/env python3
"""
Backend Deployment Updates and Fixes
Fixes Pydantic compatibility and ensures all backend components are properly deployed
"""

import os
import sys
import shutil
from pathlib import Path

def fix_pydantic_imports():
    """Fix Pydantic imports for compatibility with newer versions"""
    print("🔧 Fixing Pydantic imports for Railway deployment...")
    
    # Files that need Pydantic import fixes
    files_to_fix = [
        "app/core/config.py",
        "app/ai_engine/portfolio_models.py",
        "app/trading_engine/models.py"
    ]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"  📝 Fixing {file_path}")
            
            # Read the file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Fix the imports
            content = content.replace(
                "from pydantic import BaseSettings",
                "try:\n    from pydantic_settings import BaseSettings\nexcept ImportError:\n    from pydantic import BaseSettings"
            )
            
            # Write back the fixed content
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"  ✅ Fixed imports in {file_path}")
        else:
            print(f"  ⚠️ File not found: {file_path}")

def update_requirements():
    """Update requirements.txt with proper dependencies"""
    print("📦 Updating requirements.txt for Railway deployment...")
    
    requirements = [
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",  # Add pydantic-settings
        "python-multipart>=0.0.6",
        "requests>=2.31.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.23",
        "alembic>=1.13.1",
        "redis>=5.0.1",
        "celery>=5.3.4",
        "numpy>=1.24.3",
        "pandas>=2.0.3",
        "scikit-learn>=1.3.0",
        "openai>=1.3.0",
        "anthropic>=0.7.0",
        "google-generativeai>=0.3.0",
        "psutil>=5.9.6"  # Add psutil for monitoring
    ]
    
    with open("requirements.txt", "w") as f:
        for req in requirements:
            f.write(f"{req}\n")
    
    print("✅ Updated requirements.txt")

def create_railway_config():
    """Create Railway-specific configuration"""
    print("🚂 Creating Railway configuration...")
    
    # Create railway.json
    railway_config = {
        "$schema": "https://railway.app/railway.schema.json",
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "python3 main.py",
            "healthcheckPath": "/health",
            "healthcheckTimeout": 300,
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 3
        }
    }
    
    import json
    with open("railway.json", "w") as f:
        json.dump(railway_config, f, indent=2)
    
    # Create Procfile
    with open("Procfile", "w") as f:
        f.write("web: python3 main.py\n")
    
    print("✅ Created Railway configuration files")

def ensure_main_py_exists():
    """Ensure main.py exists and is properly configured"""
    print("🐍 Ensuring main.py is properly configured...")
    
    if not os.path.exists("main.py"):
        print("  📝 Creating main.py...")
        
        main_py_content = '''#!/usr/bin/env python3
"""
Main application entry point for Quantum Leap Backend
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    # Import routers with error handling
    routers_to_include = []
    
    try:
        from app.ai_engine.analysis_router import ai_analysis_router
        routers_to_include.append(("ai_analysis_router", ai_analysis_router, "/api/ai", ["AI Analysis"]))
        logger.info("✅ AI Analysis router loaded")
    except Exception as e:
        logger.warning(f"⚠️ AI Analysis router not available: {e}")
    
    try:
        from app.portfolio.service import portfolio_router
        routers_to_include.append(("portfolio_router", portfolio_router, "/api/portfolio", ["Portfolio"]))
        logger.info("✅ Portfolio router loaded")
    except Exception as e:
        logger.warning(f"⚠️ Portfolio router not available: {e}")
    
    try:
        from app.trading_engine.router import trading_engine_router
        routers_to_include.append(("trading_engine_router", trading_engine_router, "/api/trading-engine", ["Trading Engine"]))
        logger.info("✅ Trading Engine router loaded")
    except Exception as e:
        logger.warning(f"⚠️ Trading Engine router not available: {e}")
    
    # Create FastAPI app
    app = FastAPI(
        title="Quantum Leap Backend API",
        description="Automated Trading and Portfolio Management System",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://quantum-leap-frontend.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://quantum-leap-frontend-git-main-jagrut-patels-projects.vercel.app"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include available routers
    for router_name, router, prefix, tags in routers_to_include:
        try:
            app.include_router(router, prefix=prefix, tags=tags)
            logger.info(f"✅ Included {router_name} at {prefix}")
        except Exception as e:
            logger.error(f"❌ Failed to include {router_name}: {e}")
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Quantum Leap Backend API",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [prefix for _, _, prefix, _ in routers_to_include]
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Railway"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
        }
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler"""
        logger.error(f"Global exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    if __name__ == "__main__":
        import uvicorn
        
        port = int(os.getenv("PORT", 8000))
        host = "0.0.0.0"
        
        logger.info(f"🚀 Starting Quantum Leap Backend on {host}:{port}")
        logger.info(f"📊 Available routers: {len(routers_to_include)}")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )

except ImportError as e:
    logger.error(f"❌ Failed to import required modules: {e}")
    logger.info("🔧 This might be due to missing dependencies. Please check requirements.txt")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Failed to start application: {e}")
    sys.exit(1)
'''
        
        with open("main.py", "w") as f:
            f.write(main_py_content)
        
        print("  ✅ Created main.py")
    else:
        print("  ✅ main.py already exists")

def fix_config_file():
    """Fix app/core/config.py for Railway deployment"""
    print("⚙️ Fixing configuration file...")
    
    config_dir = Path("app/core")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_content = '''"""
Application Configuration
"""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        # Fallback for older versions
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "sqlite:///./quantum_leap.db"
    
    # API Keys (optional)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Kite Connect (optional)
    kite_api_key: Optional[str] = None
    kite_api_secret: Optional[str] = None
    
    # Environment
    environment: str = "production"
    debug: bool = False
    
    # CORS
    cors_origins: list = [
        "https://quantum-leap-frontend.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
'''
    
    with open("app/core/config.py", "w") as f:
        f.write(config_content)
    
    # Ensure __init__.py exists
    with open("app/core/__init__.py", "w") as f:
        f.write("")
    
    print("✅ Fixed configuration file")

def create_init_files():
    """Create necessary __init__.py files"""
    print("📁 Creating __init__.py files...")
    
    init_dirs = [
        "app",
        "app/core",
        "app/ai_engine",
        "app/portfolio",
        "app/trading_engine",
        "app/broker",
        "app/database"
    ]
    
    for dir_path in init_dirs:
        os.makedirs(dir_path, exist_ok=True)
        init_file = os.path.join(dir_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")
            print(f"  ✅ Created {init_file}")

def test_imports():
    """Test if all imports work correctly"""
    print("🧪 Testing imports...")
    
    try:
        # Test pydantic imports
        try:
            from pydantic_settings import BaseSettings
            print("  ✅ pydantic_settings import successful")
        except ImportError:
            from pydantic import BaseSettings
            print("  ✅ pydantic BaseSettings import successful (fallback)")
        
        # Test FastAPI
        from fastapi import FastAPI
        print("  ✅ FastAPI import successful")
        
        # Test other core dependencies
        import uvicorn
        print("  ✅ uvicorn import successful")
        
        print("✅ All core imports working")
        return True
        
    except ImportError as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Main deployment fix function"""
    print("🚀 Starting Backend Deployment Fixes...\n")
    
    try:
        # Fix Pydantic imports
        fix_pydantic_imports()
        
        # Update requirements
        update_requirements()
        
        # Create Railway config
        create_railway_config()
        
        # Ensure main.py exists
        ensure_main_py_exists()
        
        # Fix config file
        fix_config_file()
        
        # Create init files
        create_init_files()
        
        # Test imports
        imports_ok = test_imports()
        
        print("\n" + "="*60)
        print("🎉 BACKEND DEPLOYMENT FIXES COMPLETE!")
        print("="*60)
        
        print("\n✅ Fixes Applied:")
        print("- Fixed Pydantic imports for compatibility")
        print("- Updated requirements.txt with pydantic-settings")
        print("- Created Railway configuration files")
        print("- Ensured main.py is properly configured")
        print("- Fixed configuration file structure")
        print("- Created necessary __init__.py files")
        
        print("\n📋 Next Steps:")
        print("1. Commit and push these changes to your repository")
        print("2. Redeploy to Railway using: railway up")
        print("3. Check Railway logs for any remaining issues")
        print("4. Test the deployed endpoints")
        
        if imports_ok:
            print("\n🎯 All imports are working correctly!")
        else:
            print("\n⚠️ Some imports may still have issues - check Railway logs after deployment")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment fix failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)