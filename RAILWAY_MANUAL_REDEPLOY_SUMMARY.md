# 🚨 Railway Manual Redeploy Required - Summary

**Date**: October 2, 2025  
**Issue**: Railway auto-deploy not working  
**Latest Commit**: `f25e47b`  
**Current Railway Version**: `2.0.0` (OLD - needs update to 2.1.0)

---

## ✅ Work Completed (Tasks 1-4)

### 1. Repository Sync ✅
- **Branch**: `main`
- **Status**: Clean, no uncommitted changes
- **Remote**: github.com/JagPat/quantumleap-trading-backend.git
- **Latest commit**: `f25e47b`

### 2. Commit SHA Injection ✅
Updated `server-modular.js`:
- Server startup logs now show: `🚀 Server running on port X (commit=abc1234)`
- `/health` endpoint returns actual commit SHA
- Checks multiple env vars: `COMMIT_SHA || RAILWAY_GIT_COMMIT_SHA || GITHUB_SHA`
- Version bumped to `2.1.0`

### 3. Documentation Created ✅
- **RAILWAY_DEPLOYMENT_CONFIG.md**: Environment variable setup guide
- **DEPLOYMENT_VERIFICATION_GUIDE.md**: Manual redeploy procedure and verification steps

### 4. Git Operations ✅
- All changes committed with detailed message
- Pushed to GitHub `main` branch
- Commit `f25e47b` available for Railway to deploy

---

## ⏳ Pending: Manual Railway Redeploy (Task 5)

### Why Manual Redeploy is Needed
Railway auto-deploy has failed to pick up the last 5+ commits:
- `f25e47b` - Commit SHA injection (LATEST)
- `1c189b7` - Force redeploy
- `415318a` - CORS X-Config-ID fix
- `c33b9b7` - AI validation endpoint
- `402aa85` - kiteconnect module

**Current Railway status**:
- Version: `2.0.0` (should be `2.1.0`)
- Commit: `unknown` (should be `f25e47b`)
- Uptime: 45+ minutes (no redeploy since fixes)

### Manual Redeploy Instructions

#### Step 1: Access Railway Dashboard
1. Go to: https://railway.app/dashboard
2. Find service: **QuntumTrade_Backend** (or backend service name)
3. Click to open service details

#### Step 2: Trigger Deployment
1. Navigate to **"Deployments"** tab
2. Click **"Deploy"** or **"Redeploy"** button
3. **Verify settings**:
   - Branch: `main` ✅
   - Latest commit: `f25e47b` or later ✅

#### Step 3: Clear Build Cache (RECOMMENDED)
1. Find the deployment in the list
2. Click **"..."** menu (three dots)
3. Select **"Clear Cache and Redeploy"**
4. This ensures old code/dependencies don't persist

#### Step 4: Wait for Completion
- Deployment takes: 3-5 minutes
- Watch build logs for errors
- Wait for "Deployed" status

---

## 🧪 Verification Steps (Tasks 6-8)

### After Railway Deployment Completes

#### 1. Health Endpoint Check
```bash
curl https://web-production-de0bc.up.railway.app/health | jq
```

**Expected Response**:
```json
{
  "status": "ok",
  "commit": "f25e47b",  // ← NOT "unknown"
  "version": "2.1.0",   // ← NOT "2.0.0"
  "time": "2025-10-02T...",
  "uptime": 45.67,
  "port": "8080",
  "ready": true
}
```

**✅ Success indicators**:
- `commit`: Shows actual SHA (first 7 chars)
- `version`: `2.1.0` or higher
- `status`: `ok`

**❌ If commit is "unknown"**:
- Railway env vars not injected
- Check Railway **Variables** tab
- Add: `COMMIT_SHA = ${{RAILWAY_GIT_COMMIT_SHA}}`
- See: `RAILWAY_DEPLOYMENT_CONFIG.md`

#### 2. Railway Startup Logs
Look for in deployment logs:
```
🚀 Server running on port 8080 (commit=f25e47b)
📝 Commit SHA: f25e47b
✅ QuantumLeap Trading Backend server running on port 8080
🌍 Environment: production
❤️ Health check: http://0.0.0.0:8080/health
```

