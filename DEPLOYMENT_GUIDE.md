# 🚀 QuantumLeap Trading Backend - Railway Deployment Guide

This guide will walk you through deploying your FastAPI backend to Railway.app step by step.

## Prerequisites

- A GitHub account
- A Railway.app account (free tier available)
- Git installed on your computer
- The backend code ready for deployment

## Step 1: Create a New GitHub Repository

### 1.1 Create Repository on GitHub

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **"+"** button in the top right corner
3. Select **"New repository"**
4. Fill in the details:
   - **Repository name**: `quantumleap-trading-backend`
   - **Description**: `FastAPI backend for QuantumLeap Trading application`
   - **Visibility**: Choose "Public" or "Private" (both work with Railway)
   - **DO NOT** initialize with README, .gitignore, or license (we have our own)
5. Click **"Create repository"**

### 1.2 Push Your Code to GitHub

Open your terminal/command prompt and navigate to your project directory:

```bash
# Navigate to your project directory
cd /path/to/your/quantum-leap-trading-project

# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Commit the files
git commit -m "Initial commit: FastAPI backend for QuantumLeap Trading"

# Add your GitHub repository as remote origin
git remote add origin https://github.com/YOUR_USERNAME/quantumleap-trading-backend.git

# Push to GitHub
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 2: Create Railway Project

### 2.1 Sign Up for Railway

1. Go to [Railway.app](https://railway.app)
2. Click **"Sign Up"**
3. Sign up with your GitHub account (recommended)
4. Verify your email if required

### 2.2 Create New Project

1. Once logged in, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository: `quantumleap-trading-backend`
4. Railway will automatically detect it's a Python project

## Step 3: Configure Environment Variables

### 3.1 Generate Encryption Key

First, generate a secure encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output (it will look like: `gAAAAABh...`)

### 3.2 Set Environment Variables in Railway

1. In your Railway project dashboard, click on your service
2. Go to the **"Variables"** tab
3. Add the following environment variables:

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `ENCRYPTION_KEY` | `[Your generated key]` | The encryption key you generated above |
| `HOST` | `0.0.0.0` | Server host (Railway default) |
| `PORT` | `8000` | Server port (Railway will override this) |
| `DEBUG` | `false` | Set to false for production |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ALLOWED_ORIGINS` | `*` | CORS origins (configure properly for production) |
| `DATABASE_PATH` | `trading_app.db` | SQLite database file name |

### 3.3 Click "Deploy" Button

Railway will automatically deploy your application when you add the environment variables.

## Step 4: Monitor Deployment

### 4.1 Check Build Logs

1. In Railway dashboard, go to **"Deployments"** tab
2. Click on the latest deployment
3. Monitor the build logs to ensure everything installs correctly

### 4.2 Check Runtime Logs

1. Go to **"Logs"** tab
2. Look for messages like:
   ```
   Starting QuantumLeap Trading Backend API...
   Server will run on: http://0.0.0.0:8000
   Railway deployment: True
   ```

## Step 5: Get Your Public URL

### 5.1 Find Your App URL

1. In Railway dashboard, go to **"Settings"** tab
2. Scroll down to **"Domains"** section
3. You'll see a URL like: `https://your-app-name.railway.app`
4. Click **"Generate Domain"** if no domain is shown

### 5.2 Test Your API

Visit your public URL and test these endpoints:

- **Health Check**: `https://your-app-name.railway.app/health`
- **API Docs**: `https://your-app-name.railway.app/docs`
- **Root**: `https://your-app-name.railway.app/`

## Step 6: Update Frontend Configuration

Update your frontend (Base44) to use the new public URL:

```javascript
// Replace localhost with your Railway URL
const API_BASE_URL = 'https://your-app-name.railway.app';
```

## Troubleshooting

### Common Issues

1. **Build Fails**: Check the build logs for missing dependencies
2. **App Won't Start**: Verify environment variables are set correctly
3. **Database Errors**: Ensure `ENCRYPTION_KEY` is properly set
4. **CORS Errors**: Update `ALLOWED_ORIGINS` with your frontend URL

### Useful Commands

```bash
# Check Railway CLI logs
railway logs

# Redeploy
railway up

# Check environment variables
railway variables
```

## Production Considerations

### Security

1. **Update CORS**: Set `ALLOWED_ORIGINS` to your specific frontend domain
2. **Environment Variables**: Never commit `.env` files to GitHub
3. **Database**: Consider upgrading to PostgreSQL for production

### Monitoring

1. **Railway Metrics**: Monitor CPU, memory, and request metrics
2. **Logs**: Set up log aggregation for production
3. **Health Checks**: Railway automatically monitors `/health` endpoint

### Scaling

1. **Railway Pro**: Upgrade for more resources and features
2. **Database**: Consider external database for high traffic
3. **CDN**: Add CDN for static assets if needed

## Support

If you encounter issues:

1. Check Railway documentation: [docs.railway.app](https://docs.railway.app)
2. Check the deployment logs in Railway dashboard
3. Verify all environment variables are set correctly
4. Test the API endpoints using the interactive docs

## Next Steps

1. **Test all endpoints** with your Kite Connect credentials
2. **Update your frontend** to use the new public API URL
3. **Monitor the deployment** for any issues
4. **Consider upgrading** to Railway Pro for production use

Your FastAPI backend is now deployed and accessible via a public URL! 🎉 