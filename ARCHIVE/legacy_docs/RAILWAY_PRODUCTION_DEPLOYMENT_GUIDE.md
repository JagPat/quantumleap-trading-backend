# Railway Production Deployment Guide

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
