const crypto = require('crypto');

// CSRF protection middleware for OAuth operations
class CSRFProtection {
  constructor() {
    this.tokenStore = new Map(); // In production, use Redis or database
    this.tokenExpiry = 30 * 60 * 1000; // 30 minutes
  }

  // Generate CSRF token
  generateToken(sessionId) {
    const token = crypto.randomBytes(32).toString('hex');
    const expiresAt = Date.now() + this.tokenExpiry;
    
    this.tokenStore.set(sessionId, {
      token,
      expiresAt
    });

    // Clean up expired tokens periodically
    this.cleanupExpiredTokens();
    
    return token;
  }

  // Validate CSRF token
  validateToken(sessionId, providedToken) {
    const storedData = this.tokenStore.get(sessionId);
    
    if (!storedData) {
      return false;
    }

    if (Date.now() > storedData.expiresAt) {
      this.tokenStore.delete(sessionId);
      return false;
    }

    return storedData.token === providedToken;
  }

  // Clean up expired tokens
  cleanupExpiredTokens() {
    const now = Date.now();
    for (const [sessionId, data] of this.tokenStore.entries()) {
      if (now > data.expiresAt) {
        this.tokenStore.delete(sessionId);
      }
    }
  }

  // Middleware for OAuth setup endpoint
  protectOAuthSetup() {
    return (req, res, next) => {
      const sessionId = req.sessionID || req.ip;
      const csrfToken = this.generateToken(sessionId);
      
      // Add CSRF token to response for client to use
      res.locals.csrfToken = csrfToken;
      
      // Set secure headers
      res.set({
        'X-CSRF-Token': csrfToken,
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
      });
      
      next();
    };
  }

  // Middleware for OAuth callback validation
  validateOAuthCallback() {
    return (req, res, next) => {
      const sessionId = req.sessionID || req.ip;
      const providedToken = req.headers['x-csrf-token'] || req.body.csrfToken;
      
      if (!providedToken) {
        return res.status(403).json({
          success: false,
          error: 'CSRF token missing',
          message: 'Security token is required for this operation'
        });
      }

      if (!this.validateToken(sessionId, providedToken)) {
        return res.status(403).json({
          success: false,
          error: 'Invalid CSRF token',
          message: 'Security token is invalid or expired'
        });
      }

      // Token is valid, remove it (one-time use)
      this.tokenStore.delete(sessionId);
      next();
    };
  }

  // Middleware for state parameter validation in OAuth flow
  validateOAuthState() {
    return (req, res, next) => {
      const state = req.query.state || req.body.state;
      
      if (!state) {
        return res.status(400).json({
          success: false,
          error: 'Missing state parameter',
          message: 'OAuth state parameter is required for security'
        });
      }

      // Validate state format (should be base64 encoded JSON)
      try {
        const stateData = JSON.parse(Buffer.from(state, 'base64').toString());
        
        if (!stateData.timestamp || !stateData.sessionId) {
          throw new Error('Invalid state structure');
        }

        // Check if state is not too old (5 minutes max)
        const stateAge = Date.now() - stateData.timestamp;
        if (stateAge > 5 * 60 * 1000) {
          return res.status(400).json({
            success: false,
            error: 'Expired state parameter',
            message: 'OAuth state has expired, please restart the authentication process'
          });
        }

        req.oauthState = stateData;
        next();
      } catch (error) {
        return res.status(400).json({
          success: false,
          error: 'Invalid state parameter',
          message: 'OAuth state parameter is malformed'
        });
      }
    };
  }

  // Generate secure state parameter for OAuth flow
  generateOAuthState(sessionId, userId) {
    const stateData = {
      sessionId,
      userId,
      timestamp: Date.now(),
      nonce: crypto.randomBytes(16).toString('hex')
    };

    return Buffer.from(JSON.stringify(stateData)).toString('base64');
  }
}

// Export singleton instance
module.exports = new CSRFProtection();