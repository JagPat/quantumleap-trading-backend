#!/usr/bin/env python3
"""
Complete Railway Deployment Script
Ensures all latest changes are deployed to Railway with proper configuration
"""

import os
import sys
import subprocess
import json
import time
import requests
from datetime import datetime

def run_command(command, description=""):
    """Run a command and return the result"""
    print(f"🔧 {description}")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"   ❌ Failed")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False, result.stderr
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False, str(e)

def check_railway_cli():
    """Check if Railway CLI is installed and authenticated"""
    print("🚂 Checking Railway CLI...")
    
    # Check if railway CLI is installed
    success, output = run_command("railway --version", "Checking Railway CLI version")
    if not success:
        print("❌ Railway CLI not found. Please install it:")
        print("   npm install -g @railway/cli")
        return False
    
    # Check if authenticated
    success, output = run_command("railway whoami", "Checking Railway authentication")
    if not success:
        print("❌ Not authenticated with Railway. Please run:")
        print("   railway login")
        return False
    
    print("✅ Railway CLI is ready")
    return True

def create_railway_config():
    """Create or update Railway configuration files"""
    print("📝 Creating Railway 