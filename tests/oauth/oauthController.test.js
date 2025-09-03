const request = require('supertest');
const express = require('express');
const { jest } = require('@jest/globals');

// Mock dependencies
jest.mock('../../modules/auth/services/brokerService');
jest.mock('../../modules/auth/services/tokenManager');
jest.mock('../../modules/auth/services/kiteClient');

const brokerService = require('../../modules/auth/services/brokerService');
const tokenManager = require('../../modules/auth/services/tokenManager');
const kiteClient = require('../../modules/auth/services/kiteClient');
const oauthRoutes = require('../../modules/auth/routes/oauth');

describe('OAuth Controller Tests', () => {
  let app;

  beforeEach(() => {
    app = express();
    app.use(express.json());
    app.use('/api/modules/auth/broker', oauthRoutes);
    
    // Reset all mocks
    jest.clearAllMocks();
  });

  describe('POST /setup-oauth', () => {
    const validCredentials = {
      apiKey: 'test_api_key',
      apiSecret: 'test_api_secret',
      userId: 'test_user_123'
    };

    it('should successfully setup OAuth with valid credentials', async () => {
      const mockOAuthUrl = 'https://kite.zerodha.com/connect/login?api_key=test_api_key&v=3';
      
      brokerService.setupOAuth.mockResolvedValue({
        success: true,
        data: { oauthUrl: mockOAuthUrl }
      });

      const response = await request(app)
        .post('/api/modules/auth/broker/setup-oauth')
        .send(validCredentials);

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.oauthUrl).toBe(mockOAuthUrl);
      expect(brokerService.setupOAuth).toHaveBeenCalledWith(validCredentials);
    });

    it('should return 400 for missing API key', async () => {
      const invalidCredentials = {
        apiSecret: 'test_api_secret',
        userId: 'test_user_123'
      };

      const response = await request(app)
        .post('/api/modules/auth/broker/setup-oauth')
        .send(invalidCredentials);

      expect(response.status).toBe(400);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('API key is required');
    });

    it('should return 400 for missing API secret', async () => {
      const invalidCredentials = {
        apiKey: 'test_api_key',
        userId: 'test_user_123'
      };

      const response = await request(app)
        .post('/api/modules/auth/broker/setup-oauth')
        .send(invalidCredentials);

      expect(response.status).toBe(400);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('API secret is required');
    });

    it('should handle broker service errors', async () => {
      brokerService.setupOAuth.mockRejectedValue(new Error('Invalid API credentials'));

      const response = await request(app)
        .post('/api/modules/auth/broker/setup-oauth')
        .send(validCredentials);

      expect(response.status).toBe(500);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('Invalid API credentials');
    });
  });

  describe('POST /callback', () => {
    const validCallback = {
      request_token: 'test_request_token',
      action: 'login',
      status: 'success',
      userId: 'test_user_123'
    };

    it('should successfully handle OAuth callback', async () => {
      const mockTokens = {
        access_token: 'test_access_token',
        refresh_token: 'test_refresh_token',
        expires_in: 3600
      };

      brokerService.handleCallback.mockResolvedValue({
        success: true,
        data: { tokens: mockTokens, connectionStatus: 'connected' }
      });

      const response = await request(app)
        .post('/api/modules/auth/broker/callback')
        .send(validCallback);

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.connectionStatus).toBe('connected');
      expect(brokerService.handleCallback).toHaveBeenCalledWith(validCallback);
    });

    it('should return 400 for missing request token', async () => {
      const invalidCallback = {
        action: 'login',
        status: 'success',
        userId: 'test_user_123'
      };

      const response = await request(app)
        .post('/api/modules/auth/broker/callback')
        .send(invalidCallback);

      expect(response.status).toBe(400);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('Request token is required');
    });

    it('should handle OAuth authorization denial', async () => {
      const deniedCallback = {
        ...validCallback,
        status: 'error',
        error: 'access_denied'
      };

      brokerService.handleCallback.mockRejectedValue(new Error('OAuth authorization denied'));

      const response = await request(app)
        .post('/api/modules/auth/broker/callback')
        .send(deniedCallback);

      expect(response.status).toBe(401);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('OAuth authorization denied');
    });
  });

  describe('POST /refresh-token', () => {
    const refreshRequest = {
      userId: 'test_user_123'
    };

    it('should successfully refresh tokens', async () => {
      const mockRefreshedTokens = {
        access_token: 'new_access_token',
        refresh_token: 'new_refresh_token',
        expires_in: 3600
      };

      tokenManager.refreshTokens.mockResolvedValue({
        success: true,
        data: { tokens: mockRefreshedTokens }
      });

      const response = await request(app)
        .post('/api/modules/auth/broker/refresh-token')
        .send(refreshRequest);

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.tokens.access_token).toBe('new_access_token');
      expect(tokenManager.refreshTokens).toHaveBeenCalledWith('test_user_123');
    });

    it('should handle refresh token expiration', async () => {
      tokenManager.refreshTokens.mockRejectedValue(new Error('Refresh token expired'));

      const response = await request(app)
        .post('/api/modules/auth/broker/refresh-token')
        .send(refreshRequest);

      expect(response.status).toBe(401);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('Refresh token expired');
    });
  });

  describe('POST /disconnect', () => {
    const disconnectRequest = {
      userId: 'test_user_123'
    };

    it('should successfully disconnect broker', async () => {
      brokerService.disconnect.mockResolvedValue({
        success: true,
        data: { connectionStatus: 'disconnected' }
      });

      const response = await request(app)
        .post('/api/modules/auth/broker/disconnect')
        .send(disconnectRequest);

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.connectionStatus).toBe('disconnected');
      expect(brokerService.disconnect).toHaveBeenCalledWith('test_user_123');
    });

    it('should handle disconnect errors gracefully', async () => {
      brokerService.disconnect.mockRejectedValue(new Error('Token revocation failed'));

      const response = await request(app)
        .post('/api/modules/auth/broker/disconnect')
        .send(disconnectRequest);

      expect(response.status).toBe(200); // Should still succeed locally
      expect(response.body.success).toBe(true);
      expect(response.body.warning).toContain('Token revocation failed');
    });
  });

  describe('GET /status', () => {
    it('should return connection status for user', async () => {
      const mockStatus = {
        state: 'connected',
        message: 'Successfully connected to Zerodha',
        lastChecked: new Date().toISOString()
      };

      brokerService.getConnectionStatus.mockResolvedValue({
        success: true,
        data: { connectionStatus: mockStatus }
      });

      const response = await request(app)
        .get('/api/modules/auth/broker/status')
        .query({ userId: 'test_user_123' });

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.connectionStatus.state).toBe('connected');
    });

    it('should return disconnected status for non-existent user', async () => {
      brokerService.getConnectionStatus.mockResolvedValue({
        success: true,
        data: { 
          connectionStatus: { 
            state: 'disconnected', 
            message: 'No broker configuration found' 
          } 
        }
      });

      const response = await request(app)
        .get('/api/modules/auth/broker/status')
        .query({ userId: 'non_existent_user' });

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.connectionStatus.state).toBe('disconnected');
    });
  });
});