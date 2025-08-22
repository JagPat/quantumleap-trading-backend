#!/usr/bin/env python3
"""
Comprehensive Backend API Testing Script
Tests all major endpoints to verify Railway deployment is working correctly
"""

import requests
import json
import time
from typing import Dict, Any, List

class BackendTester:
    def __init__(self, base_url: str = "https://web-production-de0bc.up.railway.app"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def test_endpoint(self, endpoint: str, method: str = 'GET', data: Dict = None, expected_status: int = 200) -> Dict[str, Any]:
        """Test a single endpoint and return results"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response_time = time.time() - start_time
            
            return {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'response_time': round(response_time * 1000, 2),  # ms
                'success': response.status_code == expected_status,
                'response_size': len(response.content),
                'content_type': response.headers.get('content-type', ''),
                'error': None
            }
            
        except Exception as e:
            return {
                'endpoint': endpoint,
                'method': method,
                'status_code': None,
                'response_time': None,
                'success': False,
                'response_size': 0,
                'content_type': '',
                'error': str(e)
            }

    def run_comprehensive_tests(self) -> Dict[str, List[Dict]]:
        """Run comprehensive tests on all major endpoints"""
        
        test_results = {
            'health_checks': [],
            'portfolio_endpoints': [],
            'ai_endpoints': [],
            'broker_endpoints': [],
            'trading_engine_endpoints': [],
            'database_endpoints': []
        }
        
        print("🚀 Starting Comprehensive Backend API Testing...")
        print(f"📍 Testing Base URL: {self.base_url}")
        print("=" * 80)
        
        # Health Check Endpoints
        print("\n🏥 Testing Health Check Endpoints...")
        health_endpoints = [
            ('/', 'GET'),
            ('/health', 'GET'),
            ('/api/health', 'GET'),
        ]
        
        for endpoint, method in health_endpoints:
            result = self.test_endpoint(endpoint, method)
            test_results['health_checks'].append(result)
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status} {method} {endpoint} - {result['status_code']} ({result['response_time']}ms)")
        
        # Portfolio Endpoints
        print("\n📊 Testing Portfolio Endpoints...")
        portfolio_endpoints = [
            ('/api/portfolio/fetch-live-simple', 'GET'),
            ('/api/portfolio/holdings', 'GET'),
            ('/api/portfolio/performance', 'GET'),
            ('/api/portfolio/summary', 'GET'),
        ]
        
        for endpoint, method in portfolio_endpoints:
            # Add test user_id parameter
            test_data = {'user_id': 'test_user'} if method == 'GET' else None
            result = self.test_endpoint(endpoint, method, test_data)
            test_results['portfolio_endpoints'].append(result)
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status} {method} {endpoint} - {result['status_code']} ({result['response_time']}ms)")
        
        # AI Endpoints
        print("\n🤖 Testing AI Endpoints...")
        ai_endpoints = [
            ('/api/ai/copilot/analyze', 'POST'),
            ('/api/ai/analysis/portfolio', 'POST'),
            ('/api/ai/analysis/market', 'GET'),
            ('/api/ai/analysis/signals', 'GET'),
        ]
        
        for endpoint, method in ai_endpoints:
            test_data = {'portfolio_data': {'test': 'data'}} if method == 'POST' else None
            result = self.test_endpoint(endpoint, method, test_data)
            test_results['ai_endpoints'].append(result)
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status} {method} {endpoint} - {result['status_code']} ({result['response_time']}ms)")
        
        # Broker Endpoints
        print("\n🏦 Testing Broker Endpoints...")
        broker_endpoints = [
            ('/api/broker/status', 'GET'),
            ('/api/broker/connect', 'POST'),
            ('/api/broker/positions', 'GET'),
        ]
        
        for endpoint, method in broker_endpoints:
            test_data = {'user_id': 'test_user'} if method == 'GET' else {'api_key': 'test', 'api_secret': 'test'}
            result = self.test_endpoint(endpoint, method, test_data)
            test_results['broker_endpoints'].append(result)
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status} {method} {endpoint} - {result['status_code']} ({result['response_time']}ms)")
        
        # Trading Engine Endpoints
        print("\n⚙️ Testing Trading Engine Endpoints...")
        trading_endpoints = [
            ('/api/trading/status', 'GET'),
            ('/api/trading/strategies', 'GET'),
            ('/api/trading/positions', 'GET'),
            ('/api/trading/orders', 'GET'),
        ]
        
        for endpoint, method in trading_endpoints:
            result = self.test_endpoint(endpoint, method)
            test_results['trading_engine_endpoints'].append(result)
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status} {method} {endpoint} - {result['status_code']} ({result['response_time']}ms)")
        
        # Database Endpoints
        print("\n🗄️ Testing Database Endpoints...")
        database_endpoints = [
            ('/api/database/health', 'GET'),
            ('/api/database/stats', 'GET'),
        ]
        
        for endpoint, method in database_endpoints:
            result = self.test_endpoint(endpoint, method)
            test_results['database_endpoints'].append(result)
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status} {method} {endpoint} - {result['status_code']} ({result['response_time']}ms)")
        
        return test_results
    
    def generate_summary_report(self, test_results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Generate a summary report of all test results"""
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        total_response_time = 0
        
        category_stats = {}
        
        for category, results in test_results.items():
            category_passed = sum(1 for r in results if r['success'])
            category_total = len(results)
            category_failed = category_total - category_passed
            
            category_response_times = [r['response_time'] for r in results if r['response_time'] is not None]
            avg_response_time = sum(category_response_times) / len(category_response_times) if category_response_times else 0
            
            category_stats[category] = {
                'total': category_total,
                'passed': category_passed,
                'failed': category_failed,
                'pass_rate': (category_passed / category_total * 100) if category_total > 0 else 0,
                'avg_response_time': round(avg_response_time, 2)
            }
            
            total_tests += category_total
            passed_tests += category_passed
            failed_tests += category_failed
            total_response_time += sum(category_response_times)
        
        overall_pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = total_response_time / total_tests if total_tests > 0 else 0
        
        return {
            'overall': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'pass_rate': round(overall_pass_rate, 2),
                'avg_response_time': round(avg_response_time, 2)
            },
            'categories': category_stats
        }
    
    def print_summary_report(self, summary: Dict[str, Any]):
        """Print a formatted summary report"""
        
        print("\n" + "=" * 80)
        print("📋 COMPREHENSIVE BACKEND TEST SUMMARY")
        print("=" * 80)
        
        overall = summary['overall']
        print(f"\n🎯 Overall Results:")
        print(f"   Total Tests: {overall['total_tests']}")
        print(f"   Passed: {overall['passed']} ✅")
        print(f"   Failed: {overall['failed']} ❌")
        print(f"   Pass Rate: {overall['pass_rate']}%")
        print(f"   Avg Response Time: {overall['avg_response_time']}ms")
        
        print(f"\n📊 Category Breakdown:")
        for category, stats in summary['categories'].items():
            status_icon = "✅" if stats['pass_rate'] == 100 else "⚠️" if stats['pass_rate'] >= 50 else "❌"
            print(f"   {status_icon} {category.replace('_', ' ').title()}:")
            print(f"      {stats['passed']}/{stats['total']} passed ({stats['pass_rate']}%)")
            print(f"      Avg Response: {stats['avg_response_time']}ms")
        
        # System Health Assessment
        print(f"\n🏥 System Health Assessment:")
        if overall['pass_rate'] >= 90:
            print("   🟢 EXCELLENT - System is fully operational")
        elif overall['pass_rate'] >= 75:
            print("   🟡 GOOD - System is mostly operational with minor issues")
        elif overall['pass_rate'] >= 50:
            print("   🟠 WARNING - System has significant issues that need attention")
        else:
            print("   🔴 CRITICAL - System has major issues and needs immediate attention")
        
        # Performance Assessment
        if overall['avg_response_time'] <= 500:
            print("   ⚡ FAST - Response times are excellent")
        elif overall['avg_response_time'] <= 1000:
            print("   🚀 GOOD - Response times are acceptable")
        elif overall['avg_response_time'] <= 2000:
            print("   ⏱️ SLOW - Response times need optimization")
        else:
            print("   🐌 VERY SLOW - Response times are unacceptable")

def main():
    """Main function to run comprehensive backend tests"""
    
    tester = BackendTester()
    
    # Run all tests
    test_results = tester.run_comprehensive_tests()
    
    # Generate and print summary
    summary = tester.generate_summary_report(test_results)
    tester.print_summary_report(summary)
    
    # Save detailed results to file
    with open('backend_test_results.json', 'w') as f:
        json.dump({
            'test_results': test_results,
            'summary': summary,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: backend_test_results.json")
    print("=" * 80)
    
    # Return exit code based on results
    return 0 if summary['overall']['pass_rate'] >= 75 else 1

if __name__ == "__main__":
    exit(main())