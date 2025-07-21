"""
Test configuration for QuantumLeap Trading Backend
"""
import pytest
import os
import sys
import asyncio
from unittest.mock import Mock, patch

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test configuration
TEST_CONFIG = {
    "backend_url": os.getenv("TEST_BACKEND_URL", "https://web-production-de0bc.up.railway.app"),
    "test_user_id": "test_user_123",
    "timeout": 30
}

@pytest.fixture
def backend_url():
    """Backend URL for testing"""
    return TEST_CONFIG["backend_url"]

@pytest.fixture
def test_user_id():
    """Test user ID"""
    return TEST_CONFIG["test_user_id"]

@pytest.fixture
def test_headers():
    """Common test headers"""
    return {
        "Content-Type": "application/json",
        "X-User-ID": TEST_CONFIG["test_user_id"]
    }

@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing"""
    return {
        "total_value": 500000,
        "holdings": [
            {
                "symbol": "RELIANCE",
                "quantity": 100,
                "current_price": 2500,
                "current_value": 250000,
                "sector": "Energy"
            },
            {
                "symbol": "TCS", 
                "quantity": 50,
                "current_price": 3000,
                "current_value": 150000,
                "sector": "IT"
            },
            {
                "symbol": "HDFCBANK",
                "quantity": 80,
                "current_price": 1250,
                "current_value": 100000,
                "sector": "Banking"
            }
        ]
    }

@pytest.fixture
def mock_database():
    """Mock database connection for testing"""
    with patch('app.database.service.get_db_connection') as mock:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock_cursor

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Configure pytest for async tests
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "markers", "asyncio: mark test to run with asyncio"
    )