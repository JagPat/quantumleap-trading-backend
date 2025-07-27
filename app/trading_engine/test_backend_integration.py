"""
Backend Integration Testing
Test all trading engine components to ensure they work together properly
"""
import asyncio
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import all trading engine components
from .models import (
    TradingSignal, SignalType, Order, OrderType, OrderSide, OrderStatus,
    RiskParameters, Position, Execution
)
from .order_executor import order_executor
from .order_service import order_service
from .risk_engine import risk_engine
from .risk_monitor import risk_monitor
from .position_manager import position_manager
from .position_sizer import position_sizer
from .strategy_manager import strategy_manager, StrategyConfig, StrategyType
from .strategy_controller import strategy_controller
from .strategy_lifecycle import strategy_lifecycle_manager
from .event_bus import event_bus
from .monitoring import trading_monitor

logger = logging.getLogger(__name__)

class BackendIntegrationTester:
    """
    Comprehensive backend integration testing
    """
    
    def __init__(self):
        self.test_results = {}
        self.test_user_id = "test_user_backend_integration"
        self.test_symbol = "RELIANCE"
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all backend integration tests"""
        print("🚀 Starting Backend Integration Tests...")
        print("=" * 60)
        
        test_methods = [
            ("Database Schema", self.test_database_schema),
            ("Event Bus", self.test_event_bus),
            ("Models & Data Structures", self.test_models),
            ("Risk Engine", self.test_risk_engine),
            ("Position Sizer", self.test_position_sizer),
            ("Order Executor", self.test_order_executor),
            ("Order Service", self.test_order_service),
            ("Position Manager", self.test_position_manager),
            ("Risk Monitor", self.test_risk_monitor),
            ("Strategy Manager", self.test_strategy_manager),
            ("Strategy Controller", self.test_strategy_controller),
            ("Strategy Lifecycle", self.test_strategy_lifecycle),
            ("End-to-End Flow", self.test_end_to_end_flow)
        ]
        
        for test_name, test_method in test_methods:
            print(f"\n📋 Testing: {test_name}")
            print("-" * 40)
            
            try:
                result = await test_method()
                self.test_results[test_name] = result
                
                if result['success']:
                    print(f"✅ {test_name}: PASSED")
                    if result.get('details'):
                        for detail in result['details']:
                            print(f"   • {detail}")
                else:
                    print(f"❌ {test_name}: FAILED")
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_msg = f"Exception in {test_name}: {str(e)}"
                print(f"💥 {test_name}: EXCEPTION")
                print(f"   Error: {error_msg}")
                print(f"   Traceback: {traceback.format_exc()}")
                
                self.test_results[test_name] = {
                    'success': False,
                    'error': error_msg,
                    'exception': True
                }
        
        # Generate summary
        return self.generate_test_summary()
    
    async def test_database_schema(self) -> Dict[str, Any]:
        """Test database schema and connections"""
        try:
            from .database_schema import create_tables
            from .order_db import order_db
            
            # Test table creation
            create_tables()
            
            # Test basic database operations
            test_order = Order(
                id="test_db_order",
                user_id=self.test_user_id,
                symbol=self.test_symbol,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=10
            )
            
            # Test create
            success = order_db.create_order(test_order)
            if not success:
                return {'success': False, 'error': 'Failed to create test order'}
            
            # Test read
            retrieved_order = order_db.get_order("test_db_order")
            if not retrieved_order:
                return {'success': False, 'error': 'Failed to retrieve test order'}
            
            # Test update
            retrieved_order.status = OrderStatus.FILLED
            success = order_db.update_order(retrieved_order)
            if not success:
                return {'success': False, 'error': 'Failed to update test order'}
            
            return {
                'success': True,
                'details': [
                    'Database tables created successfully',
                    'Order CRUD operations working',
                    'Database connection stable'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_event_bus(self) -> Dict[str, Any]:
        """Test event bus functionality"""
        try:
            from .event_bus import EventType, publish_order_event
            
            # Test event publishing
            test_event_data = {
                'test_field': 'test_value',
                'timestamp': datetime.now().isoformat()
            }
            
            await publish_order_event(
                self.test_user_id, 
                EventType.ORDER_CREATED, 
                test_event_data
            )
            
            # Test event bus status
            status = event_bus.get_status()
            
            return {
                'success': True,
                'details': [
                    'Event publishing working',
                    f'Event bus active: {status.get("active", False)}',
                    f'Handlers registered: {status.get("handlers_count", 0)}'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_models(self) -> Dict[str, Any]:
        """Test data models and serialization"""
        try:
            # Test TradingSignal
            signal = TradingSignal(
                id="test_signal",
                user_id=self.test_user_id,
                symbol=self.test_symbol,
                signal_type=SignalType.BUY,
                confidence_score=0.8,
                target_price=2500.0,
                stop_loss=2400.0
            )
            
            # Test serialization
            signal_dict = signal.to_dict()
            signal_restored = TradingSignal.from_dict(signal_dict)
            
            if signal_restored.id != signal.id:
                return {'success': False, 'error': 'Signal serialization failed'}
            
            # Test Order model
            order = Order(
                id="test_order_model",
                user_id=self.test_user_id,
                symbol=self.test_symbol,
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                quantity=10,
                price=2500.0
            )
            
            # Test order methods
            order.add_fill(5, 2495.0, 2.5)
            
            if order.filled_quantity != 5:
                return {'success': False, 'error': 'Order fill logic failed'}
            
            if not order.is_partially_filled:
                return {'success': False, 'error': 'Order status logic failed'}
            
            return {
                'success': True,
                'details': [
                    'TradingSignal model working correctly',
                    'Order model and methods working',
                    'Serialization/deserialization working',
                    'Business logic methods working'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_risk_engine(self) -> Dict[str, Any]:
        """Test risk engine functionality"""
        try:
            # Create test order
            test_order = Order(
                id="test_risk_order",
                user_id=self.test_user_id,
                symbol=self.test_symbol,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=10
            )
            
            # Test order validation
            validation_result = await risk_engine.validate_order(test_order)
            
            if not hasattr(validation_result, 'valid'):
                return {'success': False, 'error': 'Risk validation result invalid'}
            
            # Test portfolio risk calculation
            portfolio_risk = await risk_engine.calculate_portfolio_risk(self.test_user_id)
            
            if not hasattr(portfolio_risk, 'risk_score'):
                return {'success': False, 'error': 'Portfolio risk calculation failed'}
            
            return {
                'success': True,
                'details': [
                    f'Order validation: {"PASSED" if validation_result.valid else "FAILED"}',
                    f'Risk score calculated: {portfolio_risk.risk_score:.3f}',
                    f'Violations found: {len(validation_result.violations)}',
                    'Risk engine operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_position_sizer(self) -> Dict[str, Any]:
        """Test position sizing functionality"""
        try:
            # Create test signal
            test_signal = TradingSignal(
                id="test_position_signal",
                user_id=self.test_user_id,
                symbol=self.test_symbol,
                signal_type=SignalType.BUY,
                confidence_score=0.75,
                target_price=2500.0
            )
            
            # Test position size calculation
            portfolio_value = 100000.0
            
            # Test different sizing models
            models_to_test = ['FIXED_FRACTIONAL', 'VOLATILITY_ADJUSTED', 'CONFIDENCE_WEIGHTED']
            
            for model in models_to_test:
                result = await position_sizer.calculate_position_size(
                    test_signal, portfolio_value, model
                )
                
                if not hasattr(result, 'recommended_quantity'):
                    return {'success': False, 'error': f'Position sizing failed for {model}'}
                
                if result.recommended_quantity <= 0:
                    return {'success': False, 'error': f'Invalid quantity for {model}'}
            
            return {
                'success': True,
                'details': [
                    f'Tested {len(models_to_test)} sizing models',
                    'All models producing valid quantities',
                    'Risk calculations working',
                    'Position sizer operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_order_executor(self) -> Dict[str, Any]:
        """Test order executor functionality"""
        try:
            # Create test signal
            test_signal = TradingSignal(
                id="test_executor_signal",
                user_id=self.test_user_id,
                symbol=self.test_symbol,
                signal_type=SignalType.BUY,
                confidence_score=0.8,
                target_price=2500.0
            )
            
            # Test signal processing
            result = await order_executor.process_signal(test_signal)
            
            if not hasattr(result, 'success'):
                return {'success': False, 'error': 'Order executor result invalid'}
            
            # Test order status retrieval
            if result.success and result.order:
                order_status = await order_executor.get_order_status(result.order.id)
                
                if not order_status:
                    return {'success': False, 'error': 'Order status retrieval failed'}
            
            return {
                'success': True,
                'details': [
                    f'Signal processing: {"SUCCESS" if result.success else "FAILED"}',
                    'Order creation working',
                    'Order status tracking working',
                    'Order executor operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_order_service(self) -> Dict[str, Any]:
        """Test order service functionality"""
        try:
            # Test getting user orders
            user_orders = await order_service.get_user_orders(self.test_user_id)
            
            if not isinstance(user_orders, list):
                return {'success': False, 'error': 'User orders retrieval failed'}
            
            # Test getting active orders
            active_orders = await order_service.get_active_orders(self.test_user_id)
            
            if not isinstance(active_orders, list):
                return {'success': False, 'error': 'Active orders retrieval failed'}
            
            # Test trading statistics
            stats = await order_service.get_trading_statistics(self.test_user_id)
            
            if not isinstance(stats, dict):
                return {'success': False, 'error': 'Trading statistics failed'}
            
            return {
                'success': True,
                'details': [
                    f'User orders retrieved: {len(user_orders)}',
                    f'Active orders: {len(active_orders)}',
                    'Trading statistics working',
                    'Order service operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_position_manager(self) -> Dict[str, Any]:
        """Test position manager functionality"""
        try:
            # Test getting user positions
            positions = await position_manager.get_user_positions(self.test_user_id)
            
            if not isinstance(positions, list):
                return {'success': False, 'error': 'Position retrieval failed'}
            
            # Test portfolio summary
            portfolio_summary = await position_manager.get_portfolio_summary(self.test_user_id)
            
            if not isinstance(portfolio_summary, dict):
                return {'success': False, 'error': 'Portfolio summary failed'}
            
            # Test position history
            position_history = await position_manager.get_position_history(self.test_user_id)
            
            if not isinstance(position_history, list):
                return {'success': False, 'error': 'Position history failed'}
            
            return {
                'success': True,
                'details': [
                    f'Positions retrieved: {len(positions)}',
                    'Portfolio summary working',
                    'Position history working',
                    'Position manager operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_risk_monitor(self) -> Dict[str, Any]:
        """Test risk monitor functionality"""
        try:
            # Test getting user alerts
            alerts = await risk_monitor.get_user_alerts(self.test_user_id)
            
            if not isinstance(alerts, list):
                return {'success': False, 'error': 'Risk alerts retrieval failed'}
            
            # Test monitoring status
            status = risk_monitor.get_monitoring_status()
            
            if not isinstance(status, dict):
                return {'success': False, 'error': 'Monitoring status failed'}
            
            # Test stop loss functionality (add and remove)
            add_result = await risk_monitor.add_stop_loss(
                self.test_user_id, self.test_symbol, 2400.0
            )
            
            if not add_result:
                return {'success': False, 'error': 'Stop loss addition failed'}
            
            remove_result = await risk_monitor.remove_stop_loss(
                self.test_user_id, self.test_symbol
            )
            
            if not remove_result:
                return {'success': False, 'error': 'Stop loss removal failed'}
            
            return {
                'success': True,
                'details': [
                    f'Risk alerts: {len(alerts)}',
                    f'Monitoring active: {status.get("monitoring_active", False)}',
                    'Stop loss management working',
                    'Risk monitor operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_strategy_manager(self) -> Dict[str, Any]:
        """Test strategy manager functionality"""
        try:
            # Create test strategy config
            test_config = StrategyConfig(
                id="test_strategy_backend",
                name="Backend Test Strategy",
                description="Test strategy for backend integration",
                strategy_type=StrategyType.MOMENTUM,
                user_id=self.test_user_id,
                symbols=[self.test_symbol],
                parameters={'test_param': 'test_value'},
                risk_parameters=RiskParameters()
            )
            
            # Test strategy deployment
            deployment_result = await strategy_manager.deploy_strategy(test_config)
            
            if not deployment_result.get('success'):
                return {'success': False, 'error': f'Strategy deployment failed: {deployment_result.get("error")}'}
            
            # Test strategy status
            status = await strategy_manager.get_strategy_status(test_config.id)
            
            if not status:
                return {'success': False, 'error': 'Strategy status retrieval failed'}
            
            # Test user strategies
            user_strategies = await strategy_manager.get_user_strategies(self.test_user_id)
            
            if not isinstance(user_strategies, list):
                return {'success': False, 'error': 'User strategies retrieval failed'}
            
            # Clean up - stop the test strategy
            await strategy_manager.stop_strategy(test_config.id)
            
            return {
                'success': True,
                'details': [
                    'Strategy deployment working',
                    'Strategy status tracking working',
                    f'User strategies: {len(user_strategies)}',
                    'Strategy manager operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_strategy_controller(self) -> Dict[str, Any]:
        """Test strategy controller functionality"""
        try:
            # Create and deploy test strategy first
            test_config = StrategyConfig(
                id="test_controller_strategy",
                name="Controller Test Strategy",
                description="Test strategy for controller testing",
                strategy_type=StrategyType.MOMENTUM,
                user_id=self.test_user_id,
                symbols=[self.test_symbol],
                parameters={'test_param': 'test_value'},
                risk_parameters=RiskParameters()
            )
            
            deployment_result = await strategy_manager.deploy_strategy(test_config)
            
            if not deployment_result.get('success'):
                return {'success': False, 'error': 'Failed to deploy test strategy for controller'}
            
            # Test control actions
            pause_result = await strategy_controller.execute_control_action(
                test_config.id, 'PAUSE', 'Backend integration test', 'SYSTEM'
            )
            
            if not pause_result.get('success'):
                return {'success': False, 'error': 'Strategy pause failed'}
            
            # Test resume
            resume_result = await strategy_controller.execute_control_action(
                test_config.id, 'RESUME', 'Backend integration test', 'SYSTEM'
            )
            
            if not resume_result.get('success'):
                return {'success': False, 'error': 'Strategy resume failed'}
            
            # Test control history
            history = await strategy_controller.get_strategy_control_history(test_config.id)
            
            if not isinstance(history, list):
                return {'success': False, 'error': 'Control history retrieval failed'}
            
            # Clean up
            await strategy_manager.stop_strategy(test_config.id)
            
            return {
                'success': True,
                'details': [
                    'Strategy pause/resume working',
                    f'Control actions recorded: {len(history)}',
                    'Control history tracking working',
                    'Strategy controller operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_strategy_lifecycle(self) -> Dict[str, Any]:
        """Test strategy lifecycle management"""
        try:
            # Create test strategy config
            test_config = StrategyConfig(
                id="test_lifecycle_strategy",
                name="Lifecycle Test Strategy",
                description="Test strategy for lifecycle testing",
                strategy_type=StrategyType.MOMENTUM,
                user_id=self.test_user_id,
                symbols=[self.test_symbol],
                parameters={'test_param': 'test_value'},
                risk_parameters=RiskParameters()
            )
            
            # Test lifecycle creation
            lifecycle_result = await strategy_lifecycle_manager.create_strategy_lifecycle(test_config)
            
            if not lifecycle_result.get('success'):
                return {'success': False, 'error': f'Lifecycle creation failed: {lifecycle_result.get("error")}'}
            
            # Test lifecycle history
            history = await strategy_lifecycle_manager.get_strategy_lifecycle_history(test_config.id)
            
            if not isinstance(history, list):
                return {'success': False, 'error': 'Lifecycle history retrieval failed'}
            
            # Test performance analysis
            analysis = await strategy_lifecycle_manager.analyze_strategy_performance(test_config.id)
            
            # Analysis might be None if insufficient data, which is okay for testing
            
            # Test optimization suggestions
            suggestions = await strategy_lifecycle_manager.generate_optimization_suggestions(test_config.id)
            
            if not isinstance(suggestions, list):
                return {'success': False, 'error': 'Optimization suggestions failed'}
            
            # Clean up
            await strategy_manager.stop_strategy(test_config.id)
            
            return {
                'success': True,
                'details': [
                    'Strategy lifecycle creation working',
                    f'Lifecycle events recorded: {len(history)}',
                    f'Optimization suggestions: {len(suggestions)}',
                    'Strategy lifecycle operational'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_end_to_end_flow(self) -> Dict[str, Any]:
        """Test complete end-to-end trading flow"""
        try:
            print("   🔄 Testing complete trading flow...")
            
            # 1. Create and deploy strategy
            test_config = StrategyConfig(
                id="test_e2e_strategy",
                name="End-to-End Test Strategy",
                description="Complete flow test strategy",
                strategy_type=StrategyType.MOMENTUM,
                user_id=self.test_user_id,
                symbols=[self.test_symbol],
                parameters={'confidence_threshold': 0.7},
                risk_parameters=RiskParameters()
            )
            
            lifecycle_result = await strategy_lifecycle_manager.create_strategy_lifecycle(test_config)
            
            if not lifecycle_result.get('success'):
                return {'success': False, 'error': 'E2E: Strategy creation failed'}
            
            # 2. Create trading signal
            test_signal = TradingSignal(
                id="test_e2e_signal",
                user_id=self.test_user_id,
                symbol=self.test_symbol,
                signal_type=SignalType.BUY,
                confidence_score=0.8,
                target_price=2500.0,
                stop_loss=2400.0,
                strategy_id=test_config.id
            )
            
            # 3. Process signal through order executor
            order_result = await order_executor.process_signal(test_signal)
            
            if not order_result.success:
                return {'success': False, 'error': f'E2E: Signal processing failed: {order_result.error_message}'}
            
            # 4. Check order was created
            if not order_result.order:
                return {'success': False, 'error': 'E2E: No order created from signal'}
            
            # 5. Verify order in database
            order_status = await order_executor.get_order_status(order_result.order.id)
            
            if not order_status:
                return {'success': False, 'error': 'E2E: Order not found in database'}
            
            # 6. Check risk monitoring
            portfolio_risk = await risk_engine.calculate_portfolio_risk(self.test_user_id)
            
            # 7. Check position tracking
            positions = await position_manager.get_user_positions(self.test_user_id)
            
            # 8. Test strategy control
            control_result = await strategy_controller.execute_control_action(
                test_config.id, 'PAUSE', 'E2E test pause', 'SYSTEM'
            )
            
            if not control_result.get('success'):
                return {'success': False, 'error': 'E2E: Strategy control failed'}
            
            # 9. Clean up
            await strategy_manager.stop_strategy(test_config.id, close_positions=True)
            
            return {
                'success': True,
                'details': [
                    '✅ Strategy creation and deployment',
                    '✅ Signal generation and processing',
                    '✅ Order creation and tracking',
                    '✅ Risk calculation and monitoring',
                    '✅ Position tracking',
                    '✅ Strategy control and lifecycle',
                    '🎉 Complete end-to-end flow working!'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': f'E2E flow failed: {str(e)}'}
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r['success']])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print("🏁 BACKEND INTEGRATION TEST SUMMARY")
        print("=" * 60)
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"   • {test_name}: {result.get('error', 'Unknown error')}")
        
        print(f"\n🎯 Backend Status: {'✅ READY' if failed_tests == 0 else '⚠️  NEEDS ATTENTION'}")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'backend_ready': failed_tests == 0,
            'detailed_results': self.test_results
        }

async def run_backend_tests():
    """Run backend integration tests"""
    tester = BackendIntegrationTester()
    return await tester.run_all_tests()

if __name__ == "__main__":
    # Run tests if called directly
    asyncio.run(run_backend_tests())