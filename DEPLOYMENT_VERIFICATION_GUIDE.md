# Backend Deployment Verification Guide

## Manual Railway Redeploy Procedure

### When Auto-Deploy Fails
If Railway doesn't automatically deploy after pushing to GitHub:

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Select Backend Service**: `QuntumTrade_Backend` or similar  
3. **Click "Deployments" Tab**
4. **Click "Deploy" or "Redeploy"**:
   - Ensure deploying from `main` branch
   - Latest commit should match your local: `git log -1 --oneline`
5. **Optional: Clear Build Cache**:
   - Click "..." menu on deployment
   - Select "Clear Cache and Redeploy"
6. **Wait 3-5 minutes** for deployment to complete

### Verify Deployment Success

#### 1. Health Endpoint Check
```bash
curl https://web-production-de0bc.up.railway.app/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "commit": "1c189b7",
  "version": "2.1.0",
  "time": "2025-10-02T...",
  "uptime": 45.67,
  "port": "8080",
  "ready": true
}
```

❌ **If commit shows "unknown"**: See `RAILWAY_DEPLOYMENT_CONFIG.md`

#### 2. Startup Logs Check
```
🚀 Server running on port 8080 (commit=1c189b7)
📝 Commit SHA: 1c189b7
```

#### 3. OAuth Callback Logs
```
🔍 [OAuth] Fetching user profile from Zerodha API...
🔑 [OAuth] Using broker user_id from profile: EBW183
```

#### 4. AI Validation Endpoint
```bash
curl -X POST https://web-production-de0bc.up.railway.app/api/ai/validate-key \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"test"}'
```

Expected: `{"valid": false, "message": "Invalid OpenAI API key"}`  
❌ If 404: Old version still deployed

### Post-Deployment User Actions

1. Clear localStorage: `localStorage.clear()`
2. Reconnect to Zerodha
3. Verify session has `user_id`
4. Test AI Configuration

---
**Last Updated**: 2025-10-02  
**Expected Version**: >= 2.1.0
