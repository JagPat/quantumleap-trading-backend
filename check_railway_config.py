#!/usr/bin/env python3
"""
Check Railway Configuration Requirements
Ensures all necessary environment variables and configurations are set
"""

import os
import json
from datetime import datetime

def check_railway_requirements():
    """Check Railway deployment requirements"""
    print("🔍 Checking Railway Configuration Requirements")
    print("=" * 60)
    
    issues = []
    recommendations = []
    
    # Check essential files
    print("\n1️⃣ Checking Essential Files...")
    essential_files = [
        ("main.py", "Application entry point"),
        ("requirements.txt", "Python dependencies"),
        ("Procfile", "Railway process configuration"),
        ("railway.json", "Railway service configuration")
    ]
    
    for file_path, description in essential_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path} - {description}")
        else:
            print(f"   ❌ {file_path} - {description} (MISSING)")
            issues.append(f"Missing {file_path}")
    
    # Check Procfile content
    print("\n2️⃣ Checking Procfile Configuration...")
    if os.path.exists("Procfile"):
        with open("Procfile", "r") as f:
            procfile_content = f.read().strip()
        print(f"   Content: {procfile_content}")
        
        if "main:app" in procfile_content and "uvicorn" in procfile_content:
            print("   ✅ Procfile looks correct")
        else:
            print("   ⚠️ Procfile might need adjustment")
            recommendations.append("Ensure Procfile uses: web: uvicorn main:app --host 0.0.0.0 --port $PORT")
    
    # Check railway.json
    print("\n3️⃣ Checking Railway Configuration...")
    if os.path.exists("railway.json"):
        with open("railway.json", "r") as f:
            railway_config = json.load(f)
        print(f"   Build command: {railway_config.get('build', {}).get('builder', 'Not specified')}")
        print(f"   Start command: {railway_config.get('deploy', {}).get('startCommand', 'Not specified')}")
    
    # Check requirements.txt
    print("\n4️⃣ Checking Dependencies...")
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r") as f:
            requirements = f.read()
        
        essential_deps = ["fastapi", "uvicorn", "pydantic"]
        for dep in essential_deps:
            if dep in requirements.lower():
                print(f"   ✅ {dep} found")
            else:
                print(f"   ❌ {dep} missing")
                issues.append(f"Missing dependency: {dep}")
    
    # Check environment variables that Railway might need
    print("\n5️⃣ Environment Variables (Local Check)...")
    railway_env_vars = [
        ("PORT", "Application port (Railway sets this)"),
        ("RAILWAY_ENVIRONMENT", "Railway environment"),
        ("DATABASE_URL", "Database connection (if using database)")
    ]
    
    for var, description in railway_env_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var} = {value[:20]}... - {description}")
        else:
            print(f"   ⚠️ {var} not set locally - {description}")
    
    # Check main.py for Railway compatibility
    print("\n6️⃣ Checking main.py Railway Compatibility...")
    try:
        with open("main.py", "r") as f:
            main_content = f.read()
        
        if 'os.getenv("PORT"' in main_content:
            print("   ✅ Uses PORT environment variable")
        else:
            print("   ⚠️ Should use PORT environment variable")
            recommendations.append("Ensure main.py uses: port = int(os.getenv('PORT', 8000))")
        
        if 'host="0.0.0.0"' in main_content:
            print("   ✅ Binds to 0.0.0.0")
        else:
            print("   ⚠️ Should bind to 0.0.0.0")
            recommendations.append("Ensure uvicorn runs with host='0.0.0.0'")
            
    except Exception as e:
        print(f"   ❌ Error reading main.py: {e}")
        issues.append("Cannot read main.py")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Configuration Summary")
    print("=" * 60)
    
    if not issues:
        print("✅ All essential configurations look good!")
        print("🚀 Railway should be able to deploy successfully")
    else:
        print(f"⚠️ Found {len(issues)} potential issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    if recommendations:
        print(f"\n💡 Recommendations ({len(recommendations)}):")
        for rec in recommendations:
            print(f"   - {rec}")
    
    # Create configuration report
    report = {
        "timestamp": datetime.now().isoformat(),
        "issues": issues,
        "recommendations": recommendations,
        "status": "ready" if not issues else "needs_attention"
    }
    
    with open("railway_config_check.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Configuration report saved to: railway_config_check.json")
    
    return len(issues) == 0

def main():
    """Main configuration check"""
    is_ready = check_railway_requirements()
    
    print("\n🎯 Next Steps:")
    if is_ready:
        print("   1. Configuration looks good")
        print("   2. Check Railway dashboard for deployment status")
        print("   3. Wait for deployment to complete (5-15 minutes)")
        print("   4. Monitor Railway logs for any runtime errors")
    else:
        print("   1. Fix the identified configuration issues")
        print("   2. Commit and push changes to GitHub")
        print("   3. Railway will automatically redeploy")
    
    print(f"\n🔗 Railway Dashboard: https://railway.com/project/925c1cba-ce50-4be3-b5f9-a6bcb7dac747")

if __name__ == "__main__":
    main()