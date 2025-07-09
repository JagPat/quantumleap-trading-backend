# VibeOps MCP Integration Guide for QuantumLeap Trading

## Overview

VibeOps MCP provides a complete deployment and management infrastructure for your QuantumLeap Trading project, including:

- **GitLab Repository**: Source control with CI/CD
- **Vercel Deployment**: Modern frontend hosting with auto-deployment
- **Supabase Database**: PostgreSQL with authentication and real-time features
- **AI-Powered Tools**: Image generation and content creation

## Current Infrastructure Setup

### 🔗 GitLab Repository
- **Project ID**: `71476476`
- **URL**: `https://gitlab.com/vibeops.infra-group/65446e3c-7ca1-4b52-af9e-a0e32eb79a56.15a5ee30-2bc5-4080-b83d-c6c26b9a8ae5`
- **Access Token**: `glpat-VZpKjKsMGmgdMsgY3f45`

### ☁️ Vercel Project
- **Project ID**: `prj_Bew3A3R7zsTUnpz6my5dRZlMhL5i`
- **Framework**: Next.js (auto-detected)
- **Auto-deployment**: Enabled from GitLab main branch

### 🗄️ Supabase Database
- **Project ID**: `vmyvivlqsklrdlmtlkvf`
- **URL**: `https://vmyvivlqsklrdlmtlkvf.supabase.co`
- **Region**: EU West 3
- **Database Password**: `b70050f880ab483c93e2be406570563b`

## Environment Variables (Already Configured)

The following environment variables have been automatically configured in your Vercel project:

```env
# Backend API Connection
BACKEND_API_URL=https://web-production-de0bc.up.railway.app
NEXT_PUBLIC_API_URL=https://web-production-de0bc.up.railway.app/api

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://vmyvivlqsklrdlmtlkvf.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZteXZpdmxxc2tscmRsbXRsa3ZmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIwMjc3ODIsImV4cCI6MjA2NzYwMzc4Mn0.oNHdka8l8Ezuybx3MquCCZ2j4wj4XlimI2YtWm_Ye20
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZteXZpdmxxc2tscmRsbXRsa3ZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MjAyNzc4MiwiZXhwIjoyMDY3NjAzNzgyfQ.di1aKrtCtZqMQZP9roTDV1So8ND6Ic4GGt2Pmn4cIwk
```

## Integration Options

### Option 1: Modern Frontend Replacement

Since you removed the local frontend, create a new Next.js application:

#### Step 1: Set up GitLab Remote
```bash
# Add VibeOps GitLab as remote
git remote add vibeops https://vibe:glpat-VZpKjKsMGmgdMsgY3f45@gitlab.com/vibeops.infra-group/65446e3c-7ca1-4b52-af9e-a0e32eb79a56.15a5ee30-2bc5-4080-b83d-c6c26b9a8ae5.git

# Push your current backend to VibeOps
git push vibeops main
```

#### Step 2: Create Frontend Directory Structure
```bash
mkdir -p frontend-nextjs
cd frontend-nextjs

# Initialize Next.js project
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

#### Step 3: Install Required Dependencies
```bash
npm install @supabase/supabase-js axios @tanstack/react-query
npm install -D @types/node
```

#### Step 4: Create API Client
```typescript
// frontend-nextjs/src/lib/api.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Trading API functions
export const tradingApi = {
  // Broker Authentication
  generateSession: (data: { api_key: string; api_secret: string; request_token: string }) =>
    apiClient.post('/auth/broker/generate-session', data),
  
  getBrokerStatus: (userId: string) =>
    apiClient.get(`/auth/broker/status?user_id=${userId}`),
  
  disconnectBroker: (userId: string) =>
    apiClient.post(`/auth/broker/disconnect?user_id=${userId}`),

  // Portfolio Data
  getPortfolioSummary: (userId: string) =>
    apiClient.get(`/portfolio/summary?user_id=${userId}`),
  
  getHoldings: (userId: string) =>
    apiClient.get(`/portfolio/holdings?user_id=${userId}`),
  
  getPositions: (userId: string) =>
    apiClient.get(`/portfolio/positions?user_id=${userId}`),
};
```

#### Step 5: Create Supabase Client
```typescript
// frontend-nextjs/src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// User profile management
export const userProfileApi = {
  createProfile: async (userId: string, profileData: any) => {
    const { data, error } = await supabase
      .from('user_profiles')
      .insert({ user_id: userId, ...profileData });
    return { data, error };
  },

  getProfile: async (userId: string) => {
    const { data, error } = await supabase
      .from('user_profiles')
      .select('*')
      .eq('user_id', userId)
      .single();
    return { data, error };
  },

  updateProfile: async (userId: string, updates: any) => {
    const { data, error } = await supabase
      .from('user_profiles')
      .update(updates)
      .eq('user_id', userId);
    return { data, error };
  },
};
```

### Option 2: Enhanced Backend Integration

Add Supabase to your existing Railway backend for additional features:

#### Install Supabase in Backend
```bash
pip install supabase-py
```

#### Create Supabase Service
```python
# app/supabase/service.py
from supabase import create_client, Client
import os