**✅ Key indicators**:
- Port shows `8080` (or Railway's assigned port)
- Commit shows `f25e47b` (not "unknown")
- No module initialization errors

#### 3. AI Validation Endpoint Test
```bash
curl -X POST https://web-production-de0bc.up.railway.app/api/ai/validate-key \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"test_key"}'
```

**Expected (invalid key)**:
```json
{
  "valid": false,
  "provider": "openai",
  "message": "Invalid OpenAI API key"
}
```

**❌ If 404 "Route not found"**:
- Old code still deployed
- AI routes not registered
- Try "Clear Cache and Redeploy" again

#### 4. CORS Headers Test
```bash
curl -I -X OPTIONS https://web-production-de0bc.up.railway.app/api/ai/validate-key \
  -H "Origin: https://quantum-leap-frontend-production.up.railway.app" \
  -H "Access-Control-Request-Headers: X-Config-ID"
```

**Expected**:
```
Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With, X-Force-Delete, X-User-ID, X-Config-ID
```

**✅ Success**: `X-Config-ID` is in the allowed headers

---

## 👤 User Actions After Backend Deployment

### Step 1: Clear Browser Storage
```javascript
// In browser DevTools Console (F12):
localStorage.clear();
location.reload();
```

### Step 2: Reconnect to Zerodha
1. Go to **Broker Integration** page
2. Enter Zerodha API Key and Secret
3. Click **"Connect to Zerodha"**
4. Complete OAuth flow in popup

### Step 3: Verify Session Has user_id
```javascript
// In browser Console:
const session = JSON.parse(localStorage.getItem('activeBrokerSession'));
console.log(session);
```

**Expected**:
```javascript
{
  config_id: "afa33f54-...",
  user_id: "EBW183",      // ← NOT null
  session_status: "connected",
  broker_name: "zerodha",
  ...
}
```

**✅ Success**: `user_id` is populated (e.g., "EBW183")  
**❌ Failure**: `user_id` is `null` → Old OAuth code still running

### Step 4: Check OAuth Logs in Railway
Look for in backend logs (after user reconnects):
```
🔍 [OAuth] Fetching user profile from Zerodha API...
🔍 [OAuth] Zerodha profile response: { "data": { "user_id": "EBW183", ... } }
🔑 [OAuth] Using broker user_id from profile: EBW183
```

**❌ If missing**: Old code still deployed, redeploy didn't work

### Step 5: Test AI Configuration
1. Go to **AI Configuration** page
2. Enter an **OpenAI API key**
3. Click **"Test"** button
4. Should see:
   - ✅ "OpenAI API key is valid" (if key is valid)
   - ✅ "Invalid OpenAI API key" (if key is invalid)
   - ❌ NOT: "Validation request failed" or 404 error

---

## 🔧 Troubleshooting

### If Health Shows "unknown" Commit
1. Check Railway **Variables** tab
2. Look for `RAILWAY_GIT_COMMIT_SHA` (auto-injected)
3. If missing, manually add:
   - Name: `COMMIT_SHA`
   - Value: `${{RAILWAY_GIT_COMMIT_SHA}}`
4. Redeploy

### If user_id is Still null
1. Verify OAuth logs show profile fetch
2. If no profile fetch logs:
   - Old code is running
   - Try "Clear Cache and Redeploy"
   - Check deployment commit matches `f25e47b`

### If /api/ai/validate-key Returns 404
1. AI routes not loaded
2. Check logs for "AI module initialized"
3. If missing:
   - Module registration failed
   - Check for kiteconnect module errors
   - Verify `npm ci` completed successfully in build logs

### If CORS Still Blocks X-Config-ID
1. Check CORS response headers
2. Should include `X-Config-ID` in `Access-Control-Allow-Headers`
3. If not:
   - Old `server-modular.js` deployed
   - Force redeploy with cache clear

---

## 📋 Checklist

Use this after Railway deployment completes:

- [ ] `/health` returns `commit: "f25e47b"` (not "unknown")
- [ ] `/health` returns `version: "2.1.0"` (not "2.0.0")
- [ ] Railway logs show: `🚀 Server running on port X (commit=f25e47b)`
- [ ] `/api/ai/validate-key` returns 200 (not 404)
- [ ] CORS allows `X-Config-ID` header
- [ ] User cleared localStorage
- [ ] User reconnected to Zerodha
- [ ] Session has `user_id` populated (not null)
- [ ] OAuth logs show profile fetch
- [ ] AI Configuration validation works (no 404 or CORS errors)

---

## 🎯 Expected End State

**Backend (Railway)**:
- ✅ Deployed commit: `f25e47b`
- ✅ Version: `2.1.0`
- ✅ `/health` shows actual commit SHA
- ✅ `/api/ai/validate-key` endpoint exists (200 response)
- ✅ CORS allows `X-Config-ID`
- ✅ OAuth callback fetches user profile from Zerodha
- ✅ Logs show commit SHA in startup message

**Frontend (User Session)**:
- ✅ localStorage cleared and refreshed
- ✅ Reconnected to Zerodha
- ✅ Session object has `user_id` (e.g., "EBW183")
- ✅ AI Configuration page can validate keys
- ✅ No CORS errors
- ✅ No 404 errors

---

**Next Steps**: 
1. You manually redeploy on Railway
2. Notify me when deployment completes
3. I will run verification tests (Tasks 6-8)
4. Guide user through browser storage clear and reconnection

**Created**: October 2, 2025  
**Commit**: `f25e47b`  
**Railway Service**: QuntumTrade_Backend
