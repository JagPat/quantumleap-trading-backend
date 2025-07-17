# Railway Deployment Test Checklist

## 🚀 **Phase 2.2 BYOAI Deployment Validation**

### **Pre-Deployment Checks**

- [ ] All code committed to GitHub
- [ ] `.nixpacks.toml` created with proper configuration
- [ ] `.dockerignore` excludes unnecessary files
- [ ] `requirements.txt` contains all AI dependencies
- [ ] `main.py` has error handling for AI engine imports

### **Post-Deployment Health Checks**

#### **1. Basic Health Endpoints**

```bash
# Test basic health
curl -s https://web-production-de0bc.up.railway.app/health
# Expected: {"status":"ok"}

# Test root endpoint
curl -s https://web-production-de0bc.up.railway.app/
# Expected: {"message":"QuantumLeap Trading Backend API",...}
```

#### **2. AI Engine Endpoints**

```bash
# Test AI preferences endpoint
curl -s https://web-production-de0bc.up.railway.app/api/ai/preferences
# Expected: JSON response with preferences or defaults

# Test AI key validation
curl -s -X POST https://web-production-de0bc.up.railway.app/api/ai/validate-key \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"test"}'
# Expected: Validation response

# Test AI signals endpoint
curl -s https://web-production-de0bc.up.railway.app/api/ai/signals
# Expected: AI signals response

# Test AI strategy endpoint
curl -s https://web-production-de0bc.up.railway.app/api/ai/strategy
# Expected: Strategy generation response
```

#### **3. Auth Endpoints (BYOAI)**

```bash
# Test auth AI preferences
curl -s https://web-production-de0bc.up.railway.app/api/auth/ai/preferences
# Expected: User AI preferences

# Test auth AI key validation
curl -s -X POST https://web-production-de0bc.up.railway.app/api/auth/ai/validate-key \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"test"}'
# Expected: Validation response
```

#### **4. Portfolio Endpoints**

```bash
# Test portfolio endpoints
curl -s https://web-production-de0bc.up.railway.app/api/portfolio/latest
# Expected: Portfolio data or error message
```

### **Frontend Integration Tests**

#### **1. AI Settings Form**

- [ ] Navigate to Settings → AI Settings tab
- [ ] Test provider selection dropdown (OpenAI, Claude, Gemini)
- [ ] Test API key input fields with validation
- [ ] Test "Test Key" functionality
- [ ] Test "Save Preferences" button
- [ ] Verify error handling and user feedback

#### **2. Dashboard Integration**

- [ ] Check AI provider status indicators
- [ ] Test strategy generation workflow
- [ ] Verify portfolio co-pilot functionality
- [ ] Test AI settings navigation

### **Security Validation**

- [ ] API keys are encrypted before storage
- [ ] No API keys exposed in frontend responses
- [ ] User isolation of AI preferences
- [ ] Partial key previews work correctly
- [ ] Validation errors handled securely

### **Performance Tests**

- [ ] Health endpoint responds < 1 second
- [ ] AI preferences endpoint responds < 2 seconds
- [ ] Key validation responds < 5 seconds
- [ ] Strategy generation responds < 10 seconds

### **Error Handling Tests**

- [ ] Invalid API keys show appropriate errors
- [ ] Network failures handled gracefully
- [ ] Missing dependencies don't crash the app
- [ ] Import errors logged but don't break deployment

## 🎯 **Success Criteria**

### **Phase 2.2 BYOAI Completion**

- [ ] All AI endpoints accessible via Railway
- [ ] Frontend AI settings form functional
- [ ] API key validation working
- [ ] User preferences persisted securely
- [ ] Dashboard AI integration complete

### **Deployment Stability**

- [ ] Railway build completes successfully
- [ ] No import errors in deployment logs
- [ ] All endpoints respond correctly
- [ ] Health checks pass consistently

### **User Experience**

- [ ] Smooth AI provider setup flow
- [ ] Clear error messages and feedback
- [ ] Secure API key management
- [ ] Intuitive settings interface

## 🚨 **Rollback Plan**

If deployment fails:

1. Check Railway deployment logs
2. Verify GitHub code is correct
3. Test locally if possible
4. Rollback to previous working commit if needed
5. Fix issues and redeploy

## 📊 **Monitoring**

After successful deployment:

- [ ] Monitor Railway logs for errors
- [ ] Track endpoint response times
- [ ] Monitor user AI settings usage
- [ ] Check for any security issues
