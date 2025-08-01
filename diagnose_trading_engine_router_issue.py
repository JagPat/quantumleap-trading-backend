#!/usr/bin/env python3

"""
Trading Engine Router Diagnosis Script
Identifies why the comprehensive router is not loading properly
"""

import os
import sys
import importlib.util
from pathlib import Path

def test_import(module_path, module_name):
    """Test if a module can be imported"""
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            return False, f"Could not create spec for {module_path}"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, "Import successful"
    except Exception as e:
        return False, str(e)

def check_file_exists(file_path):
    """Check if file exists and get basic info"""
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        return True, f"Exists ({size} bytes)"
    else:
        return False, "File not found"

def diagnose_trading_engine_router():
    """Diagnose trading engine router loading issues"""
    print("🔍 Trading Engine Router Diagnosis")
    print("=" * 50)
    
    # Check main router files
    router_files = [
        ("app/trading_engine/router.py", "Main comprehensive router"),
        ("app/trading_engine/simple_router.py", "Simple fallback router"),
        ("main.py", "Application entry point")
    ]
    
    print("\n📁 File Existence Check:")
    for file_path, description in router_files:
        exists, info = check_file_exists(file_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path} - {description}: {info}")
    
    # Check sub-router dependencies
    print("\n🔗 Sub-Router Dependencies:")
    sub_routers = [
        ("app/trading_engine/market_data_router.py", "Market data endpoints"),
        ("app/trading_engine/market_condition_router.py", "Market condition monitoring"),
        ("app/trading_engine/emergency_stop_router.py", "Emergency stop system"),
        ("app/trading_engine/manual_override_router.py", "Manual override controls"),
        ("app/trading_engine/user_preferences_router.py", "User preferences"),
        ("app/trading_engine/performance_tracker_router.py", "Performance tracking"),
        ("app/trading_engine/system_health_router.py", "System health monitoring"),
        ("app/trading_engine/alerting_router.py", "Alerting system"),
        ("app/trading_engine/audit_router.py", "Audit logging"),
        ("app/trading_engine/compliance_router.py", "Compliance validation"),
        ("app/trading_engine/investigation_router.py", "Investigation tools")
    ]
    
    missing_routers = []
    for file_path, description in sub_routers:
        exists, info = check_file_exists(file_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path} - {description}: {info}")
        if not exists:
            missing_routers.append((file_path, description))
    
    # Check core dependencies
    print("\n⚙️ Core Dependencies:")
    core_files = [
        ("app/trading_engine/models.py", "Trading models"),
        ("app/trading_engine/database_schema.py", "Database schema"),
        ("app/trading_engine/event_bus.py", "Event bus system"),
        ("app/trading_engine/monitoring.py", "Monitoring system"),
        ("app/trading_engine/order_service.py", "Order service"),
        ("app/trading_engine/order_executor.py", "Order executor"),
        ("app/trading_engine/position_manager.py", "Position manager"),
        ("app/trading_engine/risk_engine.py", "Risk engine"),
        ("app/trading_engine/strategy_manager.py", "Strategy manager")
    ]
    
    missing_dependencies = []
    for file_path, description in core_files:
        exists, info = check_file_exists(file_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path} - {description}: {info}")
        if not exists:
            missing_dependencies.append((file_path, description))
    
    # Test imports
    print("\n🧪 Import Testing:")
    
    # Test simple router import
    simple_router_success, simple_router_error = test_import(
        "app/trading_engine/simple_router.py", 
        "simple_router"
    )
    status = "✅" if simple_router_success else "❌"
    print(f"  {status} Simple Router: {simple_router_error}")
    
    # Test main router import
    main_router_success, main_router_error = test_import(
        "app/trading_engine/router.py", 
        "main_router"
    )
    status = "✅" if main_router_success else "❌"
    print(f"  {status} Main Router: {main_router_error}")
    
    # Check main.py router loading
    print("\n📋 Main.py Router Loading:")
    try:
        with open("main.py", "r") as f:
            main_content = f.read()
        
        if "from app.trading_engine.router import trading_engine_router" in main_content:
            print("  ✅ Main router import found in main.py")
        elif "from app.trading_engine.simple_router import router" in main_content:
            print("  ⚠️ Only simple router import found in main.py")
        else:
            print("  ❌ No trading engine router import found in main.py")
            
        if 'app.include_router(trading_engine_router, prefix="/api/trading-engine"' in main_content:
            print("  ✅ Main router registration found")
        else:
            print("  ❌ Main router registration not found")
            
    except Exception as e:
        print(f"  ❌ Error reading main.py: {e}")
    
    # Summary and recommendations
    print("\n" + "=" * 50)
    print("📊 DIAGNOSIS SUMMARY")
    print("=" * 50)
    
    if missing_routers:
        print(f"\n❌ Missing Sub-Routers ({len(missing_routers)}):")
        for file_path, description in missing_routers:
            print(f"  - {file_path} ({description})")
    
    if missing_dependencies:
        print(f"\n❌ Missing Dependencies ({len(missing_dependencies)}):")
        for file_path, description in missing_dependencies:
            print(f"  - {file_path} ({description})")
    
    print(f"\n🎯 Router Status:")
    print(f"  - Simple Router: {'✅ Working' if simple_router_success else '❌ Failed'}")
    print(f"  - Main Router: {'✅ Working' if main_router_success else '❌ Failed'}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if not main_router_success:
        print("  1. 🔧 Fix main router import issues")
        print("     - Resolve missing dependencies")
        print("     - Fix import errors in router.py")
        
    if missing_routers:
        print("  2. 📁 Create missing sub-routers")
        print("     - Implement missing router files")
        print("     - Add basic endpoint stubs")
        
    if missing_dependencies:
        print("  3. ⚙️ Fix missing core dependencies")
        print("     - Ensure all core files exist")
        print("     - Fix import chains")
    
    print("  4. 🔄 Update main.py to use comprehensive router")
    print("     - Switch from simple_router to main router")
    print("     - Test all endpoints become accessible")
    
    return {
        'simple_router_working': simple_router_success,
        'main_router_working': main_router_success,
        'missing_routers': missing_routers,
        'missing_dependencies': missing_dependencies
    }

if __name__ == "__main__":
    diagnosis = diagnose_trading_engine_router()
    
    if diagnosis['main_router_working']:
        print("\n🎉 Main router is working! Issue may be in main.py registration.")
    else:
        print("\n🔧 Main router has import issues that need to be fixed.")
    
    print(f"\n📈 Next Step: {'Fix router registration' if diagnosis['main_router_working'] else 'Fix import issues'}")