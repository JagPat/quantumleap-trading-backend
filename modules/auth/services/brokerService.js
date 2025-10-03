const BrokerConfig = require('../models/brokerConfig');
const OAuthToken = require('../models/oauthToken');
const TokenManager = require('./tokenManager');
const KiteClient = require('./kiteClient');
const SecurityManager = require('../../../core/security');

/**
 * Broker Service
 * Manages broker configurations, connection status, and real-time updates
 * Following existing service patterns in the auth module
 */
class BrokerService {
  constructor() {
    this.brokerConfig = new BrokerConfig();
    this.oauthToken = new OAuthToken();
    this.tokenManager = new TokenManager();
    this.kiteClient = new KiteClient();
    this.security = new SecurityManager();
    
    // Connection monitoring settings
    this.monitoringInterval = 5 * 60 * 1000; // 5 minutes
    this.connectionTimeout = 10000; // 10 seconds

    // Data cache (per config) to reduce API load
    this.cacheTtlMs = parseInt(process.env.BROKER_CACHE_TTL_MS || '30000', 10); // default 30s
    this.holdingsCache = new Map();
    this.positionsCache = new Map();
    this.ordersCache = new Map();
    
    // Start connection monitoring
    this.startConnectionMonitoring();
  }

  shouldTriggerReauth(error) {
    if (!error || !error.code) return false;
    const code = String(error.code).toUpperCase();
    return ['TOKEN_EXPIRED', 'TOKEN_INVALID', 'BROKER_UNAUTHORIZED', 'TOKEN_ERROR'].includes(code);
  }

  /**
   * Create or update broker configuration
   */
  async createOrUpdateConfig(userId, configData) {
    try {
      const {
        brokerName = 'zerodha',
        apiKey,
        apiSecret
      } = configData;

      // Validate credentials format
      const validation = this.kiteClient.validateCredentials(apiKey, apiSecret);
      if (!validation.valid) {
        throw new Error(validation.error);
      }

      // Check if config already exists
      let config = await this.brokerConfig.getByUserAndBroker(userId, brokerName);
      
      if (config) {
        // Check if credentials changed
        const existingCredentials = await this.brokerConfig.getCredentials(config.id);
        
        if (existingCredentials.apiKey !== apiKey || existingCredentials.apiSecret !== apiSecret) {
          // Credentials changed, revoke existing tokens and update config
          await this.tokenManager.revokeTokens(config.id, {
            userId: config.userId,
            reason: 'credentials_changed'
          });
          
          // Delete and recreate config with new credentials
          await this.brokerConfig.delete(config.id);
          config = await this.brokerConfig.create({
            userId,
            brokerName,
            apiKey,
            apiSecret
          });
        }
      } else {
        config = await this.brokerConfig.create({
          userId,
          brokerName,
          apiKey,
          apiSecret
        });
      }

      return {
        success: true,
        config: config,
        message: config ? 'Broker configuration updated' : 'Broker configuration created'
      };

    } catch (error) {
      throw new Error(`Failed to create/update broker configuration: ${error.message}`);
    }
  }

  /**
   * Generate broker session using request token
   */
  async generateBrokerSession({ requestToken, apiKey, apiSecret, userId, originalUserId = null, configId = null }) {
    if (!requestToken || !apiKey || !apiSecret) {
      throw new Error('Request token, API key, and API secret are required');
    }

    let targetConfig = null;

    if (configId) {
      targetConfig = await this.brokerConfig.getById(configId);
      if (!targetConfig) {
        throw new Error('Broker configuration not found');
      }

      await this.createOrUpdateConfig(targetConfig.userId, {
        brokerName: targetConfig.brokerName || 'zerodha',
        apiKey,
        apiSecret
      });

      targetConfig = await this.brokerConfig.getById(configId);
    } else {
      if (!userId) {
        throw new Error('User identifier is required to create broker configuration');
      }

      const upsertResult = await this.createOrUpdateConfig(userId, {
        brokerName: 'zerodha',
        apiKey,
        apiSecret
      });

      targetConfig = upsertResult.config || await this.brokerConfig.getByUserAndBroker(userId, 'zerodha');
    }

    if (!targetConfig) {
      throw new Error('Failed to prepare broker configuration');
    }

    const sessionResponse = await this.kiteClient.generateSession(requestToken, apiKey, apiSecret);

    if (!sessionResponse.success) {
      throw new Error(sessionResponse.message || 'Failed to generate broker session');
    }

    await this.tokenManager.storeTokens(targetConfig.id, {
      accessToken: sessionResponse.accessToken,
      refreshToken: sessionResponse.refreshToken,
      expiresIn: sessionResponse.expiresIn,
      userId: targetConfig.userId,
      brokerUserId: sessionResponse.userId,
      scope: {
        userData: {
          user_id: sessionResponse.userId,
          user_type: sessionResponse.userType,
          user_shortname: sessionResponse.userShortname,
          avatar_url: sessionResponse.avatarUrl,
          broker: sessionResponse.broker,
          exchanges: sessionResponse.exchanges,
          products: sessionResponse.products,
          order_types: sessionResponse.orderTypes
        }
      },
      source: 'user_login'
    });

    await this.brokerConfig.updateConnectionStatus(targetConfig.id, {
      state: 'connected',
      message: 'Broker session established',
      lastChecked: new Date().toISOString()
    });

    const userData = {
      user_id: sessionResponse.userId,
      user_type: sessionResponse.userType,
      user_shortname: sessionResponse.userShortname,
      avatar_url: sessionResponse.avatarUrl,
      broker: sessionResponse.broker,
      exchanges: sessionResponse.exchanges,
      products: sessionResponse.products,
      order_types: sessionResponse.orderTypes
    };

    return {
      status: 'success',
      config_id: targetConfig.id,
      user_id: targetConfig.userId,
      original_user_id: originalUserId,
      access_token: sessionResponse.accessToken,
      refresh_token: sessionResponse.refreshToken,
      user_data: userData
    };
  }

