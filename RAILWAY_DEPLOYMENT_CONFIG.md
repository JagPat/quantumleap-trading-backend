# Railway Deployment Configuration

## Required Environment Variables for Commit SHA Tracking

To ensure the `/health` endpoint returns the actual commit SHA (instead of "unknown"), Railway must inject the commit SHA as an environment variable during build/deploy.

### Option 1: Using Railway's Built-in Variable (Recommended)
Railway automatically provides `RAILWAY_GIT_COMMIT_SHA` - our code already checks for this.

**No action needed** - this should work automatically.

### Option 2: Manual Environment Variable
If Railway's auto-variable doesn't work, set manually:

1. Go to Railway Dashboard → Your Backend Service
2. Navigate to **Variables** tab
3. Add new variable:
   - **Name**: `COMMIT_SHA`
   - **Value**: `${{RAILWAY_GIT_COMMIT_SHA}}`

### Option 3: GitHub Actions Integration
If deploying via GitHub Actions:
- Set `COMMIT_SHA=${{ github.sha }}`

## Verification
After deployment, check:
```bash
curl https://web-production-de0bc.up.railway.app/health
```

Expected response:
```json
{
  "status": "ok",
  "commit": "1c189b7",  // ← Should show actual commit, not "unknown"
  "time": "2025-10-02T...",
  "uptime": 123.45,
  "port": "8080",
  "version": "2.1.0",
  "ready": true
}
```

## Server Startup Logs
Look for in Railway logs:
```
🚀 Server running on port 8080 (commit=1c189b7)
📝 Commit SHA: 1c189b7
```

If you see `(commit=unknown)`, the environment variable is not being injected.

## Troubleshooting
1. Check Railway's Variables tab for `RAILWAY_GIT_COMMIT_SHA`
2. Verify Railway has GitHub access to read commit info
3. Try manual redeploy with "Clear cache" option
4. If all else fails, hardcode in Dockerfile: `ENV COMMIT_SHA=<latest-sha>`
