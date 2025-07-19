#!/usr/bin/env python3
"""
Test script for AI preferences database functions
"""
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.service import (
    init_database, 
    store_ai_preferences, 
    get_ai_preferences, 
    get_ai_client_for_user,
    delete_ai_preferences
)

def test_ai_preferences():
    """Test AI preferences database functions"""
    print("🧪 Testing AI Preferences Database Functions")
    print("=" * 50)
    
    # Initialize database
    print("1. Initializing database...")
    init_database()
    print("✅ Database initialized")
    
    # Test user ID
    test_user_id = "EBW183"
    
    # Test storing preferences
    print(f"\n2. Storing AI preferences for user {test_user_id}...")
    success = store_ai_preferences(
        user_id=test_user_id,
        openai_api_key="sk-test-openai-key-123",
        claude_api_key="sk-ant-test-claude-key-456",
        gemini_api_key="AIza-test-gemini-key-789",
        preferred_provider="openai"
    )
    print(f"✅ Store preferences result: {success}")
    
    # Test retrieving preferences
    print(f"\n3. Retrieving AI preferences for user {test_user_id}...")
    preferences = get_ai_preferences(test_user_id)
    if preferences:
        print("✅ Preferences retrieved:")
        print(f"   - OpenAI key: {preferences['openai_api_key'][:10]}..." if preferences['openai_api_key'] else "   - OpenAI key: None")
        print(f"   - Claude key: {preferences['claude_api_key'][:10]}..." if preferences['claude_api_key'] else "   - Claude key: None")
        print(f"   - Gemini key: {preferences['gemini_api_key'][:10]}..." if preferences['gemini_api_key'] else "   - Gemini key: None")
        print(f"   - Preferred provider: {preferences['preferred_provider']}")
        print(f"   - Created at: {preferences['created_at']}")
        print(f"   - Updated at: {preferences['updated_at']}")
    else:
        print("❌ Failed to retrieve preferences")
    
    # Test AI client configuration
    print(f"\n4. Getting AI client config for user {test_user_id}...")
    client_config = get_ai_client_for_user(test_user_id)
    if client_config:
        print("✅ AI client config:")
        print(f"   - Selected provider: {client_config['selected_provider']}")
        print(f"   - API key: {client_config['api_key'][:10]}..." if client_config['api_key'] else "   - API key: None")
        print(f"   - Available providers: {client_config['available_providers']}")
        print(f"   - Preferred provider: {client_config['preferred_provider']}")
    else:
        print("❌ Failed to get AI client config")
    
    # Test with non-existent user
    print(f"\n5. Testing with non-existent user...")
    non_existent_prefs = get_ai_preferences("NONEXISTENT")
    print(f"✅ Non-existent user result: {non_existent_prefs}")
    
    # Test updating preferences
    print(f"\n6. Updating preferences for user {test_user_id}...")
    update_success = store_ai_preferences(
        user_id=test_user_id,
        openai_api_key="sk-updated-openai-key-999",
        claude_api_key=None,  # Remove Claude key
        gemini_api_key="AIza-updated-gemini-key-888",
        preferred_provider="gemini"
    )
    print(f"✅ Update preferences result: {update_success}")
    
    # Verify update
    updated_prefs = get_ai_preferences(test_user_id)
    if updated_prefs:
        print("✅ Updated preferences:")
        print(f"   - OpenAI key: {updated_prefs['openai_api_key'][:10]}..." if updated_prefs['openai_api_key'] else "   - OpenAI key: None")
        print(f"   - Claude key: {updated_prefs['claude_api_key'][:10]}..." if updated_prefs['claude_api_key'] else "   - Claude key: None")
        print(f"   - Gemini key: {updated_prefs['gemini_api_key'][:10]}..." if updated_prefs['gemini_api_key'] else "   - Gemini key: None")
        print(f"   - Preferred provider: {updated_prefs['preferred_provider']}")
    
    # Test deletion
    print(f"\n7. Deleting preferences for user {test_user_id}...")
    delete_success = delete_ai_preferences(test_user_id)
    print(f"✅ Delete preferences result: {delete_success}")
    
    # Verify deletion
    deleted_prefs = get_ai_preferences(test_user_id)
    print(f"✅ After deletion: {deleted_prefs}")
    
    print("\n" + "=" * 50)
    print("🎉 AI Preferences Database Test Complete!")

if __name__ == "__main__":
    test_ai_preferences()