  async resolveConfig({ normalizedUserId = null, originalUserId = null, configId = null }) {
    if (configId) {
      const config = await this.brokerConfig.getById(configId);
      if (config) return config;
    }

    const candidateIds = [normalizedUserId, originalUserId].filter(Boolean);
    for (const candidate of candidateIds) {
      const config = await this.brokerConfig.getByUserAndBroker(candidate, 'zerodha');
      if (config) return config;
    }

    throw new Error('Broker configuration not found for provided user');
  }

  getCacheEntry(cache, key, bypassCache = false) {
    if (bypassCache) {
      cache.delete(key);
      return null;
    }

    const entry = cache.get(key);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > this.cacheTtlMs) {
      cache.delete(key);
      return null;
    }
    return entry;
  }

  setCacheEntry(cache, key, data) {
    cache.set(key, {
      timestamp: Date.now(),
      data
    });
  }

  normalizeHolding(raw) {
    const tradingsymbol = raw.tradingsymbol || raw.symbol;
    const quantity = Number(raw.quantity || 0);
    const lastPrice = Number(raw.lastPrice || raw.last_price || 0);
    const averagePrice = Number(raw.averagePrice || raw.average_price || 0);
    const closePrice = Number(raw.closePrice || raw.close_price || 0);
    const pnl = Number(raw.pnl || 0);
    const dayChange = Number(raw.dayChange || raw.day_change || 0);
    const dayChangePercent = Number(raw.dayChangePercentage || raw.day_change_percentage || 0);
    const averageCost = Number(quantity * averagePrice);
    const currentValue = Number(quantity * lastPrice);
    const pnlPercentage = averageCost !== 0 ? Number((pnl / averageCost) * 100) : 0;

    return {
      tradingsymbol,
      symbol: tradingsymbol,
      name: raw.name || tradingsymbol,
      exchange: raw.exchange,
      instrument_token: raw.instrumentToken,
      isin: raw.isin,
      product: raw.product,
      quantity,
      t1_quantity: raw.t1Quantity,
      average_price: averagePrice,
      last_price: lastPrice,
      close_price: closePrice,
      value: currentValue,
      current_value: currentValue,
      average_cost: averageCost,
      pnl,
      pnl_percent: pnlPercentage,
      pnl_percentage: pnlPercentage,
      day_change: dayChange,
      day_change_percent: dayChangePercent,
      day_change_percentage: dayChangePercent,
      source: 'holdings'
    };
  }

  normalizePosition(raw) {
    const tradingsymbol = raw.tradingsymbol || raw.symbol;
    const quantity = Number(raw.quantity || raw.net_quantity || 0);
    const netQuantity = Number(raw.net_quantity ?? quantity);
    const lastPrice = Number(raw.last_price || raw.lastPrice || 0);
    const averagePrice = Number(raw.average_price || raw.averagePrice || 0);
    const pnl = Number(raw.pnl || raw.unrealised || 0);
    const realised = Number(raw.realised || 0);
    const unrealised = Number(raw.unrealised || 0);
    const dayPnl = Number(raw.day_pnl || raw.day_change || 0);
    const dayChange = Number(raw.day_change || raw.day_pnl || 0);
    const dayChangePercent = Number(raw.day_change_percentage || raw.day_change_percent || 0);
    const currentValue = Number(netQuantity * lastPrice);
    const averageCost = Number(netQuantity * averagePrice);
    const pnlPercentage = averageCost !== 0 ? Number((pnl / averageCost) * 100) : 0;

    return {
      tradingsymbol,
      symbol: tradingsymbol,
      exchange: raw.exchange,
      instrument_token: raw.instrument_token,
      product: raw.product,
      quantity,
      net_quantity: netQuantity,
      average_price: averagePrice,
      last_price: lastPrice,
      value: currentValue,
      current_value: currentValue,
      average_cost: averageCost,
      pnl,
      pnl_percent: pnlPercentage,
      pnl_percentage: pnlPercentage,
      realised,
      unrealised,
      day_pnl: dayPnl,
      day_change: dayChange,
      day_change_percent: dayChangePercent,
      day_change_percentage: dayChangePercent,
      m2m: Number(raw.m2m || 0),
      multiplier: Number(raw.multiplier || 1),
      overnight_quantity: Number(raw.overnight_quantity || 0),
      buy_quantity: Number(raw.buy_quantity || 0),
      sell_quantity: Number(raw.sell_quantity || 0),
      type: raw.product,
      source: 'positions'
    };
  }

  normalizeOrder(raw) {
    const filledQuantity = Number(raw.filled_quantity || 0);
    const quantity = Number(raw.quantity || 0);
    const pendingQuantity = Number(raw.pending_quantity || quantity - filledQuantity);
    return {
      order_id: raw.order_id,
      parent_order_id: raw.parent_order_id,
      status: raw.status,
      status_message: raw.status_message_raw || raw.status_message,
      tradingsymbol: raw.tradingsymbol,
      symbol: raw.tradingsymbol,
      instrument_token: raw.instrument_token,
      exchange: raw.exchange,
      transaction_type: raw.transaction_type,
      side: raw.transaction_type,
      product: raw.product,
      quantity,
      filled_quantity: filledQuantity,
      pending_quantity: pendingQuantity,
      disclosed_quantity: Number(raw.disclosed_quantity || 0),
      price: Number(raw.price || 0),
      trigger_price: Number(raw.trigger_price || 0),
      average_price: Number(raw.average_price || 0),
      order_type: raw.order_type,
      validity: raw.validity,
      placed_by: raw.placed_by,
      timestamp: raw.order_timestamp || raw.exchange_timestamp,
      order_timestamp: raw.order_timestamp || raw.exchange_timestamp,
      exchange_timestamp: raw.exchange_timestamp,
      tag: raw.tag
    };
  }

  normalizeKiteError(error, context = 'broker request') {
    const message = error?.message || 'Unknown broker error';
    const normalized = message.toLowerCase();
    const err = new Error(message.startsWith('[Broker]') ? message : `[Broker] ${context}: ${message}`);

    if (normalized.includes('token') && normalized.includes('expire')) {
      err.code = 'TOKEN_EXPIRED';
    } else if (normalized.includes('token') && normalized.includes('invalid')) {
      err.code = 'TOKEN_INVALID';
    } else if (normalized.includes('unauthorized') || normalized.includes('forbidden')) {
      err.code = 'BROKER_UNAUTHORIZED';
    } else if (normalized.includes('rate limit')) {
      err.code = 'RATE_LIMIT';
    } else {
      err.code = 'BROKER_ERROR';
    }

    err.original = error;
    return err;
  }

  async getHoldingsData({ normalizedUserId = null, originalUserId = null, configId = null, bypassCache = false } = {}) {
    const config = await this.resolveConfig({ normalizedUserId, originalUserId, configId });
    const cacheKey = config.id;
    const cached = this.getCacheEntry(this.holdingsCache, cacheKey, bypassCache);
    if (cached) {
      console.info('[Broker][DataFetch] Using cached holdings', { configId: cacheKey });
      return { ...cached.data, cached: true };
    }

    console.info('[Broker][DataFetch] Fetching holdings from Zerodha', { configId: cacheKey, bypassCache });

    try {
      let accessToken;
      try {
        accessToken = await this.tokenManager.getValidAccessToken(config.id);
      } catch (tokenError) {
        await this.tokenManager.flagReauthRequired(config.id, 'token_error', tokenError.message);
        const err = new Error('Unable to retrieve valid access token');
        err.code = 'TOKEN_ERROR';
        err.needs_reauth = true;
        throw err;
      }
      const credentials = await this.brokerConfig.getCredentials(config.id);
      const result = await this.kiteClient.getHoldings(accessToken, credentials.apiKey);

      if (!result.success) {
        const error = new Error(result.message || 'Failed to fetch holdings from broker');
        error.code = result.code || 'BROKER_ERROR';
        if (this.shouldTriggerReauth(error)) {
          await this.tokenManager.flagReauthRequired(config.id, error.code.toLowerCase(), error.message);
          error.needs_reauth = true;
        }
        throw error;
      }

      const holdings = result.holdings.map(h => this.normalizeHolding(h));
      const payload = {
        holdings,
        lastUpdated: new Date().toISOString()
      };

      this.setCacheEntry(this.holdingsCache, cacheKey, payload);
      return { ...payload, cached: false };
    } catch (error) {
      throw error?.code ? error : this.normalizeKiteError(error, 'holdings fetch failed');
    }
  }

  async getPositionsData({ normalizedUserId = null, originalUserId = null, configId = null, bypassCache = false } = {}) {
    const config = await this.resolveConfig({ normalizedUserId, originalUserId, configId });
    const cacheKey = config.id;
    const cached = this.getCacheEntry(this.positionsCache, cacheKey, bypassCache);
    if (cached) {
      console.info('[Broker][DataFetch] Using cached positions', { configId: cacheKey });
      return { ...cached.data, cached: true };
    }

    console.info('[Broker][DataFetch] Fetching positions from Zerodha', { configId: cacheKey, bypassCache });

    try {
      let accessToken;
      try {
        accessToken = await this.tokenManager.getValidAccessToken(config.id);
      } catch (tokenError) {
        await this.tokenManager.flagReauthRequired(config.id, 'token_error', tokenError.message);
        const err = new Error('Unable to retrieve valid access token');
        err.code = 'TOKEN_ERROR';
        err.needs_reauth = true;
        throw err;
      }
      const credentials = await this.brokerConfig.getCredentials(config.id);
      const result = await this.kiteClient.getPositions(accessToken, credentials.apiKey);

      if (!result.success) {
        const error = new Error(result.message || 'Failed to fetch positions from broker');
        error.code = result.code || 'BROKER_ERROR';
        if (this.shouldTriggerReauth(error)) {
          await this.tokenManager.flagReauthRequired(config.id, error.code.toLowerCase(), error.message);
          error.needs_reauth = true;
        }
        throw error;
      }

      const netPositions = (result.positions.net || []).map(p => this.normalizePosition(p));
      const dayPositions = (result.positions.day || []).map(p => this.normalizePosition(p));
      const payload = {
        positions: {
          net: netPositions,
          day: dayPositions
        },
        lastUpdated: new Date().toISOString()
      };

      this.setCacheEntry(this.positionsCache, cacheKey, payload);
      return { ...payload, cached: false };
    } catch (error) {
      throw error?.code ? error : this.normalizeKiteError(error, 'positions fetch failed');
    }
  }

  async getOrdersData({ normalizedUserId = null, originalUserId = null, configId = null, bypassCache = false } = {}) {
    const config = await this.resolveConfig({ normalizedUserId, originalUserId, configId });
    const cacheKey = config.id;
    const cached = this.getCacheEntry(this.ordersCache, cacheKey, bypassCache);
    if (cached) {
      console.info('[Broker][DataFetch] Using cached orders', { configId: cacheKey });
      return { ...cached.data, cached: true };
    }

    console.info('[Broker][DataFetch] Fetching orders from Zerodha', { configId: cacheKey, bypassCache });

    try {
      let accessToken;
      try {
        accessToken = await this.tokenManager.getValidAccessToken(config.id);
      } catch (tokenError) {
        await this.tokenManager.flagReauthRequired(config.id, 'token_error', tokenError.message);
        const err = new Error('Unable to retrieve valid access token');
        err.code = 'TOKEN_ERROR';
        err.needs_reauth = true;
        throw err;
      }
      const credentials = await this.brokerConfig.getCredentials(config.id);
      const result = await this.kiteClient.getOrders(accessToken, credentials.apiKey);

      if (!result.success) {
        const error = new Error(result.message || 'Failed to fetch orders from broker');
        error.code = result.code || 'BROKER_ERROR';
        if (this.shouldTriggerReauth(error)) {
          await this.tokenManager.flagReauthRequired(config.id, error.code.toLowerCase(), error.message);
          error.needs_reauth = true;
        }
        throw error;
      }

      const orders = (result.orders || []).map(o => this.normalizeOrder(o));
      const payload = {
        orders,
        lastUpdated: new Date().toISOString()
      };

      this.setCacheEntry(this.ordersCache, cacheKey, payload);
      return { ...payload, cached: false };
    } catch (error) {
      throw error?.code ? error : this.normalizeKiteError(error, 'orders fetch failed');
    }
  }

  async getPortfolioSnapshot({ normalizedUserId = null, originalUserId = null, configId = null, bypassCache = false } = {}) {
    try {
      const config = await this.resolveConfig({ normalizedUserId, originalUserId, configId });
      const holdingsData = await this.getHoldingsData({ normalizedUserId, originalUserId, configId: config.id, bypassCache });
      const positionsData = await this.getPositionsData({ normalizedUserId, originalUserId, configId: config.id, bypassCache });
      let ordersData = null;

      try {
        ordersData = await this.getOrdersData({ normalizedUserId, originalUserId, configId: config.id, bypassCache });
      } catch (error) {
        console.warn('[Broker][DataFetch] Orders fetch failed:', { message: error.message, code: error.code });
        if (error?.code && ['TOKEN_EXPIRED', 'TOKEN_INVALID', 'BROKER_UNAUTHORIZED'].includes(error.code)) {
          throw error;
        }
      }

      const holdings = holdingsData.holdings;
      const netPositions = positionsData.positions.net;

      const holdingsValue = holdings.reduce((sum, item) => sum + (item.value || 0), 0);
      const holdingsDayPnl = holdings.reduce((sum, item) => sum + (item.day_change || 0), 0);
      const holdingsTotalPnl = holdings.reduce((sum, item) => sum + (item.pnl || 0), 0);
      const holdingsCost = holdings.reduce((sum, item) => sum + (item.average_cost || 0), 0);

      const positionsValue = netPositions.reduce((sum, item) => sum + (item.value || 0), 0);
      const positionsDayPnl = netPositions.reduce((sum, item) => sum + (item.day_pnl || 0), 0);
      const positionsTotalPnl = netPositions.reduce((sum, item) => sum + (item.pnl || 0), 0);
      const positionsCost = netPositions.reduce((sum, item) => sum + ((item.average_price || 0) * (item.net_quantity || item.quantity || 0)), 0);

      const currentValue = holdingsValue + positionsValue;
      const totalPnl = holdingsTotalPnl + positionsTotalPnl;
      const dayPnl = holdingsDayPnl + positionsDayPnl;
      const totalInvestment = holdingsCost + positionsCost;

      const summary = {
        total_value: currentValue,
        current_value: currentValue,
        holdings_value: holdingsValue,
        positions_value: positionsValue,
        total_investment: totalInvestment,
        day_pnl: dayPnl,
        total_pnl: totalPnl,
        day_change_percent: currentValue ? (dayPnl / currentValue) * 100 : 0,
        total_pnl_percent: totalInvestment ? (totalPnl / totalInvestment) * 100 : 0,
        holdings_count: holdings.length,
        positions_count: netPositions.length,
        last_updated: [holdingsData.lastUpdated, positionsData.lastUpdated].filter(Boolean).sort().slice(-1)[0] || new Date().toISOString()
      };

      let tokenStatus = null;
      try {
        tokenStatus = await this.oauthToken.getTokenStatus(config.id);
      } catch (statusError) {
        console.warn('[Broker][DataFetch] Token status lookup failed:', statusError.message);
      }

      return {
        summary,
        holdings,
        positions: positionsData.positions.net,
        intraday_positions: positionsData.positions.day,
        orders: ordersData ? ordersData.orders : [],
        lastUpdated: summary.last_updated,
        session: {
          configId: config.id,
          needsReauth: config.needsReauth || tokenStatus?.needsReauth || false,
          sessionStatus: config.sessionStatus,
          tokenStatus,
          lastTokenRefresh: config.lastTokenRefresh,
          lastStatusCheck: config.lastStatusCheck,
          connectionStatus: config.connectionStatus
        },
        cache: {
          holdingsCached: holdingsData.cached,
          positionsCached: positionsData.cached,
          ordersCached: ordersData ? ordersData.cached : false,
          ttlMs: this.cacheTtlMs
        }
      };
    } catch (error) {
      throw error?.code ? error : this.normalizeKiteError(error, 'portfolio snapshot failed');
    }
  }

  /**
   * Update access token provided by automation (e.g., Selenium + TOTP jobs)
   */
  async updateAccessTokenFromAutomation({ normalizedUserId = null, originalUserId = null, accessToken, expiresIn = null, expiresAt = null, source = 'automation' }) {
    if (!accessToken) {
      throw new Error('Access token is required');
    }

    const candidateUserIds = [normalizedUserId, originalUserId].filter(Boolean);
    if (candidateUserIds.length === 0) {
      throw new Error('User identifier is required');
    }

    let config = null;
    for (const candidate of candidateUserIds) {
      config = await this.brokerConfig.getByUserAndBroker(candidate, 'zerodha');
      if (config) {
        break;
      }
    }

    if (!config) {
      throw new Error('Broker configuration not found for provided user');
    }

    let computedExpiresIn = Number(expiresIn);

    if ((!computedExpiresIn || !Number.isFinite(computedExpiresIn) || computedExpiresIn <= 0) && expiresAt) {
      const expiryDate = new Date(expiresAt);
      if (!Number.isNaN(expiryDate.getTime())) {
        computedExpiresIn = Math.floor((expiryDate.getTime() - Date.now()) / 1000);
      }
    }

    if (!computedExpiresIn || !Number.isFinite(computedExpiresIn) || computedExpiresIn <= 0) {
      computedExpiresIn = 24 * 60 * 60; // default to 24 hours
    }

    // Ensure we always have at least 15 minutes to account for buffer subtraction
    computedExpiresIn = Math.max(computedExpiresIn, 900);

    await this.tokenManager.storeTokens(config.id, {
      accessToken,
      refreshToken: null,
      expiresIn: computedExpiresIn,
      userId: config.userId,
      scope: { source: source || 'automation' }
    });

    const computedExpiresAt = new Date(Date.now() + computedExpiresIn * 1000);
    console.info('[Auth][Broker] Access token updated', {
      configId: config.id,
      userId: config.userId,
      source: source || 'automation',
      expiresAt: computedExpiresAt.toISOString(),
      expiresIn: computedExpiresIn
    });

    await this.brokerConfig.updateConnectionStatus(config.id, {
      state: 'connected',
      message: `Access token updated via ${source || 'automation'}`,
      lastChecked: new Date().toISOString()
    });

    return {
      config_id: config.id,
      user_id: config.userId,
      expires_in: computedExpiresIn,
      expires_at: computedExpiresAt.toISOString()
    };
  }

  /**
   * Retrieve token metadata for administrative inspection
   */
  async getTokenMetadata({ normalizedUserId = null, originalUserId = null, configId = null }) {
    let config = null;

    if (configId) {
      config = await this.brokerConfig.getById(configId);
    }

    if (!config) {
      const candidateIds = [normalizedUserId, originalUserId].filter(Boolean);
      for (const candidate of candidateIds) {
        config = await this.brokerConfig.getByUserAndBroker(candidate, 'zerodha');
        if (config) {
          break;
        }
      }
    }

    if (!config) {
      throw new Error('Broker configuration not found for supplied identifiers');
    }

    const tokenRecord = await this.oauthToken.getByConfigId(config.id);
    const tokenStatus = await this.oauthToken.getTokenStatus(config.id);

    return {
      config_id: config.id,
      user_id: config.userId,
      token_present: !!tokenRecord,
      expires_at: tokenRecord?.expiresAt || null,
      updated_at: tokenRecord?.updatedAt || null,
      source: tokenRecord?.scope?.source || null,
      status: tokenStatus?.status || 'unknown'
    };
  }

  /**
   * Get broker configuration by user ID
   */
  async getConfigByUser(userId, brokerName = 'zerodha') {
    try {
      const config = await this.brokerConfig.getByUserAndBroker(userId, brokerName);
      
      if (!config) {
        return {
          success: true,
          config: null,
          message: 'No broker configuration found'
        };
      }

      // Get token status
      const tokenStatus = await this.oauthToken.getTokenStatus(config.id);
      
      // Get connection validation
      const connectionStatus = await this.validateConnection(config.id);

      return {
        success: true,
        config: {
          ...config,
          tokenStatus,
          connectionValidation: connectionStatus
        }
      };

    } catch (error) {
      throw new Error(`Failed to get broker configuration: ${error.message}`);
    }
  }

  /**
   * Get all configurations for a user
   */
  async getAllConfigsByUser(userId) {
    try {
      const configs = await this.brokerConfig.getByUserId(userId);
      
      // Enhance each config with token and connection status
      const enhancedConfigs = await Promise.all(
        configs.map(async (config) => {
          try {
            const tokenStatus = await this.oauthToken.getTokenStatus(config.id);
            const connectionStatus = await this.validateConnection(config.id);
            
            return {
              ...config,
              tokenStatus,
              connectionValidation: connectionStatus
            };
          } catch (error) {
            return {
              ...config,
              tokenStatus: { status: 'error', error: error.message },
              connectionValidation: { valid: false, error: error.message }
            };
          }
        })
      );

      return {
        success: true,
        configs: enhancedConfigs,
        count: enhancedConfigs.length
      };

    } catch (error) {
      throw new Error(`Failed to get broker configurations: ${error.message}`);
    }
  }

  /**
   * Validate broker connection
   */
  async validateConnection(configId) {
    try {
      // Check if we have valid tokens
      const tokenValidation = await this.tokenManager.validateToken(configId);
      
      if (!tokenValidation.valid) {
        return {
          valid: false,
          status: tokenValidation.status,
          message: tokenValidation.message,
          canReconnect: tokenValidation.status === 'expired' || tokenValidation.status === 'expiring_soon'
        };
      }

      // Test actual API connection
      const accessToken = await this.tokenManager.getValidAccessToken(configId);
      const credentials = await this.brokerConfig.getCredentials(configId);
      
      let connectionTest = await this.kiteClient.testConnection(accessToken, credentials.apiKey);
      let autoRefreshAttempted = false;

      if (!connectionTest.success && connectionTest.code === 'INVALID_TOKEN') {
        console.warn(`[BrokerService] Token invalid for config ${configId}. Attempting automated refresh.`);
        await this.brokerConfig.updateConnectionStatus(configId, {
          state: 'refreshing',
          message: 'Access token invalidated. Attempting automatic refresh…',
          lastChecked: new Date().toISOString()
        });

        autoRefreshAttempted = true;
        const refreshResult = await this.tokenManager.refreshTokens(configId);
        if (refreshResult.success) {
          try {
            const refreshedAccessToken = await this.tokenManager.getValidAccessToken(configId);
            connectionTest = await this.kiteClient.testConnection(refreshedAccessToken, credentials.apiKey);
            console.info(`[BrokerService] Auto-refresh succeeded for config ${configId}`);
          } catch (autoRefreshError) {
            console.error(`[BrokerService] Auto-refresh validation failed for config ${configId}:`, autoRefreshError);
            connectionTest = {
              success: false,
              connected: false,
              error: autoRefreshError.message,
              code: 'AUTO_REFRESH_FAILED',
              message: 'Automatic token refresh failed'
            };
          }
        } else {
          console.error(`[BrokerService] Token refresh failed for config ${configId}:`, refreshResult.error);
          return {
            valid: false,
            status: 'token_invalid',
            error: refreshResult.error || connectionTest.error,
            message: refreshResult.message || 'Token refresh failed',
            canReconnect: true,
            autoRefreshAttempted: true
          };
        }
      }

      if (connectionTest.success) {
        await this.brokerConfig.updateConnectionStatus(configId, {
          state: 'connected',
          message: 'Connection validated successfully',
          lastChecked: new Date().toISOString()
        });

        return {
          valid: true,
          status: 'connected',
          userId: connectionTest.userId,
          message: 'Connection is active and healthy',
          lastChecked: new Date().toISOString(),
          autoRefreshAttempted
        };
      }

      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'error',
        message: `Connection test failed: ${connectionTest.error}`,
        lastChecked: new Date().toISOString()
      });

      return {
        valid: false,
        status: connectionTest.code === 'INVALID_TOKEN' ? 'token_invalid' : 'connection_failed',
        error: connectionTest.error,
        message: connectionTest.message || 'Connection test failed',
        canReconnect: true,
        autoRefreshAttempted
      };

    } catch (error) {
      // Update connection status
      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'error',
        message: `Validation error: ${error.message}`,
        lastChecked: new Date().toISOString()
      });

      return {
        valid: false,
        status: 'validation_error',
        error: error.message,
        message: 'Connection validation failed',
        canReconnect: true
      };
    }
  }

  /**
   * Reconnect broker (refresh tokens and validate)
   */
  async reconnectBroker(configId) {
    try {
      // Try to refresh tokens
      const refreshResult = await this.tokenManager.refreshTokens(configId);
      
      if (!refreshResult.success) {
        return {
          success: false,
          error: refreshResult.error,
          message: 'Token refresh failed - manual re-authentication required'
        };
      }

      // Validate the new connection
      const connectionStatus = await this.validateConnection(configId);
      
      if (connectionStatus.valid) {
        return {
          success: true,
          message: 'Broker reconnected successfully',
          connectionStatus
        };
      } else {
        return {
          success: false,
          error: connectionStatus.error,
          message: 'Reconnection failed - manual re-authentication may be required'
        };
      }

    } catch (error) {
      throw new Error(`Reconnection failed: ${error.message}`);
    }
  }

  /**
   * Disconnect broker
   */
  async disconnectBroker(configId) {
    try {
      const result = await this.tokenManager.revokeTokens(configId);
      
      return {
        success: true,
        message: 'Broker disconnected successfully',
        deletedTokens: result.deletedTokens
      };

    } catch (error) {
      throw new Error(`Disconnect failed: ${error.message}`);
    }
  }

  /**
   * Delete broker configuration
   */
  async deleteConfig(configId, userId) {
    try {
      // Verify ownership
      const config = await this.brokerConfig.getById(configId);
      if (!config) {
        throw new Error('Broker configuration not found');
      }

      if (config.userId !== userId) {
        throw new Error('Unauthorized: Configuration belongs to different user');
      }

      // Disconnect first (this will revoke tokens)
      await this.disconnectBroker(configId);

      // Delete configuration
      const deleted = await this.brokerConfig.delete(configId);
      
      if (!deleted) {
        throw new Error('Failed to delete broker configuration');
      }

      return {
        success: true,
        message: 'Broker configuration deleted successfully'
      };

    } catch (error) {
      throw new Error(`Failed to delete configuration: ${error.message}`);
    }
  }

  /**
   * Get real-time connection status
   */
  async getConnectionStatus(configId) {
    try {
      const config = await this.brokerConfig.getById(configId);
      if (!config) {
        return {
          success: false,
          error: 'Configuration not found'
        };
      }

      const tokenStatus = await this.oauthToken.getTokenStatus(config.id);
      const tokenExpiry = tokenStatus.expiresAt || null;
      const needsReauth = config.needsReauth || tokenStatus.needsReauth;

      // Fetch token record to get user_id and access_token
      const tokenRecord = await this.oauthToken.getByConfigId(config.id);
      let userId = null;
      let accessToken = null;
      
      if (tokenRecord) {
        userId = tokenRecord.userId || null;
        
        // Decrypt access_token if available
        try {
          if (tokenRecord.accessTokenEncrypted) {
            accessToken = this.security.decrypt(tokenRecord.accessTokenEncrypted);
          }
        } catch (decryptError) {
          console.warn('[BrokerService] Failed to decrypt access_token:', decryptError.message);
        }
      }

      return {
        success: true,
        status: {
          configId: config.id,
          isConnected: config.isConnected,
          connectionStatus: config.connectionStatus,
          tokenStatus: tokenStatus,
          tokenExpiry: tokenExpiry,
          lastSync: config.lastSync,
          brokerName: config.brokerName,
          sessionStatus: config.sessionStatus,
          lastTokenRefresh: config.lastTokenRefresh,
          needsReauth,
          userId: userId,              // ✅ Include user_id
          user_id: userId,             // ✅ Include snake_case for frontend compatibility
          accessToken: accessToken,    // ✅ Include access_token for broker API calls
          access_token: accessToken    // ✅ Include snake_case for frontend compatibility
        }
      };

    } catch (error) {
      throw new Error(`Failed to get connection status: ${error.message}`);
    }
  }

  /**
   * Get active connections overview
   */
  async getActiveConnections() {
    try {
      const activeConnections = await this.brokerConfig.getActiveConnections();
      
      return {
        success: true,
        connections: activeConnections,
        count: activeConnections.length,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      throw new Error(`Failed to get active connections: ${error.message}`);
    }
  }

  /**
   * Background connection monitoring
   */
  startConnectionMonitoring() {
    setInterval(async () => {
      try {
        console.log('🔍 Running connection health check...');
        
        const activeConnections = await this.brokerConfig.getActiveConnections();
        
        if (activeConnections.length === 0) {
          console.log('✅ No active connections to monitor');
          return;
        }

        console.log(`🔍 Monitoring ${activeConnections.length} active connections`);

        for (const connection of activeConnections) {
          try {
            const validation = await this.validateConnection(connection.id);
            
            if (validation.valid) {
              console.log(`✅ Connection ${connection.id} is healthy`);
            } else {
              console.warn(`⚠️ Connection ${connection.id} has issues: ${validation.message}`);
              
              // Try to reconnect if possible
              if (validation.canReconnect) {
                console.log(`🔄 Attempting to reconnect ${connection.id}...`);
                const reconnectResult = await this.reconnectBroker(connection.id);
                
                if (reconnectResult.success) {
                  console.log(`✅ Successfully reconnected ${connection.id}`);
                } else {
                  console.error(`❌ Failed to reconnect ${connection.id}: ${reconnectResult.error}`);
                }
              }
            }

          } catch (error) {
            console.error(`❌ Error monitoring connection ${connection.id}:`, error);
          }
        }

        console.log('🔍 Connection health check completed');

      } catch (error) {
        console.error('❌ Connection monitoring job failed:', error);
      }
    }, this.monitoringInterval);

    console.log(`🔍 Connection monitoring started (interval: ${this.monitoringInterval / 1000 / 60} minutes)`);
  }

  /**
   * Get broker service statistics
   */
  async getServiceStats() {
    try {
      const configHealth = await this.brokerConfig.healthCheck();
      const tokenStats = await this.tokenManager.getTokenStats();
      const activeConnections = await this.getActiveConnections();

      return {
        success: true,
        stats: {
          totalConfigs: configHealth.configCount,
          activeConnections: activeConnections.count,
          tokenStats: tokenStats.stats,
          healthStatus: 'operational'
        },
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      throw new Error(`Failed to get service stats: ${error.message}`);
    }
  }

  /**
   * Health check for broker service
   */
  async healthCheck() {
    try {
      const configHealth = await this.brokerConfig.healthCheck();
      const tokenHealth = await this.tokenManager.healthCheck();
      const kiteHealth = await this.kiteClient.healthCheck();

      return {
        status: 'healthy',
        brokerService: 'operational',
        components: {
          brokerConfigs: configHealth,
          tokenManager: tokenHealth,
          kiteClient: kiteHealth
        },
        monitoring: 'active',
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      return {
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }
}

module.exports = BrokerService;
