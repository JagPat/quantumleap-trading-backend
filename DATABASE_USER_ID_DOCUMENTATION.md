# Database user_id Field Documentation

## Overview
This document clarifies the different meanings of `user_id` across database tables to prevent confusion and bugs.

## Schema Reference

### Table: `broker_configs`
**Column: `user_id`**
- **Type**: `VARCHAR(255)`
- **Meaning**: System user identifier (can be UUID or string)
- **Purpose**: Links broker configuration to our application's user
- **Example**: `"550e8400-e29b-41d4-a716-446655440000"` (UUID) or OAuth-only user string

**Column: `broker_user_id`**
- **Type**: `VARCHAR(100)`
- **Meaning**: Broker's internal user identifier
- **Purpose**: Stores the user ID from the broker (Zerodha, Upstox, etc.)
- **Example**: `"EBW183"` (Zerodha user ID)

### Table: `oauth_tokens`
**Column: `user_id`**
- **Type**: `VARCHAR(255)` (in old schema) or not present (in new schema)
- **Meaning**: **DEPRECATED** - Previously stored broker's user ID
- **Current**: Should reference `broker_configs.broker_user_id` instead
- **Note**: This creates confusion with `broker_configs.user_id`

**Column: `config_id`**
- **Type**: `UUID`
- **Meaning**: Foreign key to `broker_configs.id`
- **Purpose**: Links tokens to a specific broker configuration
- **Relationship**: `oauth_tokens.config_id` → `broker_configs.id`

## Data Flow (OAuth)

1. **OAuth Callback** (`/api/broker/callback`)
   - Receives `request_token` from Zerodha
   - Exchanges for `access_token` and `refresh_token`
   - Fetches user profile from Zerodha API: `/user/profile`
   - Extracts `broker_user_id` from profile (e.g., `"EBW183"`)

2. **Database Storage**
   ```sql
   -- Store tokens
   INSERT INTO oauth_tokens (config_id, access_token_encrypted, refresh_token_encrypted)
   VALUES ($config_id, $encrypted_access, $encrypted_refresh);
   
   -- Update broker config with broker's user ID
   UPDATE broker_configs 
   SET broker_user_id = $broker_user_id 
   WHERE id = $config_id;
   ```

3. **Frontend Session**
   - Backend redirects with: `?config_id=XXX&user_id=YYY`
   - `user_id` in URL = broker's user ID (for immediate use)
   - Frontend stores in localStorage as: `{ config_id, user_id }` (snake_case)
   - Frontend loads and transforms to: `{ configId, userId }` (camelCase)

## Key Principles

### 1. Zerodha API Compliance
- All backend responses use **snake_case**
- Database schema follows Zerodha's data structure
- Example: `{ config_id: UUID, user_id: "EBW183", broker_name: "zerodha" }`

### 2. Frontend Transformation
- localStorage stores **snake_case** (matches backend)
- `brokerSessionStore.load()` transforms to **camelCase**
- Components consume **camelCase**: `{ configId, userId, brokerName }`

### 3. Database Clarity
- `broker_configs.user_id` = **System user** (our app's user identifier)
- `broker_configs.broker_user_id` = **Broker's user** (Zerodha's user ID)
- `oauth_tokens.config_id` = **Links to broker_configs.id**

## Common Pitfalls

❌ **Wrong**: Assuming `user_id` always means the same thing
```javascript
// BAD - ambiguous which user_id
const userId = session.user_id;
```

✅ **Correct**: Be explicit about which user ID you mean
```javascript
// GOOD - clear it's the broker's user ID
const brokerUserId = session.user_id; // From frontend session
const systemUserId = brokerConfig.user_id; // From database
```

## Related Issues
- **LEAK-001**: Session persistence mismatch (`userId` vs `user_id`)
- **LEAK-002**: Inconsistent property naming across stack
- **Fix**: Unified schema with snake_case persist, camelCase load

## References
- Zerodha Kite Connect API: https://kite.trade/docs/connect/v3/
- OAuth implementation: `backend-temp/modules/auth/routes/oauth.js`
- Session storage: `src/api/sessionStore.js`

