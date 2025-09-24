const crypto = require('crypto');

/**
 * Security utilities for OAuth token encryption and credential management
 * Following existing Node.js patterns in the project
 */
class SecurityManager {
  constructor() {
    this.algorithm = 'aes-256-gcm';
    this.keyLength = 32;
    this.ivLength = 16; // keep current length to preserve stored data expectations
    this.tagLength = 16;
    this.additionalData = Buffer.from('oauth-token', 'utf8');

    // Get encryption key from environment or generate one
    this.encryptionKey = this.getOrCreateEncryptionKey();
  }

  /**
   * Get or create encryption key from environment
   */
  getOrCreateEncryptionKey() {
    const envKey = process.env.OAUTH_ENCRYPTION_KEY;
    
    if (envKey) {
      // Ensure key is proper length
      return crypto.scryptSync(envKey, 'salt', this.keyLength);
    }
    
    // In development, generate a key (not recommended for production)
    if (process.env.NODE_ENV === 'development') {
      console.warn('⚠️ Using generated encryption key for development. Set OAUTH_ENCRYPTION_KEY in production.');
      return crypto.randomBytes(this.keyLength);
    }
    
    throw new Error('OAUTH_ENCRYPTION_KEY environment variable is required in production');
  }

  /**
   * Encrypt sensitive data (tokens, API secrets)
   */
  encrypt(plaintext) {
    try {
      if (plaintext === undefined || plaintext === null) {
        return '';
      }

      const iv = crypto.randomBytes(this.ivLength);
      const cipher = crypto.createCipheriv(this.algorithm, this.encryptionKey, iv);
      cipher.setAAD(this.additionalData);

      const encryptedBuffer = Buffer.concat([
        cipher.update(String(plaintext), 'utf8'),
        cipher.final()
      ]);
      const tag = cipher.getAuthTag();

      return Buffer.concat([iv, tag, encryptedBuffer]).toString('hex');
    } catch (error) {
      throw new Error(`Encryption failed: ${error.message}`);
    }
  }

  /**
   * Decrypt sensitive data
   */
  decrypt(encryptedData) {
    if (!encryptedData) {
      return '';
    }

    try {
      const buffer = Buffer.from(encryptedData, 'hex');

      if (buffer.length < (this.ivLength + this.tagLength)) {
        throw new Error('Encrypted payload too short');
      }

      const iv = buffer.subarray(0, this.ivLength);
      const tag = buffer.subarray(this.ivLength, this.ivLength + this.tagLength);
      const ciphertext = buffer.subarray(this.ivLength + this.tagLength);

      if (tag.length !== this.tagLength) {
        throw new Error(`Invalid authentication tag length: ${tag.length}`);
      }

      const decipher = crypto.createDecipheriv(this.algorithm, this.encryptionKey, iv);
      decipher.setAAD(this.additionalData);
      decipher.setAuthTag(tag);

      const decrypted = Buffer.concat([
        decipher.update(ciphertext),
        decipher.final()
      ]);

      return decrypted.toString('utf8');
    } catch (error) {
      throw new Error(`Decryption failed: ${error.message}`);
    }
  }

  /**
   * Generate secure random state for OAuth flow
   */
  generateOAuthState() {
    return crypto.randomBytes(32).toString('hex');
  }

  /**
   * Validate OAuth state to prevent CSRF attacks
   */
  validateOAuthState(providedState, storedState) {
    if (!providedState || !storedState) {
      return false;
    }
    
    // Use timing-safe comparison
    return crypto.timingSafeEqual(
      Buffer.from(providedState, 'hex'),
      Buffer.from(storedState, 'hex')
    );
  }

  /**
   * Hash API key for storage (one-way)
   */
  hashApiKey(apiKey) {
    return crypto.createHash('sha256').update(apiKey).digest('hex');
  }

  /**
   * Generate secure token ID
   */
  generateTokenId() {
    return crypto.randomUUID();
  }

  /**
   * Validate token expiration
   */
  isTokenExpired(expiresAt) {
    return this.hasTokenExpired(expiresAt);
  }

  hasTokenExpired(expiresAt) {
    if (!expiresAt) return true;
    const now = new Date();
    const expiry = new Date(expiresAt);
    return now >= expiry;
  }

  isWithinExpiryBuffer(expiresAt, bufferMinutes = 5) {
    if (!expiresAt) return true;
    const expiry = new Date(expiresAt);
    const now = new Date();
    const bufferMs = bufferMinutes * 60 * 1000;
    return expiry.getTime() - now.getTime() <= bufferMs;
  }

  calculateTokenExpiry(expiresIn, bufferMinutes = 5) {
    const now = new Date();
    const bufferSeconds = bufferMinutes * 60;
    const adjustedSeconds = Math.max(0, expiresIn - bufferSeconds);
    return new Date(now.getTime() + adjustedSeconds * 1000);
  }
}

module.exports = SecurityManager;
