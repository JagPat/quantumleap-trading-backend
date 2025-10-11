/**
 * Trading Mode Manager
 * Manages manual vs automatic trading mode for users
 * Handles consent tracking for automated trading
 */

const db = require('../../../core/database/connection');
const EventBus = require('../../../shared/events/eventBus');

class TradingModeManager {
  constructor() {
    this.db = db;
    this.eventBus = EventBus;
    
    // Default mode is manual for safety
    this.defaultMode = 'manual';
  }

  /**
   * Get user's trading mode
   * @param {string} userId - User ID
   * @returns {string} 'manual' | 'auto'
   */
  async getMode(userId) {
    try {
      const result = await this.db.query(
        `SELECT trading_mode FROM ai_preferences WHERE user_id = $1`,
        [userId]
      );
      
      return result.rows[0]?.trading_mode || this.defaultMode;
    } catch (error) {
      console.error('[TradingModeManager] Error getting mode:', error);
      return this.defaultMode; // Safe fallback
    }
  }

  /**
   * Set user's trading mode
   * @param {string} userId - User ID
   * @param {string} mode - 'manual' | 'auto'
   * @returns {Object} Updated mode status
   */
  async setMode(userId, mode) {
    try {
      if (!['manual', 'auto'].includes(mode)) {
        throw new Error(`Invalid trading mode: ${mode}. Must be 'manual' or 'auto'`);
      }

      // If switching to auto, verify consent exists
      if (mode === 'auto') {
        const hasConsent = await this.hasAutoTradingConsent(userId);
        if (!hasConsent) {
          throw new Error('Auto-trading consent required before enabling automatic mode');
        }
      }

      await this.db.query(
        `UPDATE ai_preferences 
         SET trading_mode = $1, 
             updated_at = NOW()
         WHERE user_id = $2`,
        [mode, userId]
      );

      // Emit mode change event
      this.eventBus.emit('trading:mode-changed', {
        userId,
        mode,
        timestamp: new Date().toISOString()
      });

      console.log(`[TradingModeManager] User ${userId} trading mode set to: ${mode}`);

      return {
        success: true,
        mode,
        message: mode === 'auto' 
          ? 'Automatic trading enabled - AI will execute trades automatically'
          : 'Manual trading enabled - AI will suggest trades for your approval'
      };

    } catch (error) {
      console.error('[TradingModeManager] Error setting mode:', error);
      throw error;
    }
  }

  /**
   * Check if user has given consent for auto-trading
   * @param {string} userId - User ID
   * @returns {boolean} True if consent given
   */
  async hasAutoTradingConsent(userId) {
    try {
      const result = await this.db.query(
        `SELECT auto_trading_consent, consent_timestamp 
         FROM ai_preferences 
         WHERE user_id = $1`,
        [userId]
      );
      
      const consent = result.rows[0]?.auto_trading_consent;
      const timestamp = result.rows[0]?.consent_timestamp;
      
      // Consent is valid if given and not expired (valid for 90 days)
      if (consent && timestamp) {
        const consentAge = Date.now() - new Date(timestamp).getTime();
        const maxAge = 90 * 24 * 60 * 60 * 1000; // 90 days
        
        if (consentAge < maxAge) {
          return true;
        } else {
          console.warn('[TradingModeManager] Auto-trading consent expired for user:', userId);
          // Auto-revoke consent if expired
          await this.revokeAutoTradingConsent(userId);
          return false;
        }
      }
      
      return false;
    } catch (error) {
      console.error('[TradingModeManager] Error checking consent:', error);
      return false; // Safe fallback - deny auto-trading if error
    }
  }

  /**
   * Record user consent for auto-trading
   * @param {string} userId - User ID
   * @param {Object} consentData - Consent details (disclaimers, IP, etc.)
   * @returns {Object} Consent status
   */
  async grantAutoTradingConsent(userId, consentData = {}) {
    try {
      await this.db.query(
        `UPDATE ai_preferences 
         SET auto_trading_consent = true,
             consent_timestamp = NOW(),
             consent_ip = $2,
             consent_disclaimers = $3,
             updated_at = NOW()
         WHERE user_id = $1`,
        [
          userId,
          consentData.ip || 'unknown',
          JSON.stringify(consentData.disclaimers || [])
        ]
      );

      // Emit consent event
      this.eventBus.emit('trading:consent-granted', {
        userId,
        timestamp: new Date().toISOString(),
        ip: consentData.ip
      });

      console.log(`[TradingModeManager] Auto-trading consent granted for user: ${userId}`);

      return {
        success: true,
        message: 'Auto-trading consent recorded successfully',
        validUntil: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString()
      };

    } catch (error) {
      console.error('[TradingModeManager] Error granting consent:', error);
      throw error;
    }
  }

  /**
   * Revoke auto-trading consent
   */
  async revokeAutoTradingConsent(userId) {
    try {
      await this.db.query(
        `UPDATE ai_preferences 
         SET auto_trading_consent = false,
             trading_mode = 'manual',
             consent_timestamp = NULL,
             updated_at = NOW()
         WHERE user_id = $1`,
        [userId]
      );

      this.eventBus.emit('trading:consent-revoked', {
        userId,
        timestamp: new Date().toISOString()
      });

      console.log(`[TradingModeManager] Auto-trading consent revoked for user: ${userId}`);

      return {
        success: true,
        message: 'Auto-trading consent revoked, switched to manual mode'
      };

    } catch (error) {
      console.error('[TradingModeManager] Error revoking consent:', error);
      throw error;
    }
  }

  /**
   * Check if user can execute trades automatically
   * @param {string} userId - User ID
   * @returns {boolean} True if user can execute automatically
   */
  async canExecuteAutomatically(userId) {
    const mode = await this.getMode(userId);
    const hasConsent = await this.hasAutoTradingConsent(userId);
    
    return mode === 'auto' && hasConsent;
  }

  /**
   * Get complete trading mode status for user
   */
  async getStatus(userId) {
    try {
      const mode = await this.getMode(userId);
      const hasConsent = await this.hasAutoTradingConsent(userId);
      const canExecute = mode === 'auto' && hasConsent;

      const result = await this.db.query(
        `SELECT consent_timestamp, consent_ip 
         FROM ai_preferences 
         WHERE user_id = $1`,
        [userId]
      );

      const consentTimestamp = result.rows[0]?.consent_timestamp;
      const consentIp = result.rows[0]?.consent_ip;

      return {
        mode,
        hasConsent,
        canExecuteAutomatically: canExecute,
        consentDetails: hasConsent ? {
          grantedAt: consentTimestamp,
          grantedFrom: consentIp,
          validUntil: consentTimestamp 
            ? new Date(new Date(consentTimestamp).getTime() + 90 * 24 * 60 * 60 * 1000).toISOString()
            : null
        } : null,
        message: canExecute 
          ? 'Auto-trading enabled with valid consent'
          : mode === 'auto'
            ? 'Auto-trading mode enabled but consent required'
            : 'Manual trading mode - trades require approval'
      };

    } catch (error) {
      console.error('[TradingModeManager] Error getting status:', error);
      throw error;
    }
  }
}

// Export singleton instance
let instance = null;

const getTradingModeManager = () => {
  if (!instance) {
    instance = new TradingModeManager();
  }
  return instance;
};

module.exports = getTradingModeManager;

