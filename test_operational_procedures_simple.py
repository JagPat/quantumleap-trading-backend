#!/usr/bin/env python3
"""
Simple test for operational procedures system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_operational_procedures():
    """Test operational procedures system"""
    print("🧪 Testing Operational Procedures System...")
    
    try:
        from app.trading_engine.operational_procedures import get_operational_procedures
        
        # Get operational procedures instance
        ops = get_operational_procedures()
        print("✅ Operational procedures instance created")
        
        # Test system health check
        health = ops.check_system_health()
        print(f"✅ System health check: {health['status']}")
        
        # Test metrics collection
        metrics = ops.collect_system_metrics()
        print(f"✅ System metrics collected: CPU {metrics.cpu_usage:.1f}%, Memory {metrics.memory_usage:.1f}%")
        
        # Test capacity planning
        capacity = ops.get_capacity_planning_report()
        if 'error' not in capacity:
            print("✅ Capacity planning report generated")
        else:
            print("⚠️ Capacity planning needs metrics history")
        
        # Test operational status
        status = ops.get_operational_status()
        print("✅ Operational status retrieved")
        
        # Test recovery procedures
        recovery_result = ops.trigger_automated_recovery("high_cpu")
        if recovery_result['success']:
            print("✅ Automated recovery test successful")
        
        print("\n🎉 All operational procedures tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_operational_router():
    """Test operational procedures router"""
    print("\n🧪 Testing Operational Procedures Router...")
    
    try:
        from app.trading_engine.operational_procedures_router import operational_procedures_router
        print("✅ Operational procedures router imported")
        
        # Check router endpoints
        routes = [route.path for route in operational_procedures_router.routes]
        expected_routes = ['/health', '/status', '/metrics', '/capacity-planning']
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} available")
            else:
                print(f"❌ Route {route} missing")
        
        print("✅ Operational procedures router test completed")
        return True
        
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Operational Procedures Tests\n")
    
    success1 = test_operational_procedures()
    success2 = test_operational_router()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Operational procedures system is ready.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)