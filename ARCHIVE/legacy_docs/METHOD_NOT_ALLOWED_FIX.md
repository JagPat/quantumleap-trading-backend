# Method Not Allowed (405) Fix

## Problem Identified
The frontend was getting 405 "Method Not Allowed" errors for the `fetch-live-simple` endpoint:
```
Failed to load resource: the server responded with a status of 405 () (fetch-live-simple, line 0)
❌ [RailwayAPI] Error: Method Not Allowed
```

## Root Cause
**HTTP Method Mismatch**: The frontend was sending POST requests to an endpoint that only accepts GET.

### Backend Endpoint Configuration
- **Main Router** (`app/portfolio/router.py`): `@router.get("/fetch-live-simple")` - Accepts GET ✅
- **Fallback Router** (`app/portfolio/fallback_router.py`): `@router.post("/fetch-live-simple")` - Accepts POST ❌

### Frontend Request Configuration
```javascript
// BEFORE (incorrect)
async fetchLivePortfolio(userId) {
  return this.request(`/api/portfolio/fetch-live-simple?user_id=${userId}`, {
    method: 'POST',  // ❌ Wrong method
  });
}
```

## Solution Applied

### Fixed Frontend Method
**File:** `quantum-leap-frontend/src/api/railwayAPI.js`
**Change:** Changed POST to GET

```javascript
// AFTER (correct)
async fetchLivePortfolio(userId) {
  return this.request(`/api/portfolio/fetch-live-simple?user_id=${userId}`, {
    method: 'GET',  // ✅ Correct method
  });
}
```

## Verification

### Backend Test Results
```bash
# POST (was failing)
curl -X POST "https://web-production-de0bc.up.railway.app/api/portfolio/fetch-live-simple?user_id=EBW183"
# Response: {"detail":"Method Not Allowed"} Status: 405

# GET (now working)
curl -X GET "https://web-production-de0bc.up.railway.app/api/portfolio/fetch-live-simple?user_id=EBW183"
# Response: {"status":"success","data":{...}} Status: 200
```

### Other Endpoints Checked
- ✅ `latest-simple`: Uses GET by default (no explicit method) - Working
- ✅ `mock`: Uses GET by default - Working
- ✅ AI endpoints: Use GET by default - Working

## Expected Result
After refreshing the frontend, the 405 errors should disappear and portfolio data should load properly.

## Technical Details

### Why This Happened
1. The main portfolio router was deployed and working (GET endpoints)
2. The fallback router has POST endpoints but isn't being used
3. Frontend was configured to use POST, matching the fallback router
4. But the main router only accepts GET, causing 405 errors

### The Fix
Simply aligning the frontend HTTP method with the backend endpoint method.

## Status
✅ **FIXED** - Frontend now uses GET method for `fetch-live-simple`
✅ **TESTED** - Backend responds with 200 for GET requests
✅ **DEPLOYED** - Change is ready for frontend refresh

**Next Step:** Refresh your frontend to see the fix in action!