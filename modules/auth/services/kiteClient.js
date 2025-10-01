const SecurityManager = require('../../../core/security');

/**
 * Zerodha Kite Connect API Client
 * Handles OAuth flow and API communication with Zerodha Kite Connect
 * Following existing service patterns in the auth module
 */
class KiteClient {
  constructor() {
    this.security = new SecurityManager();
    this.baseUrl = process.env.ZERODHA_API_BASE_URL || 'https://api.kite.trade';
    this.loginUrl = process.env.ZERODHA_LOGIN_URL || 'https://kite.zerodha.com/connect/login';
  }

  /**
   * Create KiteConnect instance
   */
  createKiteInstance(apiKey, accessToken = null) {
    const config = {
      api_key: apiKey,
      debug: process.env.NODE_ENV === 'development'
    };

    if (accessToken) {
      config.access_token = accessToken;
    }

    // Lazy-load to avoid adding kiteconnect to cold-start path
    // eslint-disable-next-line global-require
    const { KiteConnect } = require('kiteconnect');
    return new KiteConnect(config);
  }

  /**
   * Generate OAuth URL for Zerodha authentication
   */
  generateOAuthUrl(apiKey, state, redirectUri = null) {
    try {
      // Validate inputs
      if (!apiKey || !state) {
        throw new Error('API key and state are required');
      }

      // Build OAuth URL
      const params = new URLSearchParams({
        api_key: apiKey,
        v: '3', // Kite Connect version
        state: state
      });

      const oauthUrl = `${this.loginUrl}?${params.toString()}`;

      return {
        success: true,
        oauthUrl,
        state,
        expiresIn: 300 // OAuth state expires in 5 minutes
      };

    } catch (error) {
      throw new Error(`Failed to generate OAuth URL: ${error.message}`);
    }
  }