class SupabaseService:
    def __init__(self):
        url = "https://vmyvivlqsklrdlmtlkvf.supabase.co"
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase: Client = create_client(url, key)
    
    def store_trading_session(self, user_id: str, session_data: dict):
        """Store trading session data in Supabase"""
        return self.supabase.table('trading_sessions').insert({
            'user_id': user_id,
            'session_data': session_data,
            'created_at': 'now()'
        }).execute()
    
    def get_user_trading_history(self, user_id: str):
        """Get user's trading history"""
        return self.supabase.table('trading_history').select('*').eq('user_id', user_id).execute()
    
    def store_portfolio_snapshot(self, user_id: str, portfolio_data: dict):
        """Store daily portfolio snapshots"""
        return self.supabase.table('portfolio_snapshots').insert({
            'user_id': user_id,
            'portfolio_data': portfolio_data,
            'snapshot_date': 'now()'
        }).execute()
```

### Option 3: AI-Powered Features

Use VibeOps AI capabilities for enhanced functionality:

#### Generate Trading Charts/Visualizations
```python
# app/ai/image_service.py
from mcp_vibeops import VIBEOPS_EXECUTE_FUNCTION

class AIImageService:
    @staticmethod
    def generate_trading_chart(prompt: str):
        """Generate trading-related images using FLUX"""
        result = VIBEOPS_EXECUTE_FUNCTION(
            function_name="REPLICATE__MODEL_FLUX_1_1_PRO",
            function_args={
                "input": {
                    "prompt": f"Professional trading dashboard {prompt}, clean UI, financial charts, modern design",
                    "aspect_ratio": "16:9",
                    "output_format": "png",
                    "output_quality": 95
                }
            }
        )
        return result
    
    @staticmethod
    def generate_portfolio_visualization(portfolio_data: dict):
        """Generate portfolio visualization"""
        prompt = f"Portfolio visualization showing {len(portfolio_data.get('holdings', []))} holdings, total value chart, professional financial dashboard"
        return AIImageService.generate_trading_chart(prompt)
```

## Database Schema Setup

Create tables in Supabase for enhanced functionality:

```sql
-- User profiles table
CREATE TABLE user_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    display_name TEXT,
    email TEXT,
    avatar_url TEXT,
    trading_preferences JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trading sessions table
CREATE TABLE trading_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_data JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Portfolio snapshots table
CREATE TABLE portfolio_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    portfolio_data JSONB NOT NULL,
    total_value DECIMAL,
    total_pnl DECIMAL,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trading history table
CREATE TABLE trading_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    trade_type TEXT NOT NULL, -- 'BUY', 'SELL'
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL NOT NULL,
    total_amount DECIMAL NOT NULL,
    trade_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    broker_order_id TEXT,
    status TEXT DEFAULT 'PENDING'
);

-- Enable Row Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_history ENABLE ROW LEVEL SECURITY;

-- Create policies (users can only access their own data)
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (user_id = current_user::text);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (user_id = current_user::text);
```

## Deployment Workflow

### Automatic Deployment
1. **Push to GitLab**: Any push to the `main` branch triggers automatic deployment
2. **Vercel Build**: Automatically builds and deploys your frontend
3. **Environment Variables**: Pre-configured for seamless integration

### Manual Deployment Controls
Use VibeOps MCP functions for manual control:

```python
# Check deployment status
deployment_status = VIBEOPS_EXECUTE_FUNCTION(
    function_name="VERCEL__LIST_DEPLOYMENTS",
    function_args={"vercel_project_id": "prj_Bew3A3R7zsTUnpz6my5dRZlMhL5i"}
)

# Get Supabase project health
health_status = VIBEOPS_EXECUTE_FUNCTION(
    function_name="SUPABASE__GET_PROJECT_HEALTH_STATUS",
    function_args={"supabase_project_id": "vmyvivlqsklrdlmtlkvf"}
)
```

## Benefits Summary

### 🚀 **Performance & Scalability**
- **Vercel Edge Network**: Global CDN for fast frontend delivery
- **Supabase**: Managed PostgreSQL with connection pooling
- **Railway Backend**: Your existing API remains unchanged

### 🔒 **Security & Reliability**
- **Row Level Security**: Supabase RLS for data protection
- **Environment Variables**: Secure configuration management
- **HTTPS Everywhere**: SSL/TLS encryption across all services

### 🛠️ **Developer Experience**
- **Auto-deployment**: Push to deploy workflow
- **Environment Management**: Centralized configuration
- **Monitoring**: Built-in deployment and health monitoring

### 🎨 **Enhanced Features**
- **AI Image Generation**: Create trading visualizations
- **Real-time Updates**: Supabase real-time subscriptions
- **Modern Frontend**: React/Next.js with TypeScript

## Next Steps

1. **Set up GitLab remote** and push your code
2. **Choose integration option** (frontend replacement, backend enhancement, or both)
3. **Create database schema** in Supabase
4. **Deploy and test** the integrated solution

Your QuantumLeap Trading project now has enterprise-grade infrastructure ready for scaling! 