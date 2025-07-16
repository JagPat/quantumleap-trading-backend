# Railway Deployment Validation Checklist

## 🚨 **Emergency Deployment Fix - Phase 2.2 BYOAI**

### **Pre-Deployment Checks**
- [ ] All startup logging added to main.py
- [ ] Health check endpoint has debug logging
- [ ] Railway.json uses `/health` endpoint
- [ ] Startup test endpoint added for debugging

### **Post-Deployment Validation**

#### **1. Basic Health Checks**
```bash
# Test basic health endpoint
curl -s https://web-production-de0bc.up.railway.app/health
# Expected: {"status":"ok", "app": "QuantumLeap Trading Backend", "version": "2.0.0"}

# Test startup test endpoint
curl -s https://web-production-de0bc.up.railway.app/startup-test
# Expected: {"status":"running", "message":"App is running successfully"}

# Test ping endpoint
curl -s https://web-production-de0bc.up.railway.app/ping
# Expected: {"status":"pong", "timestamp":"2024-12-19"}
```

#### **2. Version and Deployment Info**
```bash
# Test version endpoint
curl -s https://web-production-de0bc.up.railway.app/version
# Expected: {"app_version":"2.0.0", "deployment":"latest", "commit":"[latest]", "ai_engine":"enabled/disabled"}

# Test root endpoint
curl -s https://web-production-de0bc.up.railway.app/
# Expected: {"message":"QuantumLeap Trading Backend API", "version":"2.0.0", "docs":"/docs", "health":"/health", "deployment":"latest"}
```

#### **3. AI Engine Endpoints**
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
```

#### **4. Auth Endpoints (BYOAI)**
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

#### **5. API Documentation**
```bash
# Test OpenAPI docs
curl -s https://web-production-de0bc.up.railway.app/openapi.json | jq '.paths | keys' | grep -E "(ai|preferences|health|version)"
# Expected: Should list all AI endpoints, health, version, etc.
```

### **Railway Log Analysis**

#### **Success Indicators**
- ✅ Build completes in ~40 seconds
- ✅ All dependencies install successfully
- ✅ Startup logs show "🚀 Starting QuantumLeap Trading Backend..."
- ✅ Database initialization logs appear
- ✅ "🎯 FastAPI app startup complete" message
- ✅ Health check logs show "🏥 Health check requested"

#### **Failure Indicators**
- ❌ Build fails during dependency installation
- ❌ Startup logs show import errors
- ❌ Database initialization fails
- ❌ Health check returns "service unavailable"
- ❌ No startup completion message

### **Debugging Steps**

#### **If Health Check Fails**
1. Check Railway logs for startup errors
2. Look for import errors in AI engine
3. Verify database initialization
4. Check if FastAPI app starts properly

#### **If AI Endpoints Missing**
1. Check AI engine import logs
2. Verify router inclusion in main.py
3. Test AI engine import locally
4. Check for missing dependencies

#### **If Deployment Rolls Back**
1. Verify all endpoints work locally
2. Check Railway build logs
3. Ensure health check endpoint is accessible
4. Test with minimal app configuration

### **Emergency Rollback Plan**

If deployment continues to fail:
1. **Temporary Fix**: Remove AI engine import to get basic app running
2. **Debug AI Engine**: Fix import issues in isolation
3. **Gradual Rollout**: Add AI features back incrementally
4. **Alternative Health Check**: Use `/startup-test` as health check endpoint

### **Success Criteria**

#### **Phase 2.2 BYOAI Completion**
- [ ] All health check endpoints respond correctly
- [ ] AI engine endpoints are available and functional
- [ ] Version endpoint shows correct commit hash
- [ ] Frontend can connect to backend successfully
- [ ] BYOAI features work end-to-end

#### **Deployment Stability**
- [ ] Railway build completes successfully
- [ ] Health checks pass consistently
- [ ] No startup errors in logs
- [ ] All endpoints respond within 5 seconds
- [ ] App remains stable under load

### **Next Steps After Successful Deployment**

1. **Frontend Integration Test**: Test AI settings form
2. **End-to-End Validation**: Complete BYOAI workflow
3. **Performance Testing**: Verify response times
4. **Security Validation**: Test API key encryption
5. **User Acceptance**: Validate complete user experience

---

**Last Updated**: 2024-12-19
**Commit**: [Latest commit hash after deployment]
**Status**: Emergency deployment fix in progress 