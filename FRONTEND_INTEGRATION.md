# Frontend Integration Guide

## Overview

Your FastAPI backend is now successfully deployed to Railway at:
**https://web-production-de0bc.up.railway.app**

This guide will help you integrate your existing frontend (Base44 platform) with the new backend API.

## Backend API Endpoints

Your deployed backend provides these endpoints:

### 1. Health Check
- **URL**: `GET https://web-production-de0bc.up.railway.app/health`
- **Purpose**: Verify API is running

### 2. Broker Authentication
- **URL**: `POST https://web-production-de0bc.up.railway.app/api/broker/generate-session`
- **Purpose**: Exchange Kite Connect request_token for access_token

### 3. OAuth Callback
- **URL**: `GET https://web-production-de0bc.up.railway.app/api/broker/callback`
- **Purpose**: Handle Kite Connect OAuth redirect

### 4. Portfolio Summary
- **URL**: `GET https://web-production-de0bc.up.railway.app/api/portfolio/summary?user_id={user_id}`
- **Purpose**: Get portfolio overview with P&L

### 5. Holdings Data
- **URL**: `GET https://web-production-de0bc.up.railway.app/api/portfolio/holdings?user_id={user_id}`
- **Purpose**: Get long-term equity holdings

### 6. Positions Data
- **URL**: `GET https://web-production-de0bc.up.railway.app/api/portfolio/positions?user_id={user_id}`
- **Purpose**: Get current day positions

## Frontend Integration Steps

### Step 1: Update API Base URL

In your frontend code, update the API base URL to point to the deployed backend:

```javascript
// Old (local development)
const API_BASE_URL = 'http://localhost:8000';

// New (production)
const API_BASE_URL = 'https://web-production-de0bc.up.railway.app';
```

### Step 2: Update Kite Connect OAuth Flow

#### Configure Kite Connect App Settings

1. Log into [Kite Connect Developer Console](https://developers.kite.trade/)
2. Go to your app settings
3. Update the **Redirect URL** to:
   ```
   https://web-production-de0bc.up.railway.app/api/broker/callback
   ```

#### Frontend OAuth Implementation

```javascript
// Function to initiate Kite Connect login
function initiateKiteLogin(apiKey, userId) {
    const kiteLoginUrl = `https://kite.trade/connect/login?api_key=${apiKey}&v=3`;
    
    // Store user_id in localStorage for callback handling
    localStorage.setItem('pending_user_id', userId);
    
    // Redirect to Kite Connect
    window.location.href = kiteLoginUrl;
}

// Handle callback from Kite Connect (in your callback page)
function handleKiteCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const requestToken = urlParams.get('request_token');
    const userId = localStorage.getItem('pending_user_id');
    
    if (requestToken && userId) {
        // Call your backend to exchange token
        exchangeTokenForSession(requestToken, userId);
    }
}

// Exchange request_token for access_token
async function exchangeTokenForSession(requestToken, userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/broker/generate-session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                request_token: requestToken,
                user_id: userId,
                api_key: 'YOUR_KITE_API_KEY',
                api_secret: 'YOUR_KITE_API_SECRET'
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // Store user session data
            localStorage.setItem('user_data', JSON.stringify(result.data));
            localStorage.removeItem('pending_user_id');
            
            // Redirect to dashboard
            window.location.href = '/dashboard';
        } else {
            console.error('Session generation failed:', result.message);
        }
    } catch (error) {
        console.error('Error exchanging token:', error);
    }
}
```

### Step 3: Update Portfolio Data Fetching

```javascript
// Get portfolio summary
async function getPortfolioSummary(userId) {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/portfolio/summary?user_id=${userId}`
        );
        const data = await response.json();
        
        if (data.status === 'success') {
            return data.data;
        } else {
            throw new Error(data.message || 'Failed to fetch portfolio summary');
        }
    } catch (error) {
        console.error('Error fetching portfolio summary:', error);
        throw error;
    }
}

// Get holdings data
async function getHoldings(userId) {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/portfolio/holdings?user_id=${userId}`
        );
        const data = await response.json();
        
        if (data.status === 'success') {
            return data.data;
        } else {
            throw new Error(data.message || 'Failed to fetch holdings');
        }
    } catch (error) {
        console.error('Error fetching holdings:', error);
        throw error;
    }
}

