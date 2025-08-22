#!/usr/bin/env python3
"""
Railway Production Deployment Script
Deploys the automated trading engine to Railway production environment
"""

import os
import sys
import json
import subprocess
import requests
import time
from datetime import datetime
from pathlib import Path

class RailwayProductionDeployer:
    """Handles deployment to Railway production environment"""
    
    def __init__(self):
        self.railway_url = "https://quantum-leap-backend-production.up.railway.app"
        self.deployment_config = {
            "service_name": "quantum-leap-trading-engine",
            "environment": "production",
            "python_version": "3.11",
            "start_command": "python3 production_main.py"
        }
    
    def create_railway_config(self):
        """Create Railway-specific configuration files"""
        print("⚙️ Creating Railway configuration...")
        
        # Create railway.json
        railway_config = {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {
                "builder": "NIXPACKS"
            },
            "deploy": {
                "startCommand": self.deployment_config["start_command"],
                "healthcheckPath": "/health",
                "healthcheckTimeout": 300,
                "restartPolicyType": "ON_FAILURE",
                "restartPolicyMaxRetries": 3
            }
        }
        
        with open("railway.json", "w") as f:
            json.dump(railway_config, f, indent=2)
        
        # Create Procfile for Railway
        with open("Procfile", "w") as f:
            f.write(f"web: {self.deployment_config['start_command']}\n")
        
        # Create requirements.txt with all dependencies
        requirements = [
            "fastapi>=0.104.1",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.5.0",
            "python-multipart>=0.0.6",
            "requests>=2.31.0",
            "python-jose[cryptography]>=3.3.0",
            "passlib[bcrypt]>=1.7.4",
            "python-dotenv>=1.0.0",
            "sqlalchemy>=2.0.23",
            "alembic>=1.13.1",
            "redis>=5.0.1",
            "celery>=5.3.4",
            "psutil>=5.9.6",
            "numpy>=1.24.3",
            "pandas>=2.0.3",
            "scikit-learn>=1.3.0",
            "openai>=1.3.0",
            "anthropic>=0.7.0",
            "google-generativeai>=0.3.0"
        ]
        
        with open("requirements.txt", "w") as f:
            for req in requirements:
                f.write(f"{req}\n")
        
        # Create runtime.txt
        with open("runtime.txt", "w") as f:
            f.write(f"python-{self.deployment_config['python_version']}\n")
        
        print("✅ Railway configuration created")
    
    def create_environment_variables(self):
        """Create environment variables configuration"""
        print("🔧 Setting up environment variables...")
        
        env_vars = {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "sqlite:///production_trading.db",
            "REDIS_URL": "redis://localhost:6379",
            "LOG_LEVEL": "INFO",
            "MAX_CONCURRENT_STRATEGIES": "50",
            "MAX_ORDERS_PER_MINUTE": "100",
            "BACKUP_INTERVAL": "3600",
            "MONITORING_INTERVAL": "60",
            "CORS_ORIGINS": "https://quantum-leap-frontend.vercel.app,http://localhost:3000",
            "API_RATE_LIMIT": "1000/hour",
            "HEALTH_CHECK_TIMEOUT": "30"
        }
        
        # Create .env file for local testing
        with open(".env.production", "w") as f:
            f.write("# Production Environment Variables\n")
            f.write("# Deploy these to Railway environment\n\n")
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        print("✅ Environment variables configured")
        print("📝 Please set these variables in Railway dashboard:")
        for key, value in env_vars.items():
            print(f"   {key}={value}")
    
    def create_deployment_scripts(self):
        """Create deployment and management scripts"""
        print("📜 Creating deployment scripts...")
        
        # Create deployment verification script
        deploy_verify_script = '''#!/usr/bin/env python3
"""
Railway Deployment Verification Script
"""

import requests
import time
import sys
from datetime import datetime

def verify_deployment(base_url, max_retries=10, retry_delay=30):
    """Verify Railway deployment is working"""
    print(f"🔍 Verifying deployment at {base_url}")
    
    for attempt in range(max_retries):
        try:
            # Test health endpoint
            response = requests.get(f"{base_url}/health", timeout=30)
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed: {health_data.get('status', 'unknown')}")
                
                # Test trading engine status
                response = requests.get(f"{base_url}/api/trading-engine/status", timeout=30)
                if response.status_code == 200:
                    print("✅ Trading engine endpoint accessible")
                    
                    # Test metrics endpoint
                    response = requests.get(f"{base_url}/metrics", timeout=30)
                    if response.status_code == 200:
                        print("✅ Metrics endpoint accessible")
                        print("🎉 Deployment verification successful!")
                        return True
                    else:
                        print(f"⚠️ Metrics endpoint returned {response.status_code}")
                else:
                    print(f"⚠️ Trading engine endpoint returned {response.status_code}")
            else:
                print(f"❌ Health check failed: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            print(f"⏳ Waiting {retry_delay} seconds before retry...")
            time.sleep(retry_delay)
    
    print("❌ Deployment verification failed after all retries")
    return False

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://quantum-leap-backend-production.up.railway.app"
    success = verify_deployment(base_url)
    sys.exit(0 if success else 1)
'''
        
        with open("verify_railway_deployment.py", "w") as f:
            f.write(deploy_verify_script)
        
        # Create production monitoring script
        prod_monitor_script = '''#!/usr/bin/env python3
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
        print("\\n" + "="*60)
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
                    f.write(json.dumps(status) + "\\n")
                
                time.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            print("\\n🛑 Monitoring stopped by user")

if __name__ == "__main__":
    import sys
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://quantum-leap-backend-production.up.railway.app"
    
    dashboard = ProductionMonitoringDashboard(base_url)
    dashboard.run_monitoring()
'''
        
        with open("production_monitoring_dashboard.py", "w") as f:
            f.write(prod_monitor_script)
        
        # Make scripts executable
        os.chmod("verify_railway_deployment.py", 0o755)
        os.chmod("production_monitoring_dashboard.py", 0o755)
        
        print("✅ Deployment scripts created")
    
    def create_deployment_guide(self):
        """Create comprehensive deployment guide"""
        print("📚 Creating deployment guide...")
        
        guide_content = '''# Railway Production Deployment Guide

## Overview

This guide covers deploying the Quantum Leap Automated Trading Engine to Railway's production environment.

## Prerequisites

1. Railway account with CLI installed
2. GitHub repository with the codebase
3. Production configuration files created
4. Environment variables configured

## Deployment Steps

### 1. Prepare Repository

Ensure your repository contains:
- `production_main.py` - Production application entry point
- `railway.json` - Railway configuration
- `Procfile` - Process configuration
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification
- `.env.production` - Environment variables template

### 2. Deploy to Railway

```bash
# Login to Railway
railway login

# Create new project (if not exists)
railway init

# Set environment variables
railway variables set ENVIRONMENT=production
railway variables set DATABASE_URL=sqlite:///production_trading.db
railway variables set LOG_LEVEL=INFO
railway variables set MAX_CONCURRENT_STRATEGIES=50
railway variables set MAX_ORDERS_PER_MINUTE=100
railway variables set CORS_ORIGINS=https://quantum-leap-frontend.vercel.app

# Deploy
railway up
```

### 3. Verify Deployment

```bash
# Run verification script
python3 verify_railway_deployment.py

# Check logs
railway logs

# Monitor deployment
python3 production_monitoring_dashboard.py
```

## Environment Variables

Set these variables in Railway dashboard:

| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | Environment identifier |
| `DATABASE_URL` | `sqlite:///production_trading.db` | Database connection |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_CONCURRENT_STRATEGIES` | `50` | Maximum concurrent strategies |
| `MAX_ORDERS_PER_MINUTE` | `100` | Rate limiting |
| `CORS_ORIGINS` | `https://quantum-leap-frontend.vercel.app` | CORS configuration |

## Health Checks

Railway will automatically monitor these endpoints:

- `/health` - Application health status
- `/metrics` - System performance metrics
- `/api/trading-engine/status` - Trading engine status

## Monitoring

### Real-time Monitoring

```bash
# Start monitoring dashboard
python3 production_monitoring_dashboard.py
```

### Log Monitoring

```bash
# View Railway logs
railway logs --follow

# View local logs
tail -f production.log
```

## Backup Procedures

### Automated Backups

The system includes automated database backups:

```bash
# Manual backup
python3 database_backup.py

# Setup automated backups (if using server)
./setup_backup_schedule.sh
```

### Backup Verification

```bash
# Verify latest backup
python3 -c "
from database_backup import DatabaseBackupManager
manager = DatabaseBackupManager()
backups = list(manager.backup_dir.glob('*.db.gz'))
if backups:
    latest = max(backups, key=lambda x: x.stat().st_mtime)
    print(f'Latest backup: {latest}')
    manager.verify_backup(latest)
else:
    print('No backups found')
"
```

## Troubleshooting

### Common Issues

1. **Deployment Fails**
   - Check `railway logs` for errors
   - Verify all dependencies in `requirements.txt`
   - Ensure environment variables are set

2. **Health Check Fails**
   - Check application startup logs
   - Verify database connectivity
   - Test endpoints locally

3. **High Response Times**
   - Monitor system metrics
   - Check database performance
   - Review concurrent strategy limits

### Emergency Procedures

1. **Emergency Stop**
   ```bash
   # Stop all trading activities
   curl -X POST https://your-app.railway.app/api/trading-engine/emergency-stop
   ```

2. **Rollback Deployment**
   ```bash
   # Rollback to previous version
   railway rollback
   ```

3. **Scale Resources**
   ```bash
   # Scale up resources in Railway dashboard
   # Or use Railway CLI
   railway scale
   ```

## Performance Optimization

### Database Optimization

- Regular VACUUM operations
- Index optimization
- Connection pooling

### Application Optimization

- Memory usage monitoring
- CPU usage optimization
- Request rate limiting

## Security Considerations

1. **Environment Variables**
   - Never commit sensitive data
   - Use Railway's secure variable storage
   - Rotate API keys regularly

2. **Network Security**
   - Configure CORS properly
   - Use HTTPS only
   - Implement rate limiting

3. **Database Security**
   - Regular backups
   - Access logging
   - Data encryption at rest

## Maintenance

### Regular Tasks

- [ ] Monitor system health daily
- [ ] Review logs weekly
- [ ] Update dependencies monthly
- [ ] Test backup restoration quarterly
- [ ] Performance review quarterly

### Updates

1. Test changes in staging environment
2. Deploy during low-traffic periods
3. Monitor deployment closely
4. Have rollback plan ready

## Support

For issues with:
- Railway platform: Railway support
- Application code: Development team
- Trading engine: Trading team
- AI components: AI team

## Monitoring Dashboards

- Railway Dashboard: Application metrics
- Custom Dashboard: `production_monitoring_dashboard.py`
- Health Checks: `/health` endpoint
- Performance Metrics: `/metrics` endpoint
'''
        
        with open("RAILWAY_PRODUCTION_DEPLOYMENT_GUIDE.md", "w") as f:
            f.write(guide_content)
        
        print("✅ Deployment guide created")
    
    def deploy_to_railway(self):
        """Complete Railway deployment process"""
        print("🚀 Starting Railway Production Deployment...\n")
        
        try:
            # Create Railway configuration
            self.create_railway_config()
            
            # Setup environment variables
            self.create_environment_variables()
            
            # Create deployment scripts
            self.create_deployment_scripts()
            
            # Create deployment guide
            self.create_deployment_guide()
            
            print("\n" + "="*60)
            print("🎉 RAILWAY DEPLOYMENT PREPARATION COMPLETE!")
            print("="*60)
            print("\n📋 Next Steps:")
            print("1. Review RAILWAY_PRODUCTION_DEPLOYMENT_GUIDE.md")
            print("2. Set environment variables in Railway dashboard")
            print("3. Run: railway up")
            print("4. Verify deployment: python3 verify_railway_deployment.py")
            print("5. Start monitoring: python3 production_monitoring_dashboard.py")
            print("\n🚀 Your automated trading engine is ready for Railway!")
            
            return True
            
        except Exception as e:
            print(f"❌ Railway deployment preparation failed: {e}")
            return False

def main():
    """Main deployment function"""
    deployer = RailwayProductionDeployer()
    success = deployer.deploy_to_railway()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)