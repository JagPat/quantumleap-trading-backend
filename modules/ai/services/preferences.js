/**
 * AI Preferences Service
 * Handles storage and retrieval of user AI API keys
 */

const { pool: db } = require('../../../core/database/pool');
const SecurityManager = require('../../../core/security');

class AIPreferencesService {
  constructor() {
    this.security = new SecurityManager();
  }

  /**
   * Get user's AI preferences
   */
  async getPreferences(userId) {
    try {
      const result = await db.query(
        `SELECT 
          preferred_ai_provider,
          openai_key_preview,
          claude_key_preview,
          gemini_key_preview,
          CASE WHEN openai_api_key_encrypted IS NOT NULL THEN true ELSE false END as has_openai_key,
          CASE WHEN claude_api_key_encrypted IS NOT NULL THEN true ELSE false END as has_claude_key,
          CASE WHEN gemini_api_key_encrypted IS NOT NULL THEN true ELSE false END as has_gemini_key,
          created_at,
          updated_at
         FROM ai_preferences
         WHERE user_id = $1`,
        [userId]
      );

      if (result.rows.length === 0) {
        return null;
      }

      return result.rows[0];
    } catch (error) {
      console.error('[AIPreferences] Error getting preferences:', error);
      throw error;
    }
  }

  /**
   * Save or update user's AI preferences
   */
  async savePreferences(userId, configId, preferences) {
    try {
      const {
        preferred_ai_provider = 'auto',
        openai_api_key,
        claude_api_key,
        gemini_api_key
      } = preferences;

      // Encrypt API keys if provided
      const openaiEncrypted = openai_api_key ? this.security.encrypt(openai_api_key) : null;
      const claudeEncrypted = claude_api_key ? this.security.encrypt(claude_api_key) : null;
      const geminiEncrypted = gemini_api_key ? this.security.encrypt(gemini_api_key) : null;

      // Create key previews (first 7 chars + "...")
      const openaiPreview = openai_api_key ? `${openai_api_key.substring(0, 7)}...` : null;
      const claudePreview = claude_api_key ? `${claude_api_key.substring(0, 7)}...` : null;
      const geminiPreview = gemini_api_key ? `${gemini_api_key.substring(0, 7)}...` : null;

      // Check if preferences exist
      const existing = await this.getPreferences(userId);

      let result;
      if (existing) {
        // Update existing preferences
        result = await db.query(
          `UPDATE ai_preferences 
           SET preferred_ai_provider = $1,
               openai_api_key_encrypted = COALESCE($2, openai_api_key_encrypted),
               claude_api_key_encrypted = COALESCE($3, claude_api_key_encrypted),
               gemini_api_key_encrypted = COALESCE($4, gemini_api_key_encrypted),
               openai_key_preview = COALESCE($5, openai_key_preview),
               claude_key_preview = COALESCE($6, claude_key_preview),
               gemini_key_preview = COALESCE($7, gemini_key_preview),
               config_id = COALESCE($8, config_id),
               updated_at = NOW()
           WHERE user_id = $9
           RETURNING *`,
          [
            preferred_ai_provider,
            openaiEncrypted,
            claudeEncrypted,
            geminiEncrypted,
            openaiPreview,
            claudePreview,
            geminiPreview,
            configId,
            userId
          ]
        );
      } else {
        // Create new preferences
        result = await db.query(
          `INSERT INTO ai_preferences (
            user_id,
            config_id,
            preferred_ai_provider,
            openai_api_key_encrypted,
            claude_api_key_encrypted,
            gemini_api_key_encrypted,
            openai_key_preview,
            claude_key_preview,
            gemini_key_preview
           ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
           RETURNING *`,
          [
            userId,
            configId,
            preferred_ai_provider,
            openaiEncrypted,
            claudeEncrypted,
            geminiEncrypted,
            openaiPreview,
            claudePreview,
            geminiPreview
          ]
        );
      }

      const saved = result.rows[0];
      
      return {
        preferred_ai_provider: saved.preferred_ai_provider,
        has_openai_key: !!saved.openai_api_key_encrypted,
        has_claude_key: !!saved.claude_api_key_encrypted,
        has_gemini_key: !!saved.gemini_api_key_encrypted,
        openai_key_preview: saved.openai_key_preview,
        claude_key_preview: saved.claude_key_preview,
        gemini_key_preview: saved.gemini_key_preview
      };
    } catch (error) {
      console.error('[AIPreferences] Error saving preferences:', error);
      throw error;
    }
  }

  /**
   * Get decrypted API key for a specific provider
   * (Used by AI service to make API calls)
   */
  async getDecryptedKey(userId, provider) {
    try {
      const columnMap = {
        openai: 'openai_api_key_encrypted',
        claude: 'claude_api_key_encrypted',
        gemini: 'gemini_api_key_encrypted'
      };

      const column = columnMap[provider];
      if (!column) {
        throw new Error(`Invalid provider: ${provider}`);
      }

      const result = await db.query(
        `SELECT ${column} FROM ai_preferences WHERE user_id = $1`,
        [userId]
      );

      if (result.rows.length === 0 || !result.rows[0][column]) {
        return null;
      }

      return this.security.decrypt(result.rows[0][column]);
    } catch (error) {
      console.error('[AIPreferences] Error getting decrypted key:', error);
      throw error;
    }
  }

  /**
   * Delete user's AI preferences
   */
  async deletePreferences(userId) {
    try {
      await db.query(
        `DELETE FROM ai_preferences WHERE user_id = $1`,
        [userId]
      );
      return { success: true };
    } catch (error) {
      console.error('[AIPreferences] Error deleting preferences:', error);
      throw error;
    }
  }
}

module.exports = AIPreferencesService;



