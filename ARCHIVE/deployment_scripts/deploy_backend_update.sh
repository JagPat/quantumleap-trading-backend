#!/bin/bash
# Backend Deployment Update Script
# This script commits changes and triggers Railway deployment

echo "🚀 Starting Backend Deployment Update..."

# Check for changes
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Committing changes..."
    git add .
    git commit -m "Update automated trading engine - $(date)"
    
    echo "📤 Pushing to repository..."
    git push origin main
    
    echo "✅ Changes pushed to repository"
    echo "🚂 Railway will automatically deploy the changes"
    echo "⏳ Please wait 2-3 minutes for deployment to complete"
else
    echo "ℹ️ No changes to commit"
fi

echo "🔗 Railway App URL: https://quantum-leap-backend-production.up.railway.app"
echo "📊 Check deployment status at: https://railway.app"
