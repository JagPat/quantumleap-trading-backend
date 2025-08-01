# Railway Database Setup Guide

## Overview

Based on the Railway environment variables screenshot, you have most variables configured but are missing some critical ones. This guide will help you set up the missing environment variables to get your Quantum Leap Trading Backend fully operational.

## Current Status Analysis

### ✅ Variables Already Set (from screenshot):
- `API_KEY` - ✅ Configured
- `API_RATE_LIMIT` - ✅ Configured  
- `API_SECRET` - ✅ Configured
- `BACKUP_INTERVAL` - ✅ Configured
- `CORS_ORIGINS` - ✅ Configured
- `DATABASE_URI` - ✅ Configured
- `ENCRYPTION_KEY` - ✅ Configured
- `ENVIRONMENT` - ✅ Configured
- `FRONTEND_URL` - ✅ Configured
- `HEALTH_CHECK_TIMEOUT` - ✅ Configured
- `LOG_LEVEL` - ✅ Configured
- `MAX_CONCURRENT_STRATEGIES` - ✅ Configured
- `MAX_ORDERS_PER_MINUTE` - ✅ Configured
- `MONITORING_INTERVAL` - ✅ Configured
- `REDIS_URL` - ✅ Configured
- `SESSION_SECRET` - ✅ Configured

### ❌ Missing Critical Variables:

## Required Environment Variables to Add

### 1. DATABASE_URL (Critical - Missing)
**Variable Name:** `DATABASE_URL`
**Value:** Use the same value as your `DATABASE_URI` 
**Description:** Primary database connection URL (our app expects DATABASE_URL but you have DATABASE_URI)

**Action:** Add a new variable `DATABASE_URL` with the same value as `DATABASE_URI`

### 2. AI API Keys (Optional but Recommended)
**Variable Name:** `OPENAI_API_KEY`
**Value:** Your OpenAI API key (starts with sk-)
**Description:** For AI-powered portfolio analysis

**Variable Name:** `ANTHROPIC_API_KEY`  
**Value:** Your Anthropic API key
**Description:** For Claude AI integration

**Variable Name:** `GOOGLE_API_KEY`
**Value:** Your Google AI API key
**Description:** For Gemini AI integration

### 3. Kite Connect API (For Live Trading)
**Variable Name:** `KITE_API_KEY`
**Value:** Your Kite Connect API key
**Description:** For live trading with Zerodha Kite

**Variable Name:** `KITE_API_SECRET`
**Value:** Your Kite Connect API secret
**Description:** For Kite Connect authentication

**Variable Name:** `KITE_REDIRECT_URL`
**Value:** `https://web-production-de0bc.up.railway.app/api/auth/callback`
**Description:** OAuth callback URL for Kite Connect

### 4. Additional Recommended Variables
**Variable Name:** `PORT`
**Value:** `8000`
**Description:** Application port (Railway usually sets this automatically)

**Variable Name:** `HOST`
**Value:** `0.0.0.0`
**Description:** Application host binding

## Step-by-Step Setup Instructions

### Step 1: Add DATABASE_URL (Most Important)
1. In Railway dashboard, click "New Variable" button
2. Set Variable Name: `DATABASE_URL`
3. Set Value: Copy the exact same value from your existing `DATABASE_URI` variable
4. Click "Add"

### Step 2: Add AI API Keys (Optional)
If you want AI features to work:

1. **OpenAI API Key:**
   - Go to https://platform.openai.com/api-keys
   - Create a new API key
   - Add variable `OPENAI_API_KEY` with your key

2. **Anthropic API Key:**
   - Go to https://console.anthropic.com/
   - Create API key
   - Add variable `ANTHROPIC_API_KEY` with your key

3. **Google AI API Key:**
   - Go to https://makersuite.google.com/app/apikey
   - Create API key
   - Add variable `GOOGLE_API_KEY` with your key

### Step 3: Add Kite Connect (For Live Trading)
If you want live trading capabilities:

1. **Get Kite Connect API:**
   - Go to https://kite.trade/
   - Sign up for Kite Connect API
   - Get your API key and secret

2. **Add Variables:**
   - `KITE_API_KEY`: Your Kite API key
   - `KITE_API_SECRET`: Your Kite API secret  
   - `KITE_REDIRECT_URL`: `https://web-production-de0bc.up.railway.app/api/auth/callback`