// Get positions data
async function getPositions(userId) {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/portfolio/positions?user_id=${userId}`
        );
        const data = await response.json();
        
        if (data.status === 'success') {
            return data.data;
        } else {
            throw new Error(data.message || 'Failed to fetch positions');
        }
    } catch (error) {
        console.error('Error fetching positions:', error);
        throw error;
    }
}
```

### Step 4: Error Handling

Implement proper error handling for API calls:

```javascript
// Centralized error handler
function handleApiError(error, context) {
    console.error(`Error in ${context}:`, error);
    
    if (error.message.includes('Unauthorized')) {
        // Redirect to login
        localStorage.clear();
        window.location.href = '/login';
    } else {
        // Show user-friendly error message
        showErrorMessage(`Failed to ${context}. Please try again.`);
    }
}

// Example usage
async function loadDashboardData(userId) {
    try {
        const [summary, holdings, positions] = await Promise.all([
            getPortfolioSummary(userId),
            getHoldings(userId),
            getPositions(userId)
        ]);
        
        // Update UI with data
        updateDashboard({ summary, holdings, positions });
        
    } catch (error) {
        handleApiError(error, 'load dashboard data');
    }
}
```

### Step 5: Environment Configuration

Create environment-specific configuration:

```javascript
// config.js
const config = {
    development: {
        API_BASE_URL: 'http://localhost:8000',
    },
    production: {
        API_BASE_URL: 'https://web-production-de0bc.up.railway.app',
    }
};

const environment = process.env.NODE_ENV || 'development';
export default config[environment];
```

## Testing the Integration

### 1. Test API Connectivity

```javascript
// Test if backend is accessible
async function testApiConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('API Status:', data);
        return data.status === 'healthy';
    } catch (error) {
        console.error('API connection failed:', error);
        return false;
    }
}
```

### 2. Test OAuth Flow

1. Update Kite Connect app redirect URL
2. Test the complete OAuth flow:
   - Initiate login → Kite Connect → Callback → Session generation
3. Verify user data is stored correctly

### 3. Test Data Fetching

1. Test portfolio summary endpoint
2. Test holdings endpoint  
3. Test positions endpoint
4. Verify error handling for invalid user_id

## Security Considerations

### 1. API Keys Storage

**❌ Don't do this:**
```javascript
// Never store API keys in frontend code
const API_KEY = 'your_api_key_here'; // Visible to users!
```

**✅ Do this instead:**
```javascript
// Store API keys securely on backend
// Frontend only sends user_id and request_token
```

### 2. User Session Management

```javascript
// Secure session handling
function isUserLoggedIn() {
    const userData = localStorage.getItem('user_data');
    return userData !== null;
}

function getUserId() {
    const userData = JSON.parse(localStorage.getItem('user_data') || '{}');
    return userData.user_id;
}

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}
```

### 3. CORS Configuration

The backend is currently configured with `allow_origins=["*"]` for development. For production, update this to your specific frontend domain.

## API Documentation

Full API documentation is available at:
**https://web-production-de0bc.up.railway.app/docs**

This interactive documentation allows you to:
- Test all endpoints
- See request/response schemas
- Understand error responses

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure frontend domain is allowed in backend CORS settings
2. **OAuth Redirect Fails**: Verify Kite Connect app redirect URL is correct
3. **Authentication Errors**: Check if user_id exists and has valid credentials
4. **Network Errors**: Verify Railway deployment is healthy

### Debug Steps

1. Check browser console for errors
2. Test API endpoints directly using the docs page
3. Verify network requests in browser dev tools
4. Check Railway deployment logs

## Next Steps

1. **Update your frontend code** with the integration changes above
2. **Test the OAuth flow** end-to-end
3. **Test all portfolio data fetching** functionality
4. **Deploy your updated frontend** to your hosting platform
5. **Monitor for any issues** and adjust as needed

## Support

- **Backend API Docs**: https://web-production-de0bc.up.railway.app/docs
- **Backend Health**: https://web-production-de0bc.up.railway.app/health
- **Railway Dashboard**: Monitor deployment health and logs

Your backend is ready for production use! 🚀 