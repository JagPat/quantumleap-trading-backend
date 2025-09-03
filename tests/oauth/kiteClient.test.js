const { jest } = require('@jest/globals');
const axios = require('axios');

// Mock axios
jest.mock('axios');

const KiteClient = require('../../modules/auth/services/kiteClient');

describe('Kite Client Tests', () => {
  let kiteClient;

  beforeEach(() => {
    kiteClient = new KiteClient();
    jest.clearAllMocks();
  });

  describe('generateOAuthUrl', () => {
    it('should generate valid OAuth URL', () => {
      const apiKey = 'test_api_key';
      const redirectUri = 'https://example.com/callback';

      const oauthUrl = kiteClient.generateOAuthUrl(apiKey, redirectUri);

      expect(oauthUrl).toContain('https://kite.zerodha.com/connect/login');
      expect(oauthUrl).toContain(`api_key=${apiKey}`);
      expect(oauthUrl).toContain('v=3');
      expect(oauthUrl).toContain(`redirect_params=${encodeURIComponent(redirectUri)}`);
    });

    it('should handle missing parameters', () => {
      expect(() => {
        kiteClient.generateOAuthUrl();
      }).toThrow('API key is required');

      expect(() => {
        kiteClient.generateOAuthUrl('test_key');
      }).toThrow('Redirect URI is required');
    });
  });

  describe('generateSession', () => {
    const mockSessionData = {
      access_token: 'test_access_token',
      refresh_token: 'test_refresh_token',
      expires_in: 3600,
      token_type: 'Bearer'
    };

    it('should successfully generate session with valid request token', async () => {
      const requestToken = 'test_request_token';
      const apiKey = 'test_api_key';
      const apiSecret = 'test_api_secret';

      axios.post.mockResolvedValue({
        status: 200,
        data: {
          status: 'success',
          data: mockSessionData
        }
      });

      const result = await kiteClient.generateSession(requestToken, apiKey, apiSecret);

      expect(result.success).toBe(true);
      expect(result.data.access_token).toBe('test_access_token');
      expect(result.data.refresh_token).toBe('test_refresh_token');
      
      expect(axios.post).toHaveBeenCalledWith(
        'https://api.kite.trade/session/token',
        expect.objectContaining({
          api_key: apiKey,
          request_token: requestToken,
          checksum: expect.any(String)
        }),
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Kite-Version': '3'
          }
        })
      );
    });

    it('should handle invalid request token', async () => {
      axios.post.mockRejectedValue({
        response: {
          status: 400,
          data: {
            status: 'error',
            error_type: 'TokenException',
            message: 'Invalid request token'
          }
        }
      });

      const result = await kiteClient.generateSession('invalid_token', 'api_key', 'api_secret');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid request token');
    });

    it('should handle network errors', async () => {
      axios.post.mockRejectedValue(new Error('Network error'));

      const result = await kiteClient.generateSession('token', 'key', 'secret');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });

    it('should validate required parameters', async () => {
      const result1 = await kiteClient.generateSession();
      expect(result1.success).toBe(false);
      expect(result1.error).toContain('Request token is required');

      const result2 = await kiteClient.generateSession('token');
      expect(result2.success).toBe(false);
      expect(result2.error).toContain('API key is required');

      const result3 = await kiteClient.generateSession('token', 'key');
      expect(result3.success).toBe(false);
      expect(result3.error).toContain('API secret is required');
    });
  });

  describe('refreshAccessToken', () => {
    const mockRefreshData = {
      access_token: 'new_access_token',
      refresh_token: 'new_refresh_token',
      expires_in: 3600
    };

    it('should successfully refresh access token', async () => {
      const refreshToken = 'test_refresh_token';
      const apiKey = 'test_api_key';
      const apiSecret = 'test_api_secret';

      axios.post.mockResolvedValue({
        status: 200,
        data: {
          status: 'success',
          data: mockRefreshData
        }
      });

      const result = await kiteClient.refreshAccessToken(refreshToken, apiKey, apiSecret);

      expect(result.success).toBe(true);
      expect(result.data.access_token).toBe('new_access_token');
      
      expect(axios.post).toHaveBeenCalledWith(
        'https://api.kite.trade/session/refresh_token',
        expect.objectContaining({
          api_key: apiKey,
          refresh_token: refreshToken,
          checksum: expect.any(String)
        }),
        expect.any(Object)
      );
    });

    it('should handle expired refresh token', async () => {
      axios.post.mockRejectedValue({
        response: {
          status: 403,
          data: {
            status: 'error',
            error_type: 'TokenException',
            message: 'Refresh token expired'
          }
        }
      });

      const result = await kiteClient.refreshAccessToken('expired_token', 'key', 'secret');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Refresh token expired');
    });
  });

  describe('revokeSession', () => {
    it('should successfully revoke session', async () => {
      const accessToken = 'test_access_token';
      const apiKey = 'test_api_key';

      axios.delete.mockResolvedValue({
        status: 200,
        data: {
          status: 'success',
          data: true
        }
      });

      const result = await kiteClient.revokeSession(accessToken, apiKey);

      expect(result.success).toBe(true);
      
      expect(axios.delete).toHaveBeenCalledWith(
        'https://api.kite.trade/session/token',
        expect.objectContaining({
          headers: {
            'Authorization': `token ${apiKey}:${accessToken}`,
            'X-Kite-Version': '3'
          }
        })
      );
    });

    it('should handle revocation errors gracefully', async () => {
      axios.delete.mockRejectedValue({
        response: {
          status: 400,
          data: {
            status: 'error',
            message: 'Invalid session'
          }
        }
      });

      const result = await kiteClient.revokeSession('invalid_token', 'key');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid session');
    });

    it('should handle network errors during revocation', async () => {
      axios.delete.mockRejectedValue(new Error('Network timeout'));

      const result = await kiteClient.revokeSession('token', 'key');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network timeout');
    });
  });

  describe('validateCredentials', () => {
    it('should validate API key format', () => {
      const validKey = 'abcd1234efgh5678';
      const invalidKey = 'short';

      expect(kiteClient.validateCredentials(validKey, 'secret')).toBe(true);
      expect(kiteClient.validateCredentials(invalidKey, 'secret')).toBe(false);
    });

    it('should validate API secret format', () => {
      const validSecret = 'abcdefghijklmnopqrstuvwxyz123456';
      const invalidSecret = 'short';

      expect(kiteClient.validateCredentials('validkey123', validSecret)).toBe(true);
      expect(kiteClient.validateCredentials('validkey123', invalidSecret)).toBe(false);
    });

    it('should reject empty credentials', () => {
      expect(kiteClient.validateCredentials('', 'secret')).toBe(false);
      expect(kiteClient.validateCredentials('key', '')).toBe(false);
      expect(kiteClient.validateCredentials('', '')).toBe(false);
    });
  });

  describe('generateChecksum', () => {
    it('should generate consistent checksum for same inputs', () => {
      const apiKey = 'test_key';
      const requestToken = 'test_token';
      const apiSecret = 'test_secret';

      const checksum1 = kiteClient.generateChecksum(apiKey, requestToken, apiSecret);
      const checksum2 = kiteClient.generateChecksum(apiKey, requestToken, apiSecret);

      expect(checksum1).toBe(checksum2);
      expect(checksum1).toHaveLength(64); // SHA256 hex length
    });

    it('should generate different checksums for different inputs', () => {
      const checksum1 = kiteClient.generateChecksum('key1', 'token1', 'secret1');
      const checksum2 = kiteClient.generateChecksum('key2', 'token2', 'secret2');

      expect(checksum1).not.toBe(checksum2);
    });
  });
});