"""
Test configuration for QuantumLeap Trading Backend
"""
import pytest
import os

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