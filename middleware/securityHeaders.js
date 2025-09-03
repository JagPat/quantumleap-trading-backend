// Security headers middleware for OAuth endpoints
const securityHeaders = () => {
  return (req, res, next) => {
    // Prevent clickjacking
    res.setHeader('X-Frame-Options', 'DENY');
    
    // Prevent MIME type sniffing
    res.setHeader('X-Content-Type-Options', 'nosniff');
    
    // Enable XSS protection
    res.setHeader('X-XSS-Protection', '1; mode=block');
    
    // Strict transport security (HTTPS only)
    if (req.secure || req.headers['x-forwarded-proto'] === 'https') {
      res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
    }
    
    // Content Security Policy for OAuth pages
    const csp = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' https://kite.zerodha.com",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "connect-src 'self' https://api.kite.trade https://kite.zerodha.com",
      "form-action 'self' https://kite.zerodha.com",
      "frame-ancestors 'none'",
      "base-uri 'self'"
    ].join('; ');
    
    res.setHeader('Content-Security-Policy', csp);
    
    // Referrer policy
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    
    // Permissions policy
    res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
    
    // Remove server information
    res.removeHeader('X-Powered-By');
    
    next();
  };
};

// CORS configuration for OAuth endpoints
const corsConfig = {
  origin: function (origin, callback) {
    // Allow requests from your frontend domains
    const allowedOrigins = [
      process.env.FRONTEND_URL,
      'http://localhost:3000',
      'http://localhost:5173',
      'https://kite.zerodha.com' // For OAuth callbacks
    ].filter(Boolean);

    // Allow requests with no origin (mobile apps, etc.)
    if (!origin) return callback(null, true);
    
    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'X-CSRF-Token',
    'X-API-Key'
  ],
  exposedHeaders: ['X-CSRF-Token'],
  maxAge: 86400 // 24 hours
};

// Input validation middleware
const validateInput = () => {
  return (req, res, next) => {
    // Sanitize common injection attempts
    const sanitizeString = (str) => {
      if (typeof str !== 'string') return str;
      
      // Remove potential script injections
      return str
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        .replace(/javascript:/gi, '')
        .replace(/on\w+\s*=/gi, '')
        .trim();
    };

    // Recursively sanitize object
    const sanitizeObject = (obj) => {
      if (obj === null || typeof obj !== 'object') {
        return typeof obj === 'string' ? sanitizeString(obj) : obj;
      }

      if (Array.isArray(obj)) {
        return obj.map(sanitizeObject);
      }

      const sanitized = {};
      for (const [key, value] of Object.entries(obj)) {
        sanitized[key] = sanitizeObject(value);
      }
      return sanitized;
    };

    // Sanitize request body and query parameters
    if (req.body) {
      req.body = sanitizeObject(req.body);
    }
    
    if (req.query) {
      req.query = sanitizeObject(req.query);
    }

    next();
  };
};

// Request size limiting
const requestSizeLimit = () => {
  return (req, res, next) => {
    const maxSize = 1024 * 1024; // 1MB limit
    
    if (req.headers['content-length'] && parseInt(req.headers['content-length']) > maxSize) {
      return res.status(413).json({
        success: false,
        error: 'Request too large',
        message: 'Request size exceeds maximum allowed limit'
      });
    }
    
    next();
  };
};

module.exports = {
  securityHeaders,
  corsConfig,
  validateInput,
  requestSizeLimit
};