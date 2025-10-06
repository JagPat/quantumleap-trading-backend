/**
 * Centralized User Identifier Resolver
 * Resolves an incoming identifier into a broker config object.
 * Supports both config_id (UUID) and external broker user_id (e.g. EBW183)
 */

const db = require('../../../core/database/connection');
const { isUUID } = require('../../../core/utils');

/**
 * Resolves an incoming identifier into a broker config object.
 * @param {string} input - Can be config_id (UUID) or external broker user_id (e.g. EBW183)
 * @param {string} brokerName - Broker name to scope queries (default: 'zerodha')
 * @returns {Object|null} - Resolved config object or null if not found
 */
async function resolveUserIdentifier(input, brokerName = 'zerodha') {
  // Debug logging for verification
  console.debug('[resolveUserIdentifier] Starting resolution for input:', input, 'broker:', brokerName);
  
  // Basic input validation
  if (!input) {
    console.debug('[resolveUserIdentifier] No input provided');
    return null;
  }

  try {
    // 1) If it's a UUID, try config_id lookup first
    if (isUUID(input)) {
      console.debug('[resolveUserIdentifier] Input is UUID, trying config_id lookup');
      
      const configResult = await db.query(`
        SELECT bc.* 
        FROM broker_configs bc 
        WHERE bc.id = $1 AND bc.broker_name = $2
        LIMIT 1
      `, [input, brokerName]);
      
      if (configResult.rows.length > 0) {
        const config = configResult.rows[0];
        
        // Get associated oauth token
        const tokenResult = await db.query(`
          SELECT * FROM oauth_tokens 
          WHERE config_id = $1 
          LIMIT 1
        `, [config.id]);
        
        const token = tokenResult.rows[0] || null;
        
        const resolved = {
          configId: config.id,
          brokerUserId: token?.broker_user_id || config.user_id || null,
          oauthTokenRow: token,
          brokerConfigRow: config
        };
        
        console.debug('[resolveUserIdentifier] Resolved via config_id:', { 
          configId: resolved.configId, 
          brokerUserId: resolved.brokerUserId 
        });
        
        return resolved;
      }
    }

    // 2) Try broker_configs.user_id (for internal user IDs)
    console.debug('[resolveUserIdentifier] Trying broker_configs.user_id lookup');
    
    const configByUserIdResult = await db.query(`
      SELECT bc.* 
      FROM broker_configs bc 
      WHERE bc.user_id = $1 AND bc.broker_name = $2
      LIMIT 1
    `, [input, brokerName]);
    
    if (configByUserIdResult.rows.length > 0) {
      const config = configByUserIdResult.rows[0];
      
      // Get associated oauth token
      const tokenResult = await db.query(`
        SELECT * FROM oauth_tokens 
        WHERE config_id = $1 
        LIMIT 1
      `, [config.id]);
      
      const token = tokenResult.rows[0] || null;
      
      const resolved = {
        configId: config.id,
        brokerUserId: token?.broker_user_id || config.user_id || null,
        oauthTokenRow: token,
        brokerConfigRow: config
      };
      
      console.debug('[resolveUserIdentifier] Resolved via broker_configs.user_id:', { 
        configId: resolved.configId, 
        brokerUserId: resolved.brokerUserId 
      });
      
      return resolved;
    }

    // 3) Fallback: search oauth_tokens.broker_user_id -> join broker_configs
    console.debug('[resolveUserIdentifier] Trying oauth_tokens.broker_user_id fallback');
    
    const joinedResult = await db.query(`
      SELECT bc.*, ot.*
      FROM oauth_tokens ot
      JOIN broker_configs bc ON bc.id = ot.config_id
      WHERE ot.broker_user_id = $1 AND bc.broker_name = $2
      ORDER BY ot.updated_at DESC
      LIMIT 1
    `, [input, brokerName]);
    
    if (joinedResult.rows.length > 0) {
      const row = joinedResult.rows[0];
      
      // Extract broker config and oauth token data
      const brokerConfigRow = {
        id: row.id,
        user_id: row.user_id,
        broker_name: row.broker_name,
        api_key: row.api_key,
        api_secret_encrypted: row.api_secret_encrypted,
        is_connected: row.is_connected,
        connection_status: row.connection_status,
        oauth_state: row.oauth_state,
        broker_user_id: row.broker_user_id,
        broker_user_name: row.broker_user_name,
        broker_user_type: row.broker_user_type,
        last_sync_at: row.last_sync_at,
        created_at: row.created_at,
        updated_at: row.updated_at
      };
      
      const oauthTokenRow = {
        id: row.id,
        config_id: row.config_id,
        access_token_encrypted: row.access_token_encrypted,
        refresh_token_encrypted: row.refresh_token_encrypted,
        expires_at: row.expires_at,
        token_type: row.token_type,
        scope: row.scope,
        broker_user_id: row.broker_user_id,
        created_at: row.created_at,
        updated_at: row.updated_at
      };
      
      const resolved = {
        configId: brokerConfigRow.id,
        brokerUserId: oauthTokenRow.broker_user_id || brokerConfigRow.user_id || null,
        oauthTokenRow: oauthTokenRow,
        brokerConfigRow: brokerConfigRow
      };
      
      console.debug('[resolveUserIdentifier] Resolved via oauth_tokens.broker_user_id:', { 
        configId: resolved.configId, 
        brokerUserId: resolved.brokerUserId 
      });
      
      return resolved;
    }

    // Not found
    console.debug('[resolveUserIdentifier] No resolution found for input:', input);
    return null;

  } catch (error) {
    console.error('[resolveUserIdentifier] Error during resolution:', error);
    throw error;
  }
}

module.exports = resolveUserIdentifier;
