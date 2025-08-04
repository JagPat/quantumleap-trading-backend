#!/usr/bin/env python3
"""
Test authentication router import
"""

import sys
import traceback

def test_auth_import():
    """Test if authentication router can be imported"""
    print("🔍 Testing authentication router import...")
    
    try:
        print("1. Testing core auth import...")
        from app.core.auth import TokenManager, get_current_user_id
        print("✅ Core auth imported successfully")
        
        print("2. Testing auth router import...")
        from app.auth.auth_router import router
        print("✅ Auth router imported successfully")
        
        print("3. Testing router configuration...")
        print(f"   Router prefix: {router.prefix}")
        print(f"   Router tags: {router.tags}")
        
        print("4. Testing route count...")
        route_count = len(router.routes)
        print(f"   Total routes: {route_count}")
        
        print("5. Listing routes...")
        for route in router.routes:
            print(f"   - {route.methods} {route.path}")
        
        print("\n✅ All authentication imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Authentication import failed:")
        print(f"   Error: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        print("\n📋 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auth_import()
    sys.exit(0 if success else 1)