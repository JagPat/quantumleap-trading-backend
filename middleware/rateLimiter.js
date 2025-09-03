const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis');

// Rate limiting configuration for OAuth endpoints
const createOAuthRateLimiter = () => {
  return rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 10, // Limit each IP to 10 OAuth requests per windowMs
    message: {
      success: false,
      error: 'Too many OAuth requests from this IP, please try again later.',
      retryAfter: 15 * 60 // 15 minutes in seconds
    },
    standardHeaders: true,
    legacyHeaders: false,
    // Custom key generator to include user ID if available
    keyGenerator: (req) => {
      const userId = req.body?.userId || req.query?.userId;
      const ip = req.ip || req.connection.remoteAddress;
      return userId ? `oauth_${userId}` : `oauth_ip_${ip}`;
    },
    // Skip rate limiting for successful requests to encourage proper usage
    skipSuccessfulRequests: true,
    // Custom handler for rate limit exceeded
    handler: (req, res) => {
      const logger = req.app.get('logger') || console;
      logger.warn('OAuth rate limit exceeded', {
        ip: req.ip,
        userId: req.body?.userId || req.query?.userId,
        endpoint: req.path,
        userAgent: req.get('User-Agent')
      });
      
      res.status(429).json({
        success: false,
        error: 'Rate limit exceeded for OAuth operations',
        message: 'Too many authentication attempts. Please wait before trying again.',
        retryAfter: Math.ceil((req.rateLimit.resetTime - Date.now()) / 1000)
      });
    }
  });
};

// More restrictive rate limiting for sensitive operations
const createTokenRefreshLimiter = () => {
  return rateLimit({
    windowMs: 5 * 60 * 1000, // 5 minutes
    max: 5, // Limit token refresh to 5 per 5 minutes per user
    message: {
      success: false,
      error: 'Too many token refresh requests, please try again later.'
    },
    keyGenerator: (req) => {
      const userId = req.body?.userId || req.query?.userId;
      return userId ? `refresh_${userId}` : `refresh_ip_${req.ip}`;
    }
  });
};

// General API rate limiting
const createGeneralLimiter = () => {
  return rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    message: {
      success: false,
      error: 'Too many requests from this IP, please try again later.'
    },
    standardHeaders: true,
    legacyHeaders: false
  });
};

module.exports = {
  createOAuthRateLimiter,
  createTokenRefreshLimiter,
  createGeneralLimiter
};