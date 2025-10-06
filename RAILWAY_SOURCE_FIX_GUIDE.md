# Railway Backend Deployment Source Fix Guide

## Problem Statement

Railway "Clear Cache & Redeploy" completed successfully, but the backend still shows **old commit `5406796`** instead of the latest **`77debc8`**.

**Current Status:**
- ✅ GitHub main branch: `77debc8`
- ❌ Railway deployed: `5406796`
- ❌ Gap: 5 commits behind

## Root Cause

Railway is **deploying from a pinned/cached commit** instead of tracking the latest `main` branch.

When you clicked "Clear Cache & Redeploy", Railway:
- ✅ Cleared the build cache
- ❌ Redeployed the SAME old commit (`5406796`)
- ❌ Did NOT pull the latest commit from GitHub

This happens when Railway's deployment source is configured to deploy from a **specific commit hash** instead of tracking the **main branch**.

---

## Verification Steps

### Step 1: Check Railway Source Configuration

1. **Go to Railway Dashboard:**
   - URL: https://railway.app/project/925c1cba-ce50-4be3-b5f9-a6bcb7dac747/service/78051177-075d-4dac-ad68-a054f604f847
   - Click **"Settings"** tab (left sidebar)
   - Scroll to **"Source"** section

2. **Check the current configuration:**

   **✅ EXPECTED (Good):**
   ```
   Repository: JagPat/quantumleap-trading-backend
   Branch: main
   Root Directory: / (or blank)
   Deploy from: Latest commit on main
   ```

   **❌ PROBLEMATIC (Bad):**
   ```
   Repository: JagPat/quantumleap-trading-backend
   Commit: 5406796abc123... (specific hash)
   Deploy from: Specific commit
   ```

3. **Also check:**
   - Go to **"Deployments"** tab
   - Click on the most recent deployment
   - Look at the logs for: `Checking out commit: <hash>`
   - If it shows `5406796`, Railway is pinned to old commit

---

## Fix Options

### Option A: Reconnect to GitHub Branch (Recommended)

This ensures Railway tracks the `main` branch and auto-deploys future commits.

1. **In Settings → Source section:**
   - Click **"Edit"** button (if available)
   - OR Click **"Disconnect"** to remove current source

2. **Reconnect to GitHub:**
   - Click **"Connect to GitHub"** button
   - Authenticate with GitHub (if prompted)
   - Select repository: `JagPat/quantumleap-trading-backend`
   - Select branch: **`main`**
   - Root directory: Leave blank or set to `/`
   - Click **"Connect"**

3. **Result:**
   - Railway will automatically trigger a new deployment
   - It will pull the latest commit from `main` (`77debc8`)
   - Future pushes to `main` will auto-deploy

---

### Option B: Trigger New Deployment from Branch

If you don't want to reconnect, you can trigger a new deployment:

1. **Go to "Deployments" tab**

2. **Click "New Deployment" or "Deploy" button**

3. **In the deployment dialog:**
   - Source: Ensure it says **`main`** branch (NOT a commit hash)
   - If it shows a commit hash, change it to `main`
   - Click **"Deploy"**

4. **Wait for deployment** (2-3 minutes)

---

### Option C: Use Railway CLI (Advanced)

If the UI options don't work, use the Railway CLI:

```bash
# Navigate to backend directory
cd /Users/jagrutpatel/Kiro_Project/quantum-leap-frontend/backend-temp

# Install Railway CLI (if not installed)
curl -fsSL https://railway.app/install.sh | sh

# Add to PATH
export PATH="$HOME/.railway/bin:$PATH"

# Login to Railway
railway login

# Link to the correct project and service
railway link 925c1cba-ce50-4be3-b5f9-a6bcb7dac747

# Deploy latest commit from current directory
railway up --service web
```

**Note:** You may need to select the correct environment when linking.

---

## Enable Auto-Deploy (Highly Recommended)

To prevent this issue in the future:

1. **Go to Settings → "Deploy Triggers"**

2. **Enable Auto-Deploy:**
   - Toggle **ON**: "Auto-deploy from GitHub"
   - Branch: Ensure it's set to `main`
   - Save changes

3. **Result:**
   - Every push to GitHub `main` will automatically trigger Railway deployment
   - No more manual "Redeploy" needed for code updates
   - Only configuration/environment variable changes need manual redeploy

---

## Verification After Fix

After applying the fix and waiting for deployment (2-3 minutes):

### Test 1: Check /health Endpoint

```bash
curl https://web-production-de0bc.up.railway.app/health | jq '.'
```

**Expected Response:**
```json
{
  "status": "ok",
  "commit": "77debc8",  // ← Should show LATEST commit
  "time": "2025-10-03T...",
  "uptime": 45.23,  // ← Should be LOW (< 60 seconds)
  "port": "8080",
  "version": "2.1.0",
  "ready": true
}
```

**✅ Success Indicators:**
- `commit` shows `77debc8` (latest)
- `uptime` is less than 60 seconds (fresh restart)
- `status` is `ok`
- `ready` is `true`

**❌ Still Not Fixed:**
- `commit` still shows `5406796`
- `uptime` is very high (no restart happened)
- → Railway didn't pull latest code, try another fix option

