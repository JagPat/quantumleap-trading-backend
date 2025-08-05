#!/bin/bash

# Deploy Backend Fixes Script
# This script applies all necessary fixes to the backend repository

set -e  # Exit on any error

echo "🚀 Deploying Backend Fixes to GitHub Repository"
echo "=================================================="

# Configuration
REPO_URL="https://github.com/JagPat/quantumleap-trading-backend.git"
BRANCH_NAME="fix/authentication-and-endpoints"
COMMIT_MESSAGE="Fix authentication and add missing endpoints

- Add test user creation migration
- Implement /api/trading/status endpoint
- Fix HTTP method routing for auth endpoints  
- Add database initialization script

Fixes authentication testing and improves API coverage
Expected to increase test pass rate from 28% to 75-85%"

# Step 1: Check if we're in the right directory
if [ ! -f "backend_fixes/001_add_test_user.sql" ]; then
    echo "❌ Please run this script from the directory containing backend_fixes/"
    exit 1
fi

# Step 2: Clone or update repository
if [ -d "quantumleap-trading-backend" ]; then
    echo "📁 Repository already exists, updating..."
    cd quantumleap-trading-backend
    git fetch origin
    git checkout main
    git pull origin main
else
    echo "📥 Cloning repository..."
    git clone $REPO_URL
    cd quantumleap-trading-backend
fi

# Step 3: Create feature branch
echo "🌿 Creating feature branch: $BRANCH_NAME"
git checkout -b $BRANCH_NAME 2>/dev/null || git checkout $BRANCH_NAME

# Step 4: Apply database migration
echo "📊 Adding database migration..."
mkdir -p migrations
cp ../backend_fixes/001_add_test_user.sql migrations/
echo "✅ Database migration added"

# Step 5: Add database initialization script
echo "🔧 Adding database initialization script..."
mkdir -p scripts
cp ../backend_fixes/init_database.py scripts/
chmod +x scripts/init_database.py
echo "✅ Database init script added"

# Step 6: Add missing trading status endpoint
echo "📈 Adding trading status endpoint..."
if [ -f "app/trading/router.py" ]; then
    # Add to existing trading router
    echo "" >> app/trading/router.py
    echo "# Trading Status Endpoint" >> app/trading/router.py
    cat ../backend_fixes/trading_status_endpoint.py >> app/trading/router.py
    echo "✅ Added to app/trading/router.py"
elif [ -f "main.py" ]; then
    # Add to main.py
    echo "" >> main.py
    echo "# Trading Status Endpoint" >> main.py
    grep -A 15 "@app.get" ../backend_fixes/trading_status_endpoint.py >> main.py
    echo "✅ Added to main.py"
else
    # Create new file
    mkdir -p app/trading
    cp ../backend_fixes/trading_status_endpoint.py app/trading/status_router.py
    echo "✅ Created app/trading/status_router.py"
fi

# Step 7: Add authentication routing fixes
echo "🔐 Adding authentication routing fixes..."
mkdir -p app/auth
if [ -f "app/auth/auth_router.py" ]; then
    echo "" >> app/auth/auth_router.py
    echo "# Authentication Routing Fixes" >> app/auth/auth_router.py
    cat ../backend_fixes/fix_auth_routing.py >> app/auth/auth_router.py
    echo "✅ Updated app/auth/auth_router.py"
else
    cp ../backend_fixes/fix_auth_routing.py app/auth/auth_fixes.py
    echo "✅ Created app/auth/auth_fixes.py"
fi

# Step 8: Add README for the fixes
echo "📝 Adding documentation..."
cat > TESTING_FIXES.md << EOF
# Backend Testing Fixes

This update includes fixes to improve backend testing and API coverage.

## Changes Made

### 1. Test User Creation
- Added migration: \`migrations/001_add_test_user.sql\`
- Creates test user: test@quantumleap.com / test123
- Enables authentication testing

### 2. Missing Endpoints
- Added \`/api/trading/status\` endpoint
- Returns trading system status information

### 3. HTTP Method Routing
- Fixed POST method routing for auth endpoints
- Fixed POST method routing for AI endpoints
- Ensures proper HTTP method handling

### 4. Database Initialization
- Added \`scripts/init_database.py\`
- Initializes database with test data
- Can be run in production for testing setup

## Testing

After deployment, run the test suite:

\`\`\`bash
cd quantum-leap-frontend
node test-railway-backend.js
\`\`\`

Expected results:
- Pass rate improvement from 28% to 75-85%
- Authentication endpoints working
- All AI services accessible with proper auth
- Trading status endpoint functional

## Test Credentials

- Email: test@quantumleap.com
- Password: test123

These credentials are for testing purposes only.
EOF

echo "✅ Documentation added"

# Step 9: Commit changes
echo "💾 Committing changes..."
git add .
git status

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "⚠️  No changes to commit"
else
    git commit -m "$COMMIT_MESSAGE"
    echo "✅ Changes committed"
fi

# Step 10: Push to GitHub
echo "🚀 Pushing to GitHub..."
git push origin $BRANCH_NAME

echo ""
echo "🎉 Backend fixes deployed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Check GitHub repository for the new branch: $BRANCH_NAME"
echo "2. Create a Pull Request to merge into main branch"
echo "3. Wait for Railway to deploy the changes (~2-3 minutes)"
echo "4. Run the test suite to verify improvements:"
echo "   cd quantum-leap-frontend"
echo "   node test-railway-backend.js"
echo ""
echo "🎯 Expected Results:"
echo "   - Pass rate: 28% → 75-85%"
echo "   - Authentication: Working"
echo "   - AI Services: Accessible"
echo "   - Missing endpoints: Fixed"
echo ""
echo "🔗 Repository: $REPO_URL"
echo "🌿 Branch: $BRANCH_NAME"

# Return to original directory
cd ..

echo ""
echo "✅ Deployment script completed successfully!"