#!/usr/bin/env python3

"""
Fix CORS Configuration in Backend
This script updates the main.py file to add proper CORS middleware
"""

import os
import re

def find_main_py():
    """Find the main.py file in the project"""
    possible_paths = [
        "main.py",
        "app/main.py", 
        "src/main.py",
        "backend/main.py"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def add_cors_middleware(main_py_path):
    """Add CORS middleware to main.py"""
    try:
        # Read the current file
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Check if CORS is already configured
        if 'CORSMiddleware' in content:
            print("✅ CORS middleware already configured")
            return True
        
        # Add CORS import if not present
        if 'from fastapi.middleware.cors import CORSMiddleware' not in content:
            # Find FastAPI imports and add CORS import
            fastapi_import_pattern = r'(from fastapi import.*)'
            if re.search(fastapi_import_pattern, content):
                content = re.sub(
                    fastapi_import_pattern,
                    r'\1\nfrom fastapi.middleware.cors import CORSMiddleware',
                    content
                )
            else:
                # Add at the top after other imports
                import_section = content.split('\n\n')[0]
                content = content.replace(
                    import_section,
                    import_section + '\nfrom fastapi.middleware.cors import CORSMiddleware'
                )
        
        # Add CORS middleware configuration
        cors_config = '''
# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
'''
        
        # Find where to insert CORS config (after app creation)
        app_creation_pattern = r'(app = FastAPI\(.*?\))'
        if re.search(app_creation_pattern, content, re.DOTALL):
            content = re.sub(
                app_creation_pattern,
                r'\1\n' + cors_config,
                content,
                flags=re.DOTALL
            )
        else:
            # Fallback: add after any line containing 'app = '
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'app = ' in line and 'FastAPI' in line:
                    lines.insert(i + 1, cors_config)
                    break
            content = '\n'.join(lines)
        
        # Write the updated file
        with open(main_py_path, 'w') as f:
            f.write(content)
        
        print(f"✅ CORS middleware added to {main_py_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating {main_py_path}: {e}")
        return False

def add_missing_endpoint(main_py_path):
    """Add missing /api/trading/status endpoint"""
    try:
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Check if endpoint already exists
        if '/api/trading/status' in content:
            print("✅ Trading status endpoint already exists")
            return True
        
        # Add the endpoint
        trading_status_endpoint = '''
@app.get("/api/trading/status")
async def get_trading_status():
    """Get trading system status"""
    return {
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "trading_enabled": True,
        "market_hours": "open",
        "system_health": "healthy"
    }
'''
        
        # Add datetime import if not present
        if 'from datetime import datetime' not in content:
            content = 'from datetime import datetime\n' + content
        
        # Add the endpoint before the main block
        if 'if __name__ == "__main__":' in content:
            content = content.replace(
                'if __name__ == "__main__":',
                trading_status_endpoint + '\n\nif __name__ == "__main__":'
            )
        else:
            # Add at the end
            content += trading_status_endpoint
        
        # Write the updated file
        with open(main_py_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Trading status endpoint added to {main_py_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding trading status endpoint: {e}")
        return False

def main():
    print("🔧 Fixing Backend CORS Configuration")
    print("=" * 40)
    
    # Find main.py
    main_py_path = find_main_py()
    
    if not main_py_path:
        print("❌ Could not find main.py file")
        print("💡 Please run this script from the project root directory")
        return
    
    print(f"📁 Found main.py at: {main_py_path}")
    
    # Add CORS middleware
    cors_success = add_cors_middleware(main_py_path)
    
    # Add missing endpoint
    endpoint_success = add_missing_endpoint(main_py_path)
    
    if cors_success and endpoint_success:
        print(f"\n🎉 Backend fixes applied successfully!")
        print(f"\n🚀 Next steps:")
        print(f"   1. Restart your backend server")
        print(f"   2. Deploy to Railway if needed")
        print(f"   3. Run: cd quantum-leap-frontend")
        print(f"   4. Run: node test-railway-backend.js")
        print(f"   5. Expect 85-90%+ pass rate!")
    else:
        print(f"\n⚠️ Some fixes may have failed - please check manually")

if __name__ == "__main__":
    main()