### Test 2: Check Railway Deployment Logs

1. Go to Railway → Deployments tab
2. Click on the most recent deployment
3. Look for these log entries:

**✅ Expected Logs:**
```
🚀 Starting build...
📦 Cloning repository: JagPat/quantumleap-trading-backend
🔍 Checking out commit: 77debc8...
📦 Installing dependencies...
✅ Build completed
🚀 Starting service...
✅ Service ready on port 8080
```

**❌ Problematic Logs:**
```
🔍 Checking out commit: 5406796...  // ← Still old commit!
```

---

## Commit History Reference

```
77debc8  ← LATEST (should deploy this)
  ↓
4d4a369  
  ↓
7d70325  
  ↓
ff9957c  
  ↓
7e56e83  
  ↓
5406796  ← CURRENTLY DEPLOYED (5 commits behind!)
```

**Gap:** Railway is 5 commits behind GitHub.

**What's in the missing commits:**
- `7e56e83`: Deployment status documentation
- `ff9957c`: Force redeploy trigger
- `7d70325`: Updated deployment verification guide
- `4d4a369`: Force Railway redeploy
- `77debc8`: **Fixed workflow (removed npm build step)**

---

## Quick Diagnosis Checklist

Use this checklist to verify the fix:

- [ ] Railway Settings → Source shows `main` branch (not commit hash)
- [ ] Railway Settings → Deploy Triggers → Auto-deploy is ENABLED
- [ ] Railway Settings → Source → Repository is `JagPat/quantumleap-trading-backend`
- [ ] GitHub repo shows latest commit: `77debc8`
- [ ] Railway deployment logs show it's pulling from GitHub
- [ ] `/health` endpoint returns `commit: "77debc8"`
- [ ] `/health` endpoint shows `uptime < 60` seconds
- [ ] Railway dashboard shows deployment is "Active"

---

## Troubleshooting

### Issue: Railway still deploys old commit after reconnecting

**Possible causes:**
1. Railway GitHub integration is broken
2. Railway doesn't have permission to access the repository
3. Repository is private and Railway's GitHub App needs re-authorization

**Fix:**
1. Go to GitHub → Settings → Applications → Railway
2. Verify Railway has access to `quantumleap-trading-backend` repo
3. If not, grant access
4. In Railway, disconnect and reconnect the source

### Issue: Auto-deploy is enabled but doesn't trigger on push

**Possible causes:**
1. GitHub webhook is not configured
2. Railway GitHub App doesn't have webhook permissions
3. Webhook is configured but failing

**Fix:**
1. Go to GitHub repo → Settings → Webhooks
2. Look for Railway webhook (e.g., `https://...railway.app/webhooks/...`)
3. Check recent deliveries for failures
4. If webhook is missing, reconnect Railway to GitHub
5. Railway should auto-create the webhook

### Issue: Deployment succeeds but /health still shows old commit

**Possible causes:**
1. Environment variable `COMMIT_SHA` is not set
2. Railway is not injecting `RAILWAY_GIT_COMMIT_SHA`
3. Server caching old commit value

**Fix:**
1. Check Railway → Settings → Variables
2. Add variable: `COMMIT_SHA` = `${{ RAILWAY_GIT_COMMIT_SHA }}`
3. OR update `server-modular.js` to use `RAILWAY_GIT_COMMIT_SHA`
4. Redeploy

---

## Prevention: Best Practices

To avoid this issue in the future:

1. **✅ Always use Branch-based Deployment**
   - Deploy from `main` branch, not commit hashes
   - Avoids "pinned commit" issues

2. **✅ Enable Auto-Deploy**
   - Ensures Railway tracks GitHub automatically
   - Reduces manual intervention

3. **✅ Use GitHub Actions as Backup**
   - Even if Railway auto-deploy fails, GitHub Actions can deploy via Railway CLI
   - Already configured in `.github/workflows/deploy-backend.yml`

4. **✅ Monitor Deployment Status**
   - Check `/health` endpoint after each push
   - Verify commit SHA matches GitHub

5. **✅ Use Deployment Webhooks**
   - Set up Slack/Discord notifications for Railway deployments
   - Get alerted when deployments fail or succeed

---

## Summary

**The Problem:**
- Railway is pinned to old commit `5406796` instead of latest `77debc8`
- "Clear Cache & Redeploy" redeployed the same old commit
- Railway is not tracking the `main` branch

**The Solution:**
1. Check Railway Settings → Source configuration
2. If it shows a commit hash, reconnect to `main` branch
3. Enable Auto-Deploy to track future commits
4. Verify `/health` shows latest commit `77debc8`

**Next Steps:**
1. Go to Railway dashboard
2. Check Source configuration
3. Reconnect to `main` branch if needed
4. Trigger new deployment
5. Verify with `/health` endpoint
6. Enable auto-deploy for future
7. Report back with results!

---

**Need Help?**
If none of the above solutions work, share:
- Screenshot of Railway Settings → Source section
- Screenshot of recent deployment logs
- Output of `/health` endpoint

This will help diagnose any additional issues.

---

**Last Updated:** 2025-10-03  
**Issue Ticket:** Railway Backend Stuck on Old Commit  
**Status:** Awaiting user action to fix Railway source configuration


