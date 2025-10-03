# Backend Deployment Verification Guide

## Overview

This guide helps you verify that the backend is correctly deployed on Railway with the latest code from GitHub.

---

## 1. Verify GitHub → Railway Sync

### Check Latest GitHub Commit

```bash
# In backend-temp directory
cd backend-temp
git log -1 --oneline
```

Expected output: Shows the latest commit SHA (e.g., `ff9957c`)

### Check Railway Deployment Commit

```bash
curl -s https://web-production-de0bc.up.railway.app/health | jq '.commit'
```

Expected output: Should match the GitHub commit SHA (first 7 characters)

**✅ If they match**: Railway is running the latest code  
**❌ If they don't match**: Railway needs manual redeploy

---

## 2. Manual Redeploy Procedure

If Railway auto-deploy doesn't trigger:

1. **Go to Railway Dashboard**
   - URL: https://railway.app
   - Select your project

2. **Select Backend Service**
   - Service name: `QuntumTrade_Backend` or `web-production-de0bc`

3. **Trigger Redeploy**
   - **Option A**: Deployments tab → Click `⋮` (three dots) → `Redeploy`
   - **Option B**: Settings tab → Click `Trigger Deploy` button

4. **Wait for Build**
   - Build typically takes 2-3 minutes
   - Watch the logs for any errors

5. **Verify Deployment**
   - Check `/health` endpoint again (see Section 3)

---

## 3. Verify /health Shows Correct Commit SHA

### Health Check Endpoint

```bash
curl -s https://web-production-de0bc.up.railway.app/health | jq '.'
```

### Expected Response

```json
{
  "status": "ok",
  "commit": "ff9957c",  // ← Should match GitHub commit
  "time": "2025-10-03T06:54:58.800Z",
  "uptime": 123.45,  // ← Should be LOW after redeploy (<60 seconds)
  "port": "8080",
  "version": "2.1.0",
  "ready": true
}
```

### Verification Checklist

- [ ] `status` = `"ok"`
- [ ] `commit` matches GitHub latest commit
- [ ] `uptime` is low (if just redeployed)
- [ ] `ready` = `true`

---

## 4. Verify Critical Endpoints

### OAuth Callback Endpoint

```bash
curl -X POST https://web-production-de0bc.up.railway.app/api/broker/callback \
  -H "Content-Type: application/json" \
  -d '{"request_token":"test","state":"test","config_id":"test"}' \
  | jq '.'
```

**Expected**: Should return error (missing valid data) but **NOT 404**

- ✅ `{"success":false,"error":"Invalid callback data"}` → Endpoint exists
- ❌ `{"error":"Route not found"}` → Endpoint missing

### AI Validate Key Endpoint

```bash
curl -X POST https://web-production-de0bc.up.railway.app/api/ai/validate-key \
  -H "Content-Type: application/json" \
  -H "X-Config-ID: test-config" \
  -d '{"provider":"openai","api_key":"test"}' \
  | jq '.'
```

**Expected**: Should return validation error (invalid key) but **NOT 404**

- ✅ `{"valid":false,"message":"..."}` → Endpoint exists
- ❌ `{"error":"Route not found"}` → Endpoint missing

---

## 5. Check Railway Logs for OAuth Profile Fetch

### Access Railway Logs

1. Railway Dashboard → Backend Service
2. Click `Logs` tab
3. Filter for recent logs

### Look for These Log Messages

After a user connects to Zerodha, you should see:

```
🔍 [OAuth] Complete Zerodha session data: {...}
🔍 [OAuth] Fetching user profile from Zerodha API...
🔍 [OAuth] Zerodha profile response: {"status":"success","data":{"user_id":"EBW183",...}}
🔑 [OAuth] Using broker user_id from profile: EBW183
🔑 [OAuth] Final broker user_id: EBW183
🔄 Redirecting to frontend: https://quantum-leap-frontend-production.up.railway.app/broker-callback?status=success&config_id=...&user_id=EBW183
🔑 Redirect includes user_id: EBW183
```

**✅ If you see these logs**: OAuth user_id extraction is working  
**❌ If missing**: OAuth callback might not be triggered or failing

---

## 6. Verify Server Startup Logs

### Expected Startup Sequence

```
🚀 Server running on port 8080 (commit=ff9957c)
📝 Commit SHA: ff9957c
✅ PostgreSQL connection pool established
🔐 [Auth] Auth module loaded
🔐 [Auth] OAuth routes registered at /api/broker/*
🤖 [AI] AI routes registered at /api/ai/*
🚀 Quantum Leap Trading Backend - Modular Structure Ready
```

### Verify Each Component

- [ ] Server starts on correct port (from `$PORT` env var)
- [ ] Commit SHA is logged correctly
- [ ] Database connection successful
- [ ] Auth module loaded
- [ ] OAuth routes registered (`/api/broker/*`)
- [ ] AI routes registered (`/api/ai/*`)

---

## 7. Test OAuth Flow End-to-End

### Prerequisites

