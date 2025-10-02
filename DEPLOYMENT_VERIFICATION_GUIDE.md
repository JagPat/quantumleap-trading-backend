# Backend Deployment Verification Guide

This guide helps verify that the backend is properly deployed and responding to health checks on Railway.

## 🚨 Critical Issue: Railway Health Check Failures

**Problem**: Backend builds succeed but health checks fail because `/health` endpoint doesn't respond with 200.

**Root Cause**: Missing dynamic port binding and incomplete health endpoint configuration.

## ✅ Solution Implementation

### 1. Dynamic Port Binding

**Fixed**: Backend now properly binds to `process.env.PORT` (Railway injects this).

**Verification**: Look for this log message:
```
🚀 Server running on port ${PORT}
```

### 2. Health Check Endpoint

**Fixed**: `/health` endpoint now returns proper 200 response with required fields:

```json
{
  "status": "ok",
  "commit": "abc12345...",
  "time": "2025-10-02T12:00:00.000Z",
  "uptime": 123.456,
  "port": 4000,
  "version": "2.0.0",
  "ready": true
}
```

**Key Features**:
- ✅ Always returns 200 status
- ✅ Lightweight (no DB calls)
- ✅ Includes commit SHA for verification
- ✅ Includes port number for debugging

### 3. Version Endpoint

**Fixed**: `/api/version` endpoint returns comprehensive build information:

```json
{
  "success": true,
  "data": {
    "service": "quantum-leap-backend",
    "commit": "abc12345...",
    "buildTime": "2025-10-02T12:00:00Z",
    "imageDigest": "sha256:...",
    "nodeVersion": "v20.x.x",
    "environment": "production",
    "uptime": 123.456,
    "memory": {...},
    "timestamp": "2025-10-02T12:00:00.000Z"
  }
}
```

### 4. Railway Configuration

**Fixed**: Dockerfile now uses dynamic PORT binding:

```dockerfile
# Railway will set PORT env var dynamically
ENV PORT=4000

# Health check - use dynamic PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD node -e "require('http').get('http://localhost:' + (process.env.PORT || 4000) + '/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"
```

**Key Changes**:
- ✅ Removed hardcoded `EXPOSE 4000`
- ✅ Health check uses dynamic PORT
- ✅ Railway manages port assignment

## 🧪 Testing

### Local Testing

Run the integration test locally:

```bash
# Test with dynamic port
PORT=4000 npm start

# In another terminal, run integration test
node tests/health-check.test.js

# Or test manually
curl http://localhost:4000/health
curl http://localhost:4000/api/version
```

### Expected Test Results

```
🧪 Backend Health Check Integration Test
==========================================

🚀 Starting backend server...
📊 🚀 Server running on port 4000
✅ Server is responding

🔍 Testing /health endpoint...
✅ Health endpoint test PASSED
   Status: ok
   Commit: unknown
   Port: 4000
   Time: 2025-10-02T12:00:00.000Z

🔍 Testing /api/version endpoint...
✅ Version endpoint test PASSED
   Service: quantum-leap-backend
   Commit: unknown
   Build Time: unknown
   Node Version: v20.x.x

📊 Test Results:
================
Health Endpoint: ✅ PASS
Version Endpoint: ✅ PASS

Overall: ✅ ALL TESTS PASSED
```

## 🔍 Railway Deployment Verification

### 1. Check Railway Logs

Look for these log messages in Railway deployment logs:

```
🚀 Server running on port 8080
✅ QuantumLeap Trading Backend server running on port 8080
❤️ Health check: http://0.0.0.0:8080/health
```

**Note**: Port number will be different (Railway assigns dynamically).

### 2. Test Health Endpoint

```bash
# Test Railway deployment
curl https://web-production-de0bc.up.railway.app/health

# Expected response:
{
  "status": "ok",
  "commit": "abc12345...",
  "time": "2025-10-02T12:00:00.000Z",
  "uptime": 123.456,
  "port": 8080,
  "version": "2.0.0",
  "ready": true
}
```

### 3. Test Version Endpoint

```bash
# Test Railway deployment
curl https://web-production-de0bc.up.railway.app/api/version

# Expected response:
{
  "success": true,
  "data": {
    "service": "quantum-leap-backend",
    "commit": "abc12345...",
    "buildTime": "2025-10-02T12:00:00Z",
    "nodeVersion": "v20.x.x",
    "environment": "production",
    "uptime": 123.456,
    "timestamp": "2025-10-02T12:00:00.000Z"
  }
}
```

## 🚨 Troubleshooting

### Issue: Health Check Still Failing

**Check Railway Logs For**:
1. `🚀 Server running on port ${PORT}` - Server started correctly
2. `✅ Internal health check: 200` - Internal health check passed
3. Any error messages during startup

**Common Issues**:
- **Port binding**: Ensure server binds to `0.0.0.0`, not `localhost`
- **Health check path**: Railway should use `/health` path
- **Startup time**: Health check has 30s start period, should be enough

### Issue: Commit SHA Shows "unknown"

**Cause**: Railway not injecting build arguments.

**Solution**: Configure Railway build args:
1. Go to Railway dashboard → Backend service → Settings
2. Add build argument: `COMMIT_SHA=${{ github.sha }}`
3. Redeploy

### Issue: Server Not Starting

**Check For**:
1. Database connection errors
2. Missing environment variables
3. Port conflicts
4. Module initialization failures

**Debug Steps**:
1. Check Railway deployment logs
2. Run integration test locally
3. Test with `PORT=4000 npm start`

## 📋 Verification Checklist

Before considering deployment successful:

- [ ] ✅ Server logs show `🚀 Server running on port ${PORT}`
- [ ] ✅ `/health` endpoint returns 200 with `status: "ok"`
- [ ] ✅ `/api/version` endpoint returns 200 with build info
- [ ] ✅ Railway health check passes (green status)
- [ ] ✅ Integration test passes locally
- [ ] ✅ Commit SHA matches expected (if build args configured)

## 🔧 Quick Commands

```bash
# Test locally
PORT=4000 npm start
node tests/health-check.test.js

# Test Railway deployment
curl https://web-production-de0bc.up.railway.app/health
curl https://web-production-de0bc.up.railway.app/api/version

# Check Railway logs
# (Manual check via Railway dashboard)
```

## 📊 Expected Railway Behavior

1. **Build**: Should succeed (no syntax errors)
2. **Startup**: Server starts and binds to Railway-assigned port
3. **Health Check**: Railway health check passes within 30s
4. **Endpoints**: Both `/health` and `/api/version` respond correctly
5. **Logs**: Clear startup messages with port information

**If deployment fails, check logs for `🚀 Server running on port …` and test `/health`.**
