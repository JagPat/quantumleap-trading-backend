#!/usr/bin/env python3
"""
Deployment Verification Script
Comprehensive testing of deployed AI Engine components
"""
import requests
import json
import time
import sys
from typing import Dict, Any, List

class DeploymentVerifier:
    """Verify deployment functionality"""
    
    def __init__(self, base_url: str, user_id: str = "test_user_deployment"):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.headers = {
            "Content-Type": "application/json",
            "X-User-ID": user_id
        }
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str = "", response_time: float = 0):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_time": response_time
        })
        print(f"{status} {test_name}: {message} ({response_time:.2f}s)")
    
    def test_health_endpoints(self) -> bool:
        """Test basic health endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        endpoints = [
            "/health",
            "/api/ai/monitoring/health/system",
            "/api/ai/monitoring/health/user"
        ]
        
        all_passed = True
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if "status" in data or "health_status" in data:
                        self.log_test(f"Health Check {endpoint}", True, "Healthy", response_time)
                    else:
                        self.log_test(f"Health Check {endpoint}", False, "Invalid response format", response_time)
                        all_passed = False
                else:
                    self.log_test(f"Health Check {endpoint}", False, f"HTTP {response.status_code}", response_time)
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Health Check {endpoint}", False, str(e), 0)
                all_passed = False
        
        return all_passed
    
    def test_ai_chat_engine(self) -> bool:
        """Test AI chat engine functionality"""
        print("\n💬 Testing AI Chat Engine...")
        
        try:
            # Test chat message
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/ai/chat/message",
                json={"message": "Hello, can you help me with portfolio analysis?"},
                headers=self.headers,
                timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "reply" in data and "provider_used" in data:
                    self.log_test("Chat Message", True, f"Provider: {data.get('provider_used')}", response_time)
                    
                    # Test chat sessions
                    sessions_response = requests.get(
                        f"{self.base_url}/api/ai/chat/sessions",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if sessions_response.status_code == 200:
                        self.log_test("Chat Sessions", True, "Sessions retrieved", 0.1)
                        return True
                    else:
                        self.log_test("Chat Sessions", False, f"HTTP {sessions_response.status_code}", 0)
                        return False
                else:
                    self.log_test("Chat Message", False, "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Chat Message", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Chat Engine", False, str(e), 0)
            return False
    
    def test_signal_generation(self) -> bool:
        """Test signal generation system"""
        print("\n📊 Testing Signal Generation...")
        
        try:
            # Test get signals
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/api/ai/signals",
                headers=self.headers,
                timeout=15
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "signals" in data:
                    self.log_test("Get Signals", True, f"Retrieved {len(data['signals'])} signals", response_time)
                    
                    # Test signal generation
                    gen_response = requests.post(
                        f"{self.base_url}/api/ai/signals/generate",
                        json={
                            "symbols": ["RELIANCE", "TCS"],
                            "signal_type": "buy"
                        },
                        headers=self.headers,
                        timeout=30
                    )
                    
                    if gen_response.status_code == 200:
                        gen_data = gen_response.json()
                        if "signals" in gen_data:
                            self.log_test("Generate Signals", True, f"Generated {len(gen_data['signals'])} signals", 1.5)
                            return True
                        else:
                            self.log_test("Generate Signals", False, "Invalid response format", 1.5)
                            return False
                    else:
                        self.log_test("Generate Signals", False, f"HTTP {gen_response.status_code}", 1.5)
                        return False
                else:
                    self.log_test("Get Signals", False, "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Get Signals", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Signal Generation", False, str(e), 0)
            return False
    
    def test_strategy_generation(self) -> bool:
        """Test strategy generation system"""
        print("\n🎯 Testing Strategy Generation...")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/ai/strategy/generate",
                json={
                    "parameters": {
                        "strategy_type": "momentum",
                        "risk_tolerance": "medium",
                        "time_horizon": "medium",
                        "target_symbols": ["NIFTY50"]
                    }
                },
                headers=self.headers,
                timeout=45
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "strategy" in data and "status" in data:
                    strategy = data["strategy"]
                    if "name" in strategy and "type" in strategy:
                        self.log_test("Strategy Generation", True, f"Generated {strategy['type']} strategy", response_time)
                        return True
                    else:
                        self.log_test("Strategy Generation", False, "Invalid strategy format", response_time)
                        return False
                else:
                    self.log_test("Strategy Generation", False, "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Strategy Generation", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Strategy Generation", False, str(e), 0)
            return False
    
    def test_risk_management(self) -> bool:
        """Test risk management system"""
        print("\n⚠️ Testing Risk Management...")
        
        try:
            portfolio_data = {
                "total_value": 1000000,
                "holdings": [
                    {"symbol": "RELIANCE", "current_value": 200000, "sector": "Energy"},
                    {"symbol": "TCS", "current_value": 150000, "sector": "IT"},
                    {"symbol": "HDFCBANK", "current_value": 100000, "sector": "Banking"}
                ]
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/ai/risk-cost/portfolio/assess",
                json={"portfolio_data": portfolio_data},
                headers=self.headers,
                timeout=20
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "overall_risk" in data and "risk_score" in data:
                    self.log_test("Risk Assessment", True, f"Risk: {data['overall_risk']}, Score: {data['risk_score']}", response_time)
                    
                    # Test trade validation
                    trade_response = requests.post(
                        f"{self.base_url}/api/ai/risk-cost/trade/validate",
                        json={
                            "trade_data": {"symbol": "WIPRO", "amount": 80000, "type": "buy"},
                            "portfolio_data": portfolio_data
                        },
                        headers=self.headers,
                        timeout=15
                    )
                    
                    if trade_response.status_code == 200:
                        trade_data = trade_response.json()
                        if "approved" in trade_data:
                            self.log_test("Trade Validation", True, f"Approved: {trade_data['approved']}", 0.5)
                            return True
                        else:
                            self.log_test("Trade Validation", False, "Invalid response format", 0.5)
                            return False
                    else:
                        self.log_test("Trade Validation", False, f"HTTP {trade_response.status_code}", 0.5)
                        return False
                else:
                    self.log_test("Risk Assessment", False, "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Risk Assessment", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Risk Management", False, str(e), 0)
            return False
    
    def test_cost_optimization(self) -> bool:
        """Test cost optimization system"""
        print("\n💰 Testing Cost Optimization...")
        
        try:
            # Test cost limit check
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/ai/risk-cost/cost/check-limits",
                json={"provider": "openai", "estimated_cost_cents": 100},
                headers=self.headers,
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "within_limits" in data and "usage_percentage" in data:
                    self.log_test("Cost Limit Check", True, f"Within limits: {data['within_limits']}", response_time)
                    
                    # Test cost report
                    report_response = requests.get(
                        f"{self.base_url}/api/ai/risk-cost/cost/report?days=7",
                        headers=self.headers,
                        timeout=15
                    )
                    
                    if report_response.status_code == 200:
                        report_data = report_response.json()
                        if "summary" in report_data:
                            self.log_test("Cost Report", True, f"Total cost: {report_data['summary'].get('total_cost_cents', 0)} cents", 0.5)
                            return True
                        else:
                            self.log_test("Cost Report", False, "Invalid response format", 0.5)
                            return False
                    else:
                        self.log_test("Cost Report", False, f"HTTP {report_response.status_code}", 0.5)
                        return False
                else:
                    self.log_test("Cost Limit Check", False, "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Cost Limit Check", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Cost Optimization", False, str(e), 0)
            return False
    
    def test_learning_system(self) -> bool:
        """Test learning system"""
        print("\n🧠 Testing Learning System...")
        
        try:
            # Test feedback submission
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/ai/learning/feedback",
                json={
                    "feedback_type": "signal_accuracy",
                    "item_id": "test_signal_123",
                    "rating": 4,
                    "comments": "Good signal accuracy",
                    "metadata": {"provider_used": "openai"}
                },
                headers=self.headers,
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "success":
                    self.log_test("Feedback Submission", True, "Feedback recorded", response_time)
                    
                    # Test learning insights
                    insights_response = requests.get(
                        f"{self.base_url}/api/ai/learning/insights",
                        headers=self.headers,
                        timeout=15
                    )
                    
                    if insights_response.status_code == 200:
                        insights_data = insights_response.json()
                        if "insights" in insights_data and "learning_status" in insights_data:
                            self.log_test("Learning Insights", True, f"Learning active: {insights_data['learning_status'].get('learning_active')}", 0.5)
                            return True
                        else:
                            self.log_test("Learning Insights", False, "Invalid response format", 0.5)
                            return False
                    else:
                        self.log_test("Learning Insights", False, f"HTTP {insights_response.status_code}", 0.5)
                        return False
                else:
                    self.log_test("Feedback Submission", False, "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Feedback Submission", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Learning System", False, str(e), 0)
            return False
    
    def test_monitoring_system(self) -> bool:
        """Test monitoring and error handling system"""
        print("\n📈 Testing Monitoring System...")
        
        try:
            # Test error summary
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/api/ai/monitoring/errors/summary?hours=24",
                headers=self.headers,
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "health_status" in data and "total_errors" in data:
                    self.log_test("Error Summary", True, f"Health: {data['health_status']}, Errors: {data['total_errors']}", response_time)
                    
                    # Test performance metrics
                    perf_response = requests.get(
                        f"{self.base_url}/api/ai/monitoring/performance/ai-providers",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if perf_response.status_code == 200:
                        perf_data = perf_response.json()
                        if "provider_metrics" in perf_data:
                            self.log_test("Performance Metrics", True, f"Providers monitored: {len(perf_data['provider_metrics'])}", 0.3)
                            return True
                        else:
                            self.log_test("Performance Metrics", False, "Invalid response format", 0.3)
                            return False
                    else:
                        self.log_test("Performance Metrics", False, f"HTTP {perf_response.status_code}", 0.3)
                        return False
                else:
                    self.log_test("Error Summary", False, "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Error Summary", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Monitoring System", False, str(e), 0)
            return False
    
    def run_all_tests(self) -> bool:
        """Run all deployment verification tests"""
        print(f"🚀 Starting Deployment Verification for {self.base_url}")
        print(f"👤 User ID: {self.user_id}")
        print("=" * 60)
        
        test_functions = [
            self.test_health_endpoints,
            self.test_ai_chat_engine,
            self.test_signal_generation,
            self.test_strategy_generation,
            self.test_risk_management,
            self.test_cost_optimization,
            self.test_learning_system,
            self.test_monitoring_system
        ]
        
        passed_tests = 0
        total_tests = len(test_functions)
        
        for test_func in test_functions:
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ Test {test_func.__name__} failed with exception: {e}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 DEPLOYMENT VERIFICATION SUMMARY")
        print("=" * 60)
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"✅ Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - Deployment is fully functional!")
            return True
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed - Check logs above")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate detailed test report"""
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        return {
            "deployment_url": self.base_url,
            "user_id": self.user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": total - passed,
                "success_rate": (passed / total * 100) if total > 0 else 0
            },
            "test_results": self.test_results
        }

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify AI Engine deployment")
    parser.add_argument("--url", default="https://web-production-de0bc.up.railway.app", help="Base URL to test")
    parser.add_argument("--user-id", default="test_user_deployment", help="User ID for testing")
    parser.add_argument("--report", action="store_true", help="Generate JSON report")
    
    args = parser.parse_args()
    
    verifier = DeploymentVerifier(args.url, args.user_id)
    success = verifier.run_all_tests()
    
    if args.report:
        report = verifier.generate_report()
        with open("deployment_verification_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: deployment_verification_report.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())