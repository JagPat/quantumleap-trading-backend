const crypto = require('crypto');

// Secure logging utility that excludes sensitive data
class SecureLogger {
  constructor() {
    this.sensitiveFields = [
      'password',
      'apiSecret',
      'api_secret',
      'accessToken',
      'access_token',
      'refreshToken',
      'refresh_token',
      'authorization',
      'checksum',
      'otp',
      'pin',
      'secret',
      'key',
      'token'
    ];
  }

  // Sanitize object by removing or masking sensitive fields
  sanitizeData(data) {
    if (!data || typeof data !== 'object') {
      return data;
    }

    if (Array.isArray(data)) {
      return data.map(item => this.sanitizeData(item));
    }

    const sanitized = {};
    
    for (const [key, value] of Object.entries(data)) {
      const lowerKey = key.toLowerCase();
      
      // Check if field contains sensitive data
      const isSensitive = this.sensitiveFields.some(field => 
        lowerKey.includes(field.toLowerCase())
      );

      if (isSensitive) {
        if (typeof value === 'string' && value.length > 0) {
          // Mask sensitive strings
          sanitized[key] = this.maskSensitiveValue(value);
        } else {
          sanitized[key] = '[REDACTED]';
        }
      } else if (typeof value === 'object' && value !== null) {
        // Recursively sanitize nested objects
        sanitized[key] = this.sanitizeData(value);
      } else {
        sanitized[key] = value;
      }
    }

    return sanitized;
  }

  // Mask sensitive values showing only first and last few characters
  maskSensitiveValue(value) {
    if (typeof value !== 'string' || value.length < 8) {
      return '[REDACTED]';
    }

    const start = value.substring(0, 3);
    const end = value.substring(value.length - 3);
    const middle = '*'.repeat(Math.min(value.length - 6, 10));
    
    return `${start}${middle}${end}`;
  }

  // Log OAuth operation with sanitized data
  logOAuthOperation(operation, data, level = 'info') {
    const sanitizedData = this.sanitizeData(data);
    const logEntry = {
      timestamp: new Date().toISOString(),
      operation,
      data: sanitizedData,
      requestId: this.generateRequestId()
    };

    console[level](`OAuth ${operation}:`, JSON.stringify(logEntry, null, 2));
    return logEntry.requestId;
  }

  // Log OAuth error with context but no sensitive data
  logOAuthError(operation, error, context = {}) {
    const sanitizedContext = this.sanitizeData(context);
    const logEntry = {
      timestamp: new Date().toISOString(),
      operation,
      error: {
        message: error.message,
        code: error.code || 'UNKNOWN',
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
      },
      context: sanitizedContext,
      requestId: this.generateRequestId()
    };

    console.error(`OAuth Error - ${operation}:`, JSON.stringify(logEntry, null, 2));
    return logEntry.requestId;
  }

  // Log security events
  logSecurityEvent(event, details = {}) {
    const sanitizedDetails = this.sanitizeData(details);
    const logEntry = {
      timestamp: new Date().toISOString(),
      event,
      severity: 'HIGH',
      details: sanitizedDetails,
      requestId: this.generateRequestId()
    };

    console.warn(`Security Event - ${event}:`, JSON.stringify(logEntry, null, 2));
    return logEntry.requestId;
  }

  // Generate unique request ID for tracking
  generateRequestId() {
    return crypto.randomBytes(8).toString('hex');
  }

  // Middleware to add secure logging to requests
  middleware() {
    return (req, res, next) => {
      const requestId = this.generateRequestId();
      req.requestId = requestId;
      
      // Log request (sanitized)
      const requestData = {
        method: req.method,
        url: req.url,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        body: this.sanitizeData(req.body),
        query: this.sanitizeData(req.query)
      };

      this.logOAuthOperation('REQUEST', { requestId, ...requestData }, 'debug');

      // Override res.json to log responses (sanitized)
      const originalJson = res.json;
      res.json = function(data) {
        const sanitizedResponse = this.sanitizeData(data);
        this.logOAuthOperation('RESPONSE', { 
          requestId, 
          statusCode: res.statusCode,
          data: sanitizedResponse 
        }, 'debug');
        
        return originalJson.call(this, data);
      }.bind(this);

      next();
    };
  }
}

// Export singleton instance
module.exports = new SecureLogger();