### Step 4: Verify Configuration
After adding variables, your Railway should automatically redeploy. You can verify by:

1. Check deployment logs for any errors
2. Test the health endpoint: `https://web-production-de0bc.up.railway.app/health`
3. Test trading engine: `https://web-production-de0bc.up.railway.app/api/trading-engine/health`

## Minimal Setup (Just to Get Running)

If you want to get the system running quickly with minimal setup, just add:

1. **DATABASE_URL** (copy value from DATABASE_URI) - **REQUIRED**
2. **OPENAI_API_KEY** (optional, but recommended for AI features)

## Database Configuration Details

### Current Database Setup
Based on your variables, you're using:
- **DATABASE_URI**: Already configured ✅
- **REDIS_URL**: Already configured ✅

### What's Missing
The application code looks for `DATABASE_URL` but you have `DATABASE_URI`. Both should point to the same database.

### Database Types Supported
- **PostgreSQL** (Recommended for production): `postgresql://user:password@host:port/database`
- **SQLite** (Development): `sqlite:///./quantum_leap.db`
- **MySQL**: `mysql://user:password@host:port/database`

## Security Best Practices

### Environment Variables Security
- ✅ All sensitive values are hidden (showing as *****)
- ✅ Using proper encryption key
- ✅ Session secret configured
- ✅ CORS origins properly set

### Additional Security Recommendations
1. **Rotate API Keys Regularly**: Change API keys every 90 days
2. **Monitor Usage**: Check API usage for unusual patterns
3. **Backup Database**: Ensure regular database backups
4. **SSL/TLS**: Railway provides HTTPS automatically

## Troubleshooting Common Issues

### Issue 1: Application Won't Start
**Symptom:** Deployment fails with database connection error
**Solution:** Ensure `DATABASE_URL` is set (not just `DATABASE_URI`)

### Issue 2: AI Features Not Working  
**Symptom:** AI analysis returns errors
**Solution:** Add `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY`

### Issue 3: Trading Features Not Working
**Symptom:** Cannot place orders or connect to broker
**Solution:** Add Kite Connect API credentials

### Issue 4: CORS Errors
**Symptom:** Frontend cannot connect to backend
**Solution:** Verify `FRONTEND_URL` and `CORS_ORIGINS` are correct

## Testing Your Setup

### 1. Basic Health Check
```bash
curl https://web-production-de0bc.up.railway.app/health
```
Should return: `{"status":"ok",...}`

### 2. Trading Engine Health
```bash
curl https://web-production-de0bc.up.railway.app/api/trading-engine/health
```
Should return: `{"status":"operational",...}`

### 3. Operational Procedures (New Feature)
```bash
curl https://web-production-de0bc.up.railway.app/api/trading-engine/operational/health
```
Should return: `{"status":"operational",...}`

## Next Steps After Setup

1. **Deploy and Test**: Railway will auto-deploy after adding variables
2. **Monitor Logs**: Check Railway logs for any startup errors
3. **Test Endpoints**: Use the curl commands above to verify functionality
4. **Frontend Integration**: Ensure frontend can connect to backend
5. **Live Trading Setup**: Configure Kite Connect for live trading (optional)

## Support and Resources

### Railway Documentation
- [Environment Variables](https://docs.railway.app/develop/variables)
- [Database Setup](https://docs.railway.app/databases/postgresql)

### API Documentation
- [OpenAI API](https://platform.openai.com/docs)
- [Anthropic API](https://docs.anthropic.com/)
- [Kite Connect API](https://kite.trade/docs/connect/v3/)

### Contact Support
If you encounter issues:
1. Check Railway deployment logs
2. Verify all environment variables are set correctly
3. Test individual endpoints to isolate issues
4. Check database connectivity

---

## Quick Action Checklist

- [ ] Add `DATABASE_URL` variable (copy from `DATABASE_URI`)
- [ ] Add `OPENAI_API_KEY` (optional, for AI features)
- [ ] Add `KITE_API_KEY` and `KITE_API_SECRET` (optional, for live trading)
- [ ] Add `KITE_REDIRECT_URL` (if using Kite Connect)
- [ ] Wait for Railway to redeploy
- [ ] Test health endpoints
- [ ] Verify operational procedures endpoints
- [ ] Test frontend connectivity

**Most Important:** Add the `DATABASE_URL` variable first - this is likely why your deployment is failing!