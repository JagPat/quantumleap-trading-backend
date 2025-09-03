const { jest } = require('@jest/globals');

// Mock dependencies
jest.mock('../../core/security');
jest.mock('../../modules/auth/models/oauthToken');

const security = require('../../core/security');
const OAuthToken = require('../../modules/auth/models/oauthToken');
const TokenManager = require('../../modules/auth/services/tokenManager');

describe('Token Manager Tests', () => {
  let tokenManager;

  beforeEach(() => {
    tokenManager = new TokenManager();
    jest.clearAllMocks();
  });

  describe('storeTokens', () => {
    const mockTokens = {
      access_token: 'test_access_token',
      refresh_token: 'test_refresh_token',
      expires_in: 3600
    };

    it('should successfully store encrypted tokens', async () => {
      const configId = 'test_config_123';
      const encryptedAccessToken = 'encrypted_access_token';
      const encryptedRefreshToken = 'encrypted_refresh_token';

      security.encrypt.mockImplementation((token) => {
        if (token === 'test_access_token') return encryptedAccessToken;
        if (token === 'test_refresh_token') return encryptedRefreshToken;
        return token;
      });

      OAuthToken.create.mockResolvedValue({
        id: 'token_id_123',
        configId,
        accessTokenEncrypted: encryptedAccessToken,
        refreshTokenEncrypted: encryptedRefreshToken
      });

      const result = await tokenManager.storeTokens(configId, mockTokens);

      expect(result.success).toBe(true);
      expect(security.encrypt).toHaveBeenCalledWith('test_access_token');
      expect(security.encrypt).toHaveBeenCalledWith('test_refresh_token');
      expect(OAuthToken.create).toHaveBeenCalledWith({
        configId,
        accessTokenEncrypted: encryptedAccessToken,
        refreshTokenEncrypted: encryptedRefreshToken,
        expiresAt: expect.any(Date),
        tokenType: 'Bearer'
      });
    });

    it('should handle encryption errors', async () => {
      security.encrypt.mockRejectedValue(new Error('Encryption failed'));

      const result = await tokenManager.storeTokens('test_config_123', mockTokens);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Encryption failed');
    });

    it('should handle database storage errors', async () => {
      security.encrypt.mockResolvedValue('encrypted_token');
      OAuthToken.create.mockRejectedValue(new Error('Database error'));

      const result = await tokenManager.storeTokens('test_config_123', mockTokens);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Database error');
    });
  });

  describe('getTokens', () => {
    it('should successfully retrieve and decrypt tokens', async () => {
      const configId = 'test_config_123';
      const encryptedTokens = {
        accessTokenEncrypted: 'encrypted_access_token',
        refreshTokenEncrypted: 'encrypted_refresh_token',
        expiresAt: new Date(Date.now() + 3600000) // 1 hour from now
      };

      OAuthToken.findByConfigId.mockResolvedValue(encryptedTokens);
      
      security.decrypt.mockImplementation((encryptedToken) => {
        if (encryptedToken === 'encrypted_access_token') return 'test_access_token';
        if (encryptedToken === 'encrypted_refresh_token') return 'test_refresh_token';
        return encryptedToken;
      });

      const result = await tokenManager.getTokens(configId);

      expect(result.success).toBe(true);
      expect(result.data.tokens.access_token).toBe('test_access_token');
      expect(result.data.tokens.refresh_token).toBe('test_refresh_token');
      expect(security.decrypt).toHaveBeenCalledWith('encrypted_access_token');
      expect(security.decrypt).toHaveBeenCalledWith('encrypted_refresh_token');
    });

    it('should return null for non-existent tokens', async () => {
      OAuthToken.findByConfigId.mockResolvedValue(null);

      const result = await tokenManager.getTokens('non_existent_config');

      expect(result.success).toBe(true);
      expect(result.data.tokens).toBe(null);
    });

    it('should handle decryption errors', async () => {
      const encryptedTokens = {
        accessTokenEncrypted: 'encrypted_access_token',
        refreshTokenEncrypted: 'encrypted_refresh_token',
        expiresAt: new Date(Date.now() + 3600000)
      };

      OAuthToken.findByConfigId.mockResolvedValue(encryptedTokens);
      security.decrypt.mockRejectedValue(new Error('Decryption failed'));

      const result = await tokenManager.getTokens('test_config_123');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Decryption failed');
    });

    it('should detect expired tokens', async () => {
      const expiredTokens = {
        accessTokenEncrypted: 'encrypted_access_token',
        refreshTokenEncrypted: 'encrypted_refresh_token',
        expiresAt: new Date(Date.now() - 3600000) // 1 hour ago
      };

      OAuthToken.findByConfigId.mockResolvedValue(expiredTokens);
      security.decrypt.mockResolvedValue('decrypted_token');

      const result = await tokenManager.getTokens('test_config_123');

      expect(result.success).toBe(true);
      expect(result.data.expired).toBe(true);
    });
  });

  describe('refreshTokens', () => {
    it('should successfully refresh expired tokens', async () => {
      const userId = 'test_user_123';
      const configId = 'test_config_123';
      
      // Mock existing expired tokens
      const expiredTokens = {
        accessTokenEncrypted: 'old_encrypted_access_token',
        refreshTokenEncrypted: 'encrypted_refresh_token',
        expiresAt: new Date(Date.now() - 3600000)
      };

      // Mock new tokens from refresh
      const newTokens = {
        access_token: 'new_access_token',
        refresh_token: 'new_refresh_token',
        expires_in: 3600
      };

      OAuthToken.findByConfigId.mockResolvedValue(expiredTokens);
      security.decrypt.mockResolvedValue('old_refresh_token');
      
      // Mock the refresh API call (this would be mocked in kiteClient)
      tokenManager.kiteClient = {
        refreshAccessToken: jest.fn().mockResolvedValue(newTokens)
      };

      security.encrypt.mockImplementation((token) => `encrypted_${token}`);
      OAuthToken.updateTokens.mockResolvedValue(true);

      const result = await tokenManager.refreshTokens(userId);

      expect(result.success).toBe(true);
      expect(result.data.tokens.access_token).toBe('new_access_token');
    });

    it('should handle refresh token expiration', async () => {
      const userId = 'test_user_123';
      
      tokenManager.kiteClient = {
        refreshAccessToken: jest.fn().mockRejectedValue(new Error('Refresh token expired'))
      };

      OAuthToken.findByConfigId.mockResolvedValue({
        refreshTokenEncrypted: 'encrypted_refresh_token',
        expiresAt: new Date(Date.now() - 3600000)
      });
      security.decrypt.mockResolvedValue('expired_refresh_token');

      const result = await tokenManager.refreshTokens(userId);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Refresh token expired');
    });
  });

  describe('revokeTokens', () => {
    it('should successfully revoke and delete tokens', async () => {
      const configId = 'test_config_123';

      OAuthToken.deleteByConfigId.mockResolvedValue(true);

      const result = await tokenManager.revokeTokens(configId);

      expect(result.success).toBe(true);
      expect(OAuthToken.deleteByConfigId).toHaveBeenCalledWith(configId);
    });

    it('should handle token deletion errors', async () => {
      const configId = 'test_config_123';

      OAuthToken.deleteByConfigId.mockRejectedValue(new Error('Database deletion failed'));

      const result = await tokenManager.revokeTokens(configId);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Database deletion failed');
    });
  });

  describe('validateTokens', () => {
    it('should validate non-expired tokens', async () => {
      const tokens = {
        access_token: 'valid_token',
        expiresAt: new Date(Date.now() + 3600000) // 1 hour from now
      };

      const result = tokenManager.validateTokens(tokens);

      expect(result.valid).toBe(true);
      expect(result.expired).toBe(false);
    });

    it('should detect expired tokens', async () => {
      const tokens = {
        access_token: 'expired_token',
        expiresAt: new Date(Date.now() - 3600000) // 1 hour ago
      };

      const result = tokenManager.validateTokens(tokens);

      expect(result.valid).toBe(false);
      expect(result.expired).toBe(true);
    });

    it('should handle missing expiration date', async () => {
      const tokens = {
        access_token: 'token_without_expiry'
      };

      const result = tokenManager.validateTokens(tokens);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('Missing expiration date');
    });
  });
});