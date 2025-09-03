// Test setup file for OAuth integration tests
const { jest } = require('@jest/globals');

// Global test configuration
global.console = {
  ...console,
  // Suppress console.log during tests unless needed
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: console.warn,
  error: console.error,
};

// Mock environment variables for testing
process.env.NODE_ENV = 'test';
process.env.OAUTH_ENCRYPTION_KEY = 'test_encryption_key_32_characters_long';
process.env.JWT_SECRET = 'test_jwt_secret_key';
process.env.AUTH_OTP_PEPPER = 'test_otp_pepper';
process.env.ZERODHA_API_KEY = 'test_zerodha_api_key';
process.env.ZERODHA_API_SECRET = 'test_zerodha_api_secret';
process.env.ZERODHA_REDIRECT_URI = 'http://localhost:3000/oauth/callback';

// Global test timeout
jest.setTimeout(10000);

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
});

// Global error handler for unhandled promises
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Mock axios for all tests
jest.mock('axios', () => ({
  post: jest.fn(),
  get: jest.fn(),
  delete: jest.fn(),
  create: jest.fn(() => ({
    post: jest.fn(),
    get: jest.fn(),
    delete: jest.fn()
  }))
}));