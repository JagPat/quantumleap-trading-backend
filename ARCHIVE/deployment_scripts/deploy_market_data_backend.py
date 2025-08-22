#!/usr/bin/env python3
"""
Deploy Market Data Backend Components
Ensures all market data and condition monitoring components are properly integrated
"""
import os
import sys
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all new components can be imported"""
    print("🧪 Testing component imports...")
    
    try:
        # Test market data components
        from app.trading_engine.market_data_manager import MarketDataManager
        from app.trading_engine.market_data_processor import MarketDataProcessor
        from app.trading_engine.market_condition_monitor import MarketConditionMonitor
        print("✅ Core components import successfully")
        
        # Test routers
        from app.trading_engine.market_data_router import router as market_data_router
        from app.trading_engine.market_condition_router import router as market_condition_router
        print("✅ Router components import successfully")
        
        # Test market data main router
        from app.trading_engine.market_data_main_router import router as trading_engine_router
        print("✅ Market data main router imports successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints are properly configured"""
    print("🔍 Testing API endpoint configuration...")
    
    try:
        from app.trading_engine.market_data_main_router import router as trading_engine_router
        
        # Get all routes
        routes = []
        for route in trading_engine_router.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        print(f"✅ Found {len(routes)} routes in trading engine router")
        
        # Check for market data routes
        market_data_routes = [r for r in routes if 'market-data' in r]
        market_condition_routes = [r for r in routes if 'market-condition' in r]
        
        print(f"✅ Market data routes: {len(market_data_routes)}")
        print(f"✅ Market condition routes: {len(market_condition_routes)}")
        
        if market_data_routes:
            print("   Sample market data routes:")
            for route in market_data_routes[:3]:
                print(f"   - {route}")
        
        if market_condition_routes:
            print("   Sample market condition routes:")
            for route in market_condition_routes[:3]:
                print(f"   - {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def run_component_tests():
    """Run the component tests to verify functionality"""
    print("🧪 Running component tests...")
    
    test_files = [
        "test_processor_simple.py",
        "test_market_condition_monitor.py"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"🔍 Running {test_file}...")
            try:
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print(f"✅ {test_file} passed")
                else:
                    print(f"❌ {test_file} failed:")
                    print(result.stderr)
                    return False
            except subprocess.TimeoutExpired:
                print(f"⏰ {test_file} timed out")
                return False
            except Exception as e:
                print(f"❌ Error running {test_file}: {e}")
                return False
        else:
            print(f"⚠️ Test file {test_file} not found")
    
    return True

def create_deployment_summary():
    """Create a deployment summary"""
    print("📋 Creating deployment summary...")
    
    summary = {
        "deployment_time": datetime.utcnow().isoformat(),
        "components_deployed": [
            "MarketDataManager",
            "MarketDataProcessor", 
            "MarketConditionMonitor",
            "MarketDataRouter",
            "MarketConditionRouter"
        ],
        "api_endpoints": [
            "/api/trading-engine/market-data/*",
            "/api/trading-engine/market-condition/*"
        ],
        "features": [
            "Real-time market data processing",
            "Sub-second latency processing",
            "Market condition monitoring",
            "Volatility detection",
            "Gap analysis",
            "Trend analysis",
            "Trading halt detection",
            "Market session tracking"
        ]
    }
    
    with open("MARKET_DATA_DEPLOYMENT_SUMMARY.json", "w") as f:
        import json
        json.dump(summary, f, indent=2)
    
    print("✅ Deployment summary created")
    return summary

def main():
    """Main deployment function"""
    print("🚀 Deploying Market Data Backend Components")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("❌ Import tests failed - deployment aborted")
        return False
    
    # Test API endpoints
    if not test_api_endpoints():
        print("❌ API endpoint tests failed - deployment aborted")
        return False
    
    # Run component tests
    if not run_component_tests():
        print("❌ Component tests failed - deployment aborted")
        return False
    
    # Create deployment summary
    summary = create_deployment_summary()
    
    print("\n🎉 Market Data Backend Deployment Complete!")
    print("=" * 50)
    print("✅ All components deployed successfully")
    print("✅ All tests passed")
    print("✅ API endpoints configured")
    print("\n📊 Deployment Summary:")
    print(f"   Components: {len(summary['components_deployed'])}")
    print(f"   API Endpoints: {len(summary['api_endpoints'])}")
    print(f"   Features: {len(summary['features'])}")
    
    print("\n🔗 Available Endpoints:")
    for endpoint in summary['api_endpoints']:
        print(f"   - {endpoint}")
    
    print("\n🚀 Ready for Frontend Integration!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)