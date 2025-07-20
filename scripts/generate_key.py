#!/usr/bin/env python3
"""
Simple script to generate encryption key for Railway
"""
import base64
import os

def generate_key():
    """Generate a 32-byte key and encode it as base64"""
    key = os.urandom(32)
    encoded_key = base64.urlsafe_b64encode(key).decode()
    print(f"Generated encryption key: {encoded_key}")
    print("\nAdd this to your Railway environment variables:")
    print(f"ENCRYPTION_KEY={encoded_key}")
    return encoded_key

if __name__ == "__main__":
    generate_key() 