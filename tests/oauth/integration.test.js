const request = require('supertest');
const express = require('express');
const { jest } = require('@jest/globals');

// Integration test for complete OAuth flow
describe('OAuth Integration Tests', () => {
  let app;
  let testUserId;
  let testConfigId;

  beforeAll(async () => {
    // Setup test app with all OAuth routes
    app = express();
    app.use(express.json());
    
    // Mock user ID for testing
    testUserId = 'test_user_integration_123';
    testConfigId = 'test_config_integration_123';
  });

  describe('Complete OAuth Flow', () => {
    it('should complete full OAuth flow from setup to callback', async () => {
      // Step 1: Setup OAuth with credentials
      const setupResponse = await request(app)
        .post('/api/modules/auth/broker/setup-oauth')
        .send({
          apiKey: 'test_api_key_integration',
          apiSecret: 'test_api_secret_integration',
          userId: testUserId
        });

      expect(setupResponse.status).toBe(200);
      expect(setupResponse.body.success).toBe(true);
      expect(setupResponse.body.data.oauthUrl).toContain('kite.zerodha.com');

      // Step 2: Simulate OAuth callback
      const callbackResponse = await request(app)
        .post('/api/modules/auth/broker/callback')
        .send({
          request_token: 'test_request_token_integration',
          action: 'login',
          status: 'success',
          userId: testUserId
        });

      expect(callbackResponse.status).toBe(200);
      expect(callbackResponse.body.success).toBe(true);
      expect(callbackResponse.body.data.connectionStatus).toBe('connected');

      // Step 3: Check connection status
      const statusResponse = await request(app)
        .get('/api/modules/auth/broker/status')
        .query({ userId: testUserId });

      expect(statusResponse.status).toBe(200);
      expect(statusResponse.body.success).toBe(true);
      expect(statusResponse.body.data.connectionStatus.state).toBe('connected');
    });

    it('should handle OAuth flow with token refresh', async () => {
      // Simulate token refresh scenario
      const refreshResponse = await request(app)
        .post('/api/modules/auth/broker/refresh-token')
        .send({ userId: testUserId });

      expect(refreshResponse.status).toBe(200);
      expect(refreshResponse.body.success).toBe(true);
      expect(refreshResponse.body.data.tokens).toBeDefined();
    });

    it('should handle complete disconnection flow', async () => {
      // Test disconnection
      const disconnectResponse = await request(app)
        .post('/api/modules/auth/broker/disconnect')
        .send({ userId: testUserId });

      expect(disconnectResponse.status).toBe(200);
      expect(disconnectResponse.body.success).toBe(true);

      // Verify status is disconnected
      const statusResponse = await request(app)
        .get('/api/modules/auth/broker/status')
        .query({ userId: testUserId });

      expect(statusResponse.body.data.connectionStatus.state).toBe('disconnected');
    });
  });

  describe('Error Scenarios', () => {
    it('should handle invalid credentials gracefully', async () => {
      const response = await request(app)
        .post('/api/modules/auth/broker/setup-oauth')
        .send({
          apiKey: 'invalid_key',
          apiSecret: 'invalid_secret',
          userId: testUserId
        });

      expect(response.status).toBe(400);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('Invalid');
    });

    it('should handle OAuth authorization denial', async () => {
      const response = await request(app)
        .post('/api/modules/auth/broker/callback')
        .send({
          request_token: 'denied_token',
          action: 'login',
          status: 'error',
          error: 'access_denied',
          userId: testUserId
        });

      expect(response.status).toBe(401);
      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('denied');
    });
  });
});