- Frontend is deployed (https://quantum-leap-frontend-production.up.railway.app)
- Backend is deployed (https://web-production-de0bc.up.railway.app)
- Zerodha API credentials configured

### Steps

1. **Clear Browser Storage**
   ```javascript
   localStorage.clear();
   sessionStorage.clear();
   location.reload();
   ```

2. **Connect to Zerodha**
   - Go to Broker Integration page
   - Enter API Key and Secret
   - Click "Connect to Zerodha"
   - Complete OAuth in popup

3. **Verify Session in LocalStorage**
   ```javascript
   JSON.parse(localStorage.getItem('activeBrokerSession'))
   ```
   
   Expected output:
   ```json
   {
     "config_id": "820195a8-f9f9-479a-bcb2-690073a1d8a3",
     "user_id": "EBW183",  // ← Should NOT be null
     "broker_name": "zerodha",
     "session_status": "connected",
     "needs_reauth": false
   }
   ```

4. **Test AI Configuration**
   - Go to AI Configuration page
   - Enter OpenAI API key
   - Click "Test" → Should validate
   - Click "Save Configuration" → Should succeed without "No active broker connection found" error

---

## 8. Common Issues and Troubleshooting

### Issue: Health Check Shows Old Commit

**Symptom**: `/health` returns old commit SHA, uptime is very high

**Cause**: Railway didn't autodeploy or deployment failed

**Fix**:
1. Check Railway dashboard for deployment errors
2. Manually trigger redeploy (see Section 2)
3. Verify GitHub webhook is configured correctly

### Issue: 404 on `/api/broker/callback`

**Symptom**: OAuth callback returns "Route not found"

**Cause**: Routes not registered or wrong endpoint path

**Fix**:
1. Check server startup logs for "OAuth routes registered"
2. Verify `modules/auth/routes/oauth.js` is loaded
3. Verify frontend calls `/api/broker/callback` (not `/api/modules/auth/broker/callback`)

### Issue: 404 on `/api/ai/validate-key`

**Symptom**: AI validation returns "Route not found"

**Cause**: AI routes not registered

**Fix**:
1. Check server startup logs for "AI routes registered"
2. Verify `server-modular.js` has: `app.use('/api/ai', aiRoutes);`
3. Redeploy with latest code

### Issue: CORS Errors for `X-Config-ID`

**Symptom**: Browser console shows "Request header field X-Config-ID is not allowed"

**Cause**: CORS configuration missing header

**Fix**:
1. Verify `server-modular.js` CORS config includes:
   ```javascript
   allowedHeaders: ['Content-Type', 'Authorization', 'X-Config-ID', 'X-User-ID']
   ```
2. Redeploy backend

### Issue: OAuth Completes but `user_id` is null

**Symptom**: Session has `config_id` but `user_id` is null/undefined

**Cause**: OAuth callback not fetching user profile from Zerodha API

**Fix**:
1. Check Railway logs for "Fetching user profile from Zerodha API"
2. If missing, verify `modules/auth/routes/oauth.js` has profile fetch code (lines 596-625)
3. Check for API errors in logs
4. Redeploy with latest code (commit bb320a1 or later)

---

## 9. Deployment Checklist

Use this checklist before and after deployment:

### Pre-Deployment

- [ ] All code changes committed to GitHub
- [ ] Tests pass locally
- [ ] Environment variables configured in Railway
- [ ] Database migrations run (if any)
- [ ] Frontend is compatible with backend changes

### Post-Deployment

- [ ] `/health` returns correct commit SHA
- [ ] `/health` shows `status: "ok"` and `ready: true`
- [ ] Server startup logs show all modules loaded
- [ ] OAuth routes registered (`/api/broker/*`)
- [ ] AI routes registered (`/api/ai/*`)
- [ ] CORS headers configured correctly
- [ ] Test endpoints return expected responses (not 404)
- [ ] OAuth flow completes and extracts `user_id`
- [ ] AI configuration save works without errors

---

## 10. Verify Railway Configuration

### Environment Variables Required

```
DATABASE_URL=postgresql://...
FRONTEND_URL=https://quantum-leap-frontend-production.up.railway.app
PORT=8080  # Set by Railway automatically
NODE_ENV=production
ZERODHA_API_KEY=...
ZERODHA_API_SECRET=...
JWT_SECRET=...
ENCRYPTION_KEY=...
```

### Build Settings

- **Builder**: Dockerfile
- **Dockerfile Path**: `Dockerfile`
- **Root Directory**: `/` (or backend-temp if using monorepo)

### Health Check Settings

- **Path**: `/health`
- **Interval**: 30s
- **Timeout**: 10s
- **Retries**: 3

---

## 11. Quick Verification Script

Run this script to verify everything at once:

```bash
#!/bin/bash

echo "🔍 Verifying Backend Deployment..."
echo ""

# Get GitHub commit
cd backend-temp
GITHUB_COMMIT=$(git log -1 --format="%h")
echo "GitHub Commit: $GITHUB_COMMIT"

# Get Railway commit
RAILWAY_COMMIT=$(curl -s https://web-production-de0bc.up.railway.app/health | jq -r '.commit')
echo "Railway Commit: $RAILWAY_COMMIT"

# Compare
if [ "$GITHUB_COMMIT" = "$RAILWAY_COMMIT" ]; then
  echo "✅ Commits match - Railway is up to date"
else
  echo "❌ Commits don't match - Railway needs redeploy"
  exit 1
fi

# Test endpoints
echo ""
echo "Testing /api/broker/callback..."
curl -s -o /dev/null -w "%{http_code}" -X POST https://web-production-de0bc.up.railway.app/api/broker/callback \
  -H "Content-Type: application/json" \
  -d '{"request_token":"test","state":"test","config_id":"test"}'

echo ""
echo "Testing /api/ai/validate-key..."
curl -s -o /dev/null -w "%{http_code}" -X POST https://web-production-de0bc.up.railway.app/api/ai/validate-key \
  -H "Content-Type: application/json" \
  -H "X-Config-ID: test" \
  -d '{"provider":"openai","api_key":"test"}'

echo ""
echo "✅ All verifications complete"
```

---

## Support

If you encounter issues not covered in this guide:

1. Check Railway logs for error messages
2. Verify environment variables are set correctly
3. Ensure database is accessible
4. Check GitHub repository for recent commits
5. Review recent code changes that might affect deployment

---

**Last Updated**: 2025-10-03  
**Backend Version**: 2.1.0  
**Latest Commit**: ff9957c
