const db = require('../../../core/database/connection');

/**
 * Strategy Goals Service
 * Handles validation, storage, and management of user-defined trading goals
 * for automated strategy execution
 */
class StrategyGoalsService {
  constructor() {
    this.db = db;
  }

  /**
   * Validate goal parameters
   * Ensures realistic and safe targets
   */
  validateGoals(goals) {
    const errors = [];

    // Profit target validation
    if (!goals.profitTarget || goals.profitTarget <= 0) {
      errors.push('Profit target must be greater than 0');
    }
    if (goals.profitTarget > 100) {
      errors.push('Profit target cannot exceed 100% for safety');
    }

    // Timeframe validation
    if (!goals.timeframe || goals.timeframe < 1) {
      errors.push('Timeframe must be at least 1 day');
    }
    if (goals.timeframe > 365) {
      errors.push('Timeframe cannot exceed 365 days');
    }

    // Max loss validation
    if (!goals.maxLoss || goals.maxLoss <= 0) {
      errors.push('Max loss must be greater than 0');
    }
    if (goals.maxLoss > 50) {
      errors.push('Max loss cannot exceed 50% for safety');
    }

    // Risk tolerance validation
    const validRiskLevels = ['low', 'moderate', 'high'];
    if (goals.riskTolerance && !validRiskLevels.includes(goals.riskTolerance.toLowerCase())) {
      errors.push('Risk tolerance must be low, moderate, or high');
    }

    // Symbols validation
    // ✅ ALLOW: AI_SELECT string OR array of symbols
    if (goals.symbols) {
      const isAISelect = goals.symbols === 'AI_SELECT' || 
                         (Array.isArray(goals.symbols) && goals.symbols.includes('AI_SELECT'));
      const isValidArray = Array.isArray(goals.symbols) && goals.symbols.length > 0;
      
      if (!isAISelect && !isValidArray) {
        errors.push('At least one symbol must be specified, or use "AI_SELECT" for AI-driven selection');
      }
    }

    // Logical validation: profit target should be realistic given timeframe
    const dailyTargetRate = goals.profitTarget / goals.timeframe;
    if (dailyTargetRate > 2) {
      errors.push('Daily profit target is unrealistically high (>2% per day). Consider adjusting profit target or timeframe');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * Store trading goals in database
   */
  async storeGoals(userId, configId, goals) {
    const validation = this.validateGoals(goals);
    if (!validation.isValid) {
      throw new Error(`Invalid goals: ${validation.errors.join(', ')}`);
    }

    try {
      const query = `
        INSERT INTO strategy_automations (
          user_id,
          config_id,
          name,
          profit_target_percent,
          timeframe_days,
          max_loss_percent,
          risk_tolerance,
          symbols,
          status,
          trading_mode
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
      `;

      const values = [
        userId,
        configId,
        goals.name || `Goal: ${goals.profitTarget}% in ${goals.timeframe} days`,
        goals.profitTarget,
        goals.timeframe,
        goals.maxLoss,
        (goals.riskTolerance || 'moderate').toLowerCase(),
        JSON.stringify(goals.symbols || []),
        'pending', // Will be approved after AI generates strategy
        'paper' // Default to paper mode for safety
      ];

      const result = await this.db.query(query, values);
      
      console.log('[StrategyGoals] Goals stored successfully:', {
        automationId: result.rows[0].id,
        userId,
        profitTarget: goals.profitTarget
      });

      return {
        success: true,
        automation: this.transformAutomation(result.rows[0])
      };
    } catch (error) {
      console.error('[StrategyGoals] Error storing goals:', error);
      throw new Error(`Failed to store goals: ${error.message}`);
    }
  }

  /**
   * Get all strategy automations for a user
   */
  async getUserAutomations(userId, status = null) {
    try {
      let query = `
        SELECT * FROM strategy_automations
        WHERE user_id = $1
      `;
      const params = [userId];

      if (status) {
        query += ` AND status = $2`;
        params.push(status);
      }

      query += ` ORDER BY created_at DESC`;

      const result = await this.db.query(query, params);
      
      return {
        success: true,
        automations: result.rows.map(row => this.transformAutomation(row))
      };
    } catch (error) {
      console.error('[StrategyGoals] Error fetching automations:', error);
      throw new Error(`Failed to fetch automations: ${error.message}`);
    }
  }

  /**
   * Get specific automation by ID
   */
  async getAutomation(automationId, userId = null) {
    try {
      let query = `SELECT * FROM strategy_automations WHERE id = $1`;
      const params = [automationId];

      if (userId) {
        query += ` AND user_id = $2`;
        params.push(userId);
      }

      const result = await this.db.query(query, params);
      
      if (result.rows.length === 0) {
        throw new Error('Automation not found');
      }

      return {
        success: true,
        automation: this.transformAutomation(result.rows[0])
      };
    } catch (error) {
      console.error('[StrategyGoals] Error fetching automation:', error);
      throw new Error(`Failed to fetch automation: ${error.message}`);
    }
  }

  /**
   * Update automation with AI-generated strategy
   */
  async updateWithStrategy(automationId, strategyRules, aiConfidence) {
    try {
      const query = `
        UPDATE strategy_automations
        SET strategy_rules = $1,
            ai_confidence_score = $2,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $3
        RETURNING *
      `;

      const result = await this.db.query(query, [
        JSON.stringify(strategyRules),
        aiConfidence,
        automationId
      ]);

      if (result.rows.length === 0) {
        throw new Error('Automation not found');
      }

      console.log('[StrategyGoals] Strategy attached to automation:', {
        automationId,
        aiConfidence
      });

      return {
        success: true,
        automation: this.transformAutomation(result.rows[0])
      };
    } catch (error) {
      console.error('[StrategyGoals] Error updating strategy:', error);
      throw new Error(`Failed to update strategy: ${error.message}`);
    }
  }

  /**
   * Approve a strategy automation
   */
  async approveAutomation(automationId, userId, adjustments = null) {
    try {
      // If adjustments provided, update strategy rules
      if (adjustments) {
        const getQuery = `SELECT strategy_rules FROM strategy_automations WHERE id = $1 AND user_id = $2`;
        const current = await this.db.query(getQuery, [automationId, userId]);
        
        if (current.rows.length === 0) {
          throw new Error('Automation not found');
        }

        const currentRules = current.rows[0].strategy_rules || {};
        const updatedRules = { ...currentRules, ...adjustments };

        const updateQuery = `
          UPDATE strategy_automations
          SET strategy_rules = $1,
              status = 'approved',
              approved_at = CURRENT_TIMESTAMP,
              updated_at = CURRENT_TIMESTAMP
          WHERE id = $2 AND user_id = $3
          RETURNING *
        `;

        const result = await this.db.query(updateQuery, [
          JSON.stringify(updatedRules),
          automationId,
          userId
        ]);

        return {
          success: true,
          automation: this.transformAutomation(result.rows[0])
        };
      }

      // No adjustments, just approve
      const query = `
        UPDATE strategy_automations
        SET status = 'approved',
            approved_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1 AND user_id = $2
        RETURNING *
      `;

      const result = await this.db.query(query, [automationId, userId]);

      if (result.rows.length === 0) {
        throw new Error('Automation not found');
      }

      console.log('[StrategyGoals] Automation approved:', {
        automationId,
        userId
      });

      return {
        success: true,
        automation: this.transformAutomation(result.rows[0])
      };
    } catch (error) {
      console.error('[StrategyGoals] Error approving automation:', error);
      throw new Error(`Failed to approve automation: ${error.message}`);
    }
  }

  /**
   * Reject a strategy automation
   */
  async rejectAutomation(automationId, userId, reason = null) {
    try {
      const query = `
        UPDATE strategy_automations
        SET status = 'rejected',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1 AND user_id = $2
        RETURNING *
      `;

      const result = await this.db.query(query, [automationId, userId]);

      if (result.rows.length === 0) {
        throw new Error('Automation not found');
      }

      console.log('[StrategyGoals] Automation rejected:', {
        automationId,
        userId,
        reason
      });

      return {
        success: true,
        automation: this.transformAutomation(result.rows[0])
      };
    } catch (error) {
      console.error('[StrategyGoals] Error rejecting automation:', error);
      throw new Error(`Failed to reject automation: ${error.message}`);
    }
  }

  /**
   * Transform database row to camelCase object
   */
  transformAutomation(row) {
    return {
      id: row.id,
      userId: row.user_id,
      configId: row.config_id,
      strategyId: row.strategy_id,
      name: row.name,
      profitTargetPercent: parseFloat(row.profit_target_percent),
      timeframeDays: row.timeframe_days,
      maxLossPercent: parseFloat(row.max_loss_percent),
      riskTolerance: row.risk_tolerance,
      symbols: row.symbols,
      strategyRules: row.strategy_rules,
      status: row.status,
      tradingMode: row.trading_mode,
      isActive: row.is_active,
      aiConfidenceScore: row.ai_confidence_score ? parseFloat(row.ai_confidence_score) : null,
      approvedAt: row.approved_at,
      startedAt: row.started_at,
      completedAt: row.completed_at,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }
}

module.exports = StrategyGoalsService;

