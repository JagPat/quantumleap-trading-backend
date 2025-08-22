#!/usr/bin/env python3
"""
Test script to identify which trading engine import is failing
"""

import sys
import traceback

def test_import(module_name, import_statement):
    """Test a specific import and report results"""
    try:
        exec(import_statement)
        print(f"✅ {module_name}: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ {module_name}: FAILED - {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def main():
    print("🔍 Testing Trading Engine Component Imports...")
    print("=" * 60)
    
    imports_to_test = [
        ("database_schema", "from app.trading_engine.database_schema import check_trading_engine_health, get_trading_system_config, set_trading_system_config"),
        ("event_bus", "from app.trading_engine.event_bus import event_bus"),
        ("monitoring", "from app.trading_engine.monitoring import trading_monitor"),
        ("models", "from app.trading_engine.models import TradingSignal, SignalType, OrderType, OrderSide, OrderStatus, StrategyStatus"),
        ("order_service", "from app.trading_engine.order_service import order_service"),
        ("order_executor", "from app.trading_engine.order_executor import order_executor"),
        ("position_manager", "from app.trading_engine.position_manager import position_manager"),
        ("risk_engine", "from app.trading_engine.risk_engine import risk_engine"),
        ("risk_monitor", "from app.trading_engine.risk_monitor import risk_monitor"),
        ("position_sizer", "from app.trading_engine.position_sizer import position_sizer"),
        ("strategy_manager", "from app.trading_engine.strategy_manager import strategy_manager, StrategyConfig, StrategyType"),
        ("strategy_controller", "from app.trading_engine.strategy_controller import strategy_controller"),
        ("strategy_lifecycle", "from app.trading_engine.strategy_lifecycle import strategy_lifecycle_manager"),
    ]
    
    failed_imports = []
    
    for module_name, import_statement in imports_to_test:
        if not test_import(module_name, import_statement):
            failed_imports.append(module_name)
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print(f"✅ Successful imports: {len(imports_to_test) - len(failed_imports)}")
    print(f"❌ Failed imports: {len(failed_imports)}")
    
    if failed_imports:
        print(f"\n🚨 Failed modules: {', '.join(failed_imports)}")
        print("\n💡 The trading engine router is likely failing because of these import errors.")
        print("   This explains why you're getting 404 errors - the fallback router is being used instead.")
    else:
        print("\n✅ All imports successful! The issue might be elsewhere.")
    
    # Test the full router import
    print("\n" + "=" * 60)
    print("🔍 Testing Full Router Import...")
    try:
        from app.trading_engine.router import router as trading_engine_router
        print("✅ Trading engine router import: SUCCESS")
        print(f"   Router prefix: {trading_engine_router.prefix}")
        print(f"   Number of routes: {len(trading_engine_router.routes)}")
    except Exception as e:
        print(f"❌ Trading engine router import: FAILED - {e}")
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()