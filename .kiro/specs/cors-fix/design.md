# CORS Fix Design Document

## Overview

This design addresses the persistent CORS preflight failures by implementing a comprehensive solution that covers both backend CORS configuration and frontend error handling. The solution ensures browser compatibility and provides robust error recovery.

## Architecture

### Backend CORS Layer
- Enhanced FastAPI CORS middleware configuration
- Explicit OPTIONS route handlers for problematic endpoints
- Comprehensive header allowlist
- Origin validation with wildcard support

### Frontend Error Handling Layer
- Improved error detection and classification
- Exponential backoff retry mechanism
- Request deduplication to prevent spam
- User-friendly error messaging

### Monitoring Layer
- Detailed logging for debugging
- Health check integration
- Performance metrics tracking

## Components and Interfaces

### 1. Backend CORS Configuration

#### Enhanced CORS Middleware
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "https://quantum-leap-frontend.vercel.app",
        "https://quantum-leap-frontend-*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language", 
        "Content-Type",
        "Authorization",
        "Origin",
        "X-Requested-With",
        "X-User-ID",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
    max_age=600,
)
```

#### Explicit OPTIONS Handlers
```python
@app.options("/api/{path:path}")
async def api_options_handler(path: str, request: Request):
    origin = request.headers.get("origin", "")
    
    # Validate origin
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://quantum-leap-frontend.vercel.app"
    ]
    
    if origin in allowed_origins or origin.startswith("https://quantum-leap-frontend-"):
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "Accept, Accept-Language, Content-Language, Content-Type, Authorization, Origin, X-Requested-With, X-User-ID, Access-Control-Request-Method, Access-Control-Request-Headers",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "600"
            }
        )
    else:
        return Response(status_code=403, content="Origin not allowed")
```

### 2. Frontend Error Handling

#### Enhanced Error Detection
```javascript
const isCORSError = (error) => {
    return error.message.includes('CORS') || 
           error.message.includes('Access-Control') || 
           error.message.includes('Load failed') ||
           error.message.includes('Failed to fetch') ||
           error.message.includes('Preflight') ||
           error.message.includes('access control checks') ||
           (error.name === 'TypeError' && (
               error.message === 'Load failed' ||
               error.message.includes('Failed to fetch') ||
               error.message === 'Network request failed'
           ));
};
```

#### Retry Logic with Exponential Backoff
```javascript
async function retryRequest(endpoint, options, attempt = 0) {
    const maxRetries = 3;
    const baseDelay = 1000;
    
    if (attempt >= maxRetries) {
        throw new Error('Max retries exceeded');
    }
    
    try {
        return await makeRequest(endpoint, options);
    } catch (error) {
        if (isCORSError(error)) {
            const delay = baseDelay * Math.pow(2, attempt);
            console.warn(`🔄 [RailwayAPI] CORS error, retrying ${attempt + 1}/${maxRetries} for ${endpoint} after ${delay}ms`);
            
            await new Promise(resolve => setTimeout(resolve, delay));
            return retryRequest(endpoint, options, attempt + 1);
        }
        throw error;
    }
}
```

### 3. Request Deduplication

#### Pending Request Management
```javascript
class RequestManager {
    constructor() {
        this.pendingRequests = new Map();
    }
    
    async request(key, requestFn) {
        if (this.pendingRequests.has(key)) {
            return this.pendingRequests.get(key);
        }
        
        const promise = requestFn();
        this.pendingRequests.set(key, promise);
        
        try {
            const result = await promise;
            return result;
        } finally {
            this.pendingRequests.delete(key);
        }
    }
}
```

## Data Models

### Error Response Model
```javascript
{
    status: 'cors_error' | 'network_error' | 'timeout_error',
    message: string,
    error: string,
    endpoint: string,
    retry_suggested: boolean,
    retries_exhausted?: boolean,
    retry_after?: number
}
```

### Health Check Model
```javascript
{
    backend_healthy: boolean,
    last_check: timestamp,
    cors_working: boolean,
    response_time: number
}
```

## Error Handling

### CORS Error Classification
1. **Preflight Failure**: OPTIONS request returns 400/403
2. **Header Rejection**: Required headers not allowed
3. **Origin Rejection**: Origin not in allowlist
4. **Network Failure**: Complete connection failure

### Error Recovery Strategies
1. **Immediate Retry**: For transient network issues
2. **Exponential Backoff**: For server overload
3. **Fallback Endpoints**: For service degradation
4. **User Notification**: For persistent failures

### Fallback Mechanisms
1. **Mock Data**: When backend unavailable
2. **Cached Responses**: For recently fetched data
3. **Offline Mode**: For critical functionality

## Testing Strategy

### Backend Testing
1. **Unit Tests**: CORS middleware configuration
2. **Integration Tests**: OPTIONS endpoint responses
3. **Browser Tests**: Real browser preflight requests
4. **Load Tests**: High-volume CORS requests

### Frontend Testing
1. **Error Simulation**: Mock CORS failures
2. **Retry Logic**: Verify exponential backoff
3. **Deduplication**: Prevent duplicate requests
4. **User Experience**: Error message display

### End-to-End Testing
1. **Cross-Origin Requests**: Full browser flow
2. **Authentication Flow**: With CORS headers
3. **Error Recovery**: Network interruption scenarios
4. **Performance**: Response time under load

## Performance Considerations

### Backend Optimizations
- CORS preflight caching (max-age: 600)
- Efficient origin validation
- Minimal header processing

### Frontend Optimizations
- Request deduplication
- Intelligent retry timing
- Connection pooling
- Response caching

## Security Considerations

### Origin Validation
- Strict origin checking
- No wildcard origins in production
- Subdomain pattern matching

### Header Security
- Minimal required headers
- No sensitive data in preflight
- Proper credential handling

## Monitoring and Logging

### Backend Metrics
- CORS request success rate
- Preflight response times
- Origin rejection counts
- Error categorization

### Frontend Metrics
- Retry attempt frequency
- Error recovery success rate
- User experience impact
- Network performance

This design provides a comprehensive solution to the CORS issues while maintaining security, performance, and user experience standards.