  /**
   * Exchange request token for access token
   */
  async generateSession(requestToken, apiKey, apiSecret) {
    try {
      // Validate inputs
      if (!requestToken || !apiKey || !apiSecret) {
        throw new Error('Request token, API key, and API secret are required');
      }

      // Create KiteConnect instance
      const kc = this.createKiteInstance(apiKey);

      // Generate session
      const sessionData = await kc.generateSession(requestToken, apiSecret);

      // Validate response
      if (!sessionData.access_token) {
        throw new Error('Invalid session response from Zerodha');
      }

      return {
        success: true,
        accessToken: sessionData.access_token,
        refreshToken: sessionData.refresh_token,
        userId: sessionData.user_id,
        userType: sessionData.user_type,
        userShortname: sessionData.user_shortname,
        avatarUrl: sessionData.avatar_url,
        broker: sessionData.broker,
        exchanges: sessionData.exchanges,
        products: sessionData.products,
        orderTypes: sessionData.order_types,
        expiresIn: 86400 // 24 hours for Zerodha tokens
      };

    } catch (error) {
      // Handle specific Kite Connect errors
      if (error.message.includes('Invalid API credentials')) {
        throw new Error('Invalid API credentials provided');
      } else if (error.message.includes('Invalid request token')) {
        throw new Error('Invalid or expired request token');
      } else if (error.message.includes('ENOTFOUND') || error.message.includes('ECONNREFUSED')) {
        throw new Error('Unable to connect to Zerodha servers');
      }

      throw new Error(`Session generation failed: ${error.message}`);
    }
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshAccessToken(refreshToken, apiKey, apiSecret) {
    try {
      // Validate inputs
      if (!refreshToken || !apiKey || !apiSecret) {
        throw new Error('Refresh token, API key, and API secret are required');
      }

      // Create KiteConnect instance
      const kc = this.createKiteInstance(apiKey);

      // Refresh token
      const tokenData = await kc.renewAccessToken(refreshToken, apiSecret);

      // Validate response
      if (!tokenData.access_token) {
        throw new Error('Invalid token refresh response from Zerodha');
      }

      return {
        success: true,
        accessToken: tokenData.access_token,
        refreshToken: tokenData.refresh_token,
        expiresIn: 86400 // 24 hours
      };

    } catch (error) {
      // Handle specific refresh errors
      if (error.message.includes('Invalid refresh token')) {
        throw new Error('Invalid or expired refresh token');
      } else if (error.message.includes('Invalid API credentials')) {
        throw new Error('Invalid API credentials for token refresh');
      }

      throw new Error(`Token refresh failed: ${error.message}`);
    }
  }

  /**
   * Invalidate access token (logout)
   */
  async invalidateAccessToken(accessToken, apiKey) {
    try {
      // Validate inputs
      if (!accessToken || !apiKey) {
        throw new Error('Access token and API key are required');
      }

      // Create KiteConnect instance with access token
      const kc = this.createKiteInstance(apiKey, accessToken);

      // Invalidate token
      await kc.invalidateAccessToken();

      return {
        success: true,
        message: 'Access token invalidated successfully'
      };

    } catch (error) {
      // Don't throw error for invalidation failures - token might already be invalid
      console.warn('Token invalidation warning:', error.message);
      
      return {
        success: true,
        message: 'Token invalidation completed (may have already been invalid)',
        warning: error.message
      };
    }
  }

  /**
   * Get user profile information
   */
  async getUserProfile(accessToken, apiKey) {
    try {
      // Validate inputs
      if (!accessToken || !apiKey) {
        throw new Error('Access token and API key are required');
      }

      // Create KiteConnect instance with access token
      const kc = this.createKiteInstance(apiKey, accessToken);

      // Get profile
      const profile = await kc.getProfile();

      return {
        success: true,
        profile: {
          userId: profile.user_id,
          userType: profile.user_type,
          email: profile.email,
          userName: profile.user_name,
          userShortname: profile.user_shortname,
          avatarUrl: profile.avatar_url,
          broker: profile.broker,
          exchanges: profile.exchanges,
          products: profile.products,
          orderTypes: profile.order_types
        }
      };

    } catch (error) {
      if (error.message.includes('Invalid access token')) {
        throw new Error('Invalid or expired access token');
      }

      throw new Error(`Failed to get user profile: ${error.message}`);
    }
  }

  /**
   * Test API connection and credentials
   */
  async testConnection(accessToken, apiKey) {
    try {
      // Try to get user profile as a connection test
      const result = await this.getUserProfile(accessToken, apiKey);
      
      return {
        success: true,
        connected: true,
        userId: result.profile.userId,
        message: 'Connection test successful'
      };

    } catch (error) {
      const message = error.message || 'Connection test failed';
      const normalized = message.toLowerCase();
      const isInvalidToken = normalized.includes('invalid or expired access token')
        || normalized.includes('tokenexception')
        || normalized.includes('token is invalid');

      return {
        success: false,
        connected: false,
        error: message,
        code: isInvalidToken ? 'INVALID_TOKEN' : 'CONNECTION_ERROR',
        message: isInvalidToken ? 'Access token invalid or expired' : 'Connection test failed'
      };
    }
  }

  /**
   * Get portfolio holdings
   */
  async getHoldings(accessToken, apiKey) {
    try {
      const kc = this.createKiteInstance(apiKey, accessToken);
      const holdings = await kc.getHoldings();

      return {
        success: true,
        holdings: holdings.map(holding => ({
          tradingsymbol: holding.tradingsymbol,
          exchange: holding.exchange,
          instrumentToken: holding.instrument_token,
          isin: holding.isin,
          product: holding.product,
          quantity: holding.quantity,
          t1Quantity: holding.t1_quantity,
          realisedQuantity: holding.realised_quantity,
          authorisedQuantity: holding.authorised_quantity,
          authorisedDate: holding.authorised_date,
          openingQuantity: holding.opening_quantity,
          collateralQuantity: holding.collateral_quantity,
          collateralType: holding.collateral_type,
          discrepancy: holding.discrepancy,
          averagePrice: holding.average_price,
          lastPrice: holding.last_price,
          closePrice: holding.close_price,
          pnl: holding.pnl,
          dayChange: holding.day_change,
          dayChangePercentage: holding.day_change_percentage
        }))
      };

    } catch (error) {
      throw new Error(`Failed to get holdings: ${error.message}`);
    }
  }

  /**
   * Get current positions
   */
  async getPositions(accessToken, apiKey) {
    try {
      const kc = this.createKiteInstance(apiKey, accessToken);
      const positions = await kc.getPositions();

      return {
        success: true,
        positions: {
          net: positions.net || [],
          day: positions.day || []
        }
      };

    } catch (error) {
      throw new Error(`Failed to get positions: ${error.message}`);
    }
  }

  /**
   * Get account margins
   */
  async getMargins(accessToken, apiKey) {
    try {
      const kc = this.createKiteInstance(apiKey, accessToken);
      const margins = await kc.getMargins();

      return {
        success: true,
        margins
      };

    } catch (error) {
      throw new Error(`Failed to get margins: ${error.message}`);
    }
  }

  /**
   * Get order history
   */
  async getOrders(accessToken, apiKey) {
    try {
      const kc = this.createKiteInstance(apiKey, accessToken);
      const orders = await kc.getOrders();

      return {
        success: true,
        orders
      };

    } catch (error) {
      throw new Error(`Failed to get orders: ${error.message}`);
    }
  }

  /**
   * Validate API credentials (without OAuth)
   */
  validateCredentials(apiKey, apiSecret) {
    try {
      // Basic validation
      if (!apiKey || typeof apiKey !== 'string' || apiKey.length < 10) {
        return {
          valid: false,
          error: 'Invalid API key format'
        };
      }

      if (!apiSecret || typeof apiSecret !== 'string' || apiSecret.length < 10) {
        return {
          valid: false,
          error: 'Invalid API secret format'
        };
      }

      // Check for common patterns
      if (apiKey.includes(' ') || apiSecret.includes(' ')) {
        return {
          valid: false,
          error: 'API credentials should not contain spaces'
        };
      }

      return {
        valid: true,
        message: 'Credentials format is valid'
      };

    } catch (error) {
      return {
        valid: false,
        error: `Credential validation failed: ${error.message}`
      };
    }
  }

  /**
   * Health check for Kite Connect service
   */
  async healthCheck() {
    try {
      // Test basic connectivity to Zerodha servers
      const https = require('https');
      const url = new URL(this.baseUrl);

      return new Promise((resolve) => {
        const req = https.request({
          hostname: url.hostname,
          port: 443,
          path: '/',
          method: 'HEAD',
          timeout: 5000
        }, (res) => {
          resolve({
            status: 'healthy',
            kiteApiReachable: true,
            statusCode: res.statusCode,
            timestamp: new Date().toISOString()
          });
        });

        req.on('error', (error) => {
          resolve({
            status: 'unhealthy',
            kiteApiReachable: false,
            error: error.message,
            timestamp: new Date().toISOString()
          });
        });

        req.on('timeout', () => {
          req.destroy();
          resolve({
            status: 'unhealthy',
            kiteApiReachable: false,
            error: 'Connection timeout',
            timestamp: new Date().toISOString()
          });
        });

        req.end();
      });

    } catch (error) {
      return {
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }
}

module.exports = KiteClient;
