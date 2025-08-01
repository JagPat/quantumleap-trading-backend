#!/usr/bin/env python3
"""
Production Monitoring Dashboard
Real-time monitoring of Railway deployment
"""

import requests
import time
import json
from datetime import datetime

class ProductionMonitoringDashboard:
    def __init__(self, base_url):
        self.base_url = base_url
        self.monitoring_interval = 60  # seconds
    
    def get_system_status(self):
        """Get current system status"""
        try:
            # Health check
            health_response = requests.get(f"{self.base_url}/health", timeout=10)
            health_data = health_response.json() if health_response.status_code == 200 else {}
            
            # Metrics
            metrics_response = requests.get(f"{self.base_url}/metrics", timeout=10)
            metrics_data = metrics_response.json() if metrics_response.status_code == 200 else {}
            
            # Trading engine status
            trading_response = requests.get(f"{self.base_url}/api/trading-engine/status", timeout=10)
            trading_data = trading_response.json() if trading_response.status_code == 200 else {}
            
            return {
                "timestamp": datetime.now().isoformat(),
                "health": health_data,
                "metrics": metrics_data,
                "trading_engine": trading_data,
                "response_times": {
                    "health": health_response.elapsed.total_seconds() if health_response.status_code == 200 else None,
                    "metrics": metrics_response.elapsed.total_seconds() if metrics_response.status_code == 200 else None,
                    "trading": trading_response.elapsed.total_seconds() if trading_response.status_code == 200 else None
                }
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "error"
            }
    
    def display_status(self, status):
        """Display system status"""
        print("\n" + "="*60)
        print(f"🚀 PRODUCTION MONITORING - {status['timestamp']}")
        print("="*60)
        
        if "error" in status:
            print(f"❌ Error: {status['error']}")
            return
        
        # Health status
        health = status.get("health", {})
        health_status = health.get("status", "unknown")
        print(f"🏥 Health: {health_status}")
        
        # Response times
        response_times = status.get("response_times", {})
        for endpoint, time_taken in response_times.items():
            if time_taken:
                print(f"⏱️  {endpoint.title()}: {time_taken:.3f}s")
        
        # Trading engine
        trading = status.get("trading_engine", {})
        if trading:
            print(f"🤖 Trading Engine: {trading.get('status', 'unknown')}")
            if 'active_strategies' in trading:
                print(f"📊 Active Strategies: {trading['active_strategies']}")
        
        # System metrics
        metrics = status.get("metrics", {})
        if metrics:
            print("📈 System Metrics:")
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    print(f"   {key}: {value}")
    
    def run_monitoring(self):
        """Run continuous monitoring"""
        print("🚀 Starting Production Monitoring Dashboard...")
        print(f"📡 Monitoring: {self.base_url}")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                status = self.get_system_status()
                self.display_status(status)
                
                # Log to file
                with open("production_monitoring.log", "a") as f:
                    f.write(json.dumps(status) + "\n")
                
                time.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")

if __name__ == "__main__":
    import sys
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://quantum-leap-backend-production.up.railway.app"
    
    dashboard = ProductionMonitoringDashboard(base_url)
    dashboard.run_monitoring()
