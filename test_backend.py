#!/usr/bin/env python3
"""
Backend Testing Script
Run comprehensive backend integration tests
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def main():
    """Main test runner"""
    try:
        from trading_engine.test_backend_integration import run_backend_tests
        
        print("🚀 Starting Quantum Leap Trading Engine Backend Tests")
        print("=" * 60)
        
        # Run all backend tests
        results = await run_backend_tests()
        
        # Exit with appropriate code
        if results['backend_ready']:
            print("\n🎉 All backend systems operational!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Backend needs attention ({results['failed_tests']} failures)")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())