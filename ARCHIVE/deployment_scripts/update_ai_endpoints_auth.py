#!/usr/bin/env python3
"""
Script to update all AI endpoints with authentication
"""

import re

# Read the current file
with open('app/ai_engine/ai_components_router.py', 'r') as f:
    content = f.read()

# Define the endpoints to update with authentication
endpoints_to_update = [
    (r'@router\.post\("/strategy-templates/deploy"\)\nasync def deploy_strategy\(deployment: StrategyDeployment\):', 
     '@router.post("/strategy-templates/deploy")\nasync def deploy_strategy(deployment: StrategyDeployment, user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/strategy-templates/\{template_id\}/backtest"\)\nasync def backtest_strategy\(template_id: str\):', 
     '@router.post("/strategy-templates/{template_id}/backtest")\nasync def backtest_strategy(template_id: str, user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/market-intelligence"\)\nasync def get_market_intelligence\(request: MarketIntelligenceRequest\):', 
     '@router.post("/market-intelligence")\nasync def get_market_intelligence(request: MarketIntelligenceRequest, user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/performance-analytics"\)\nasync def get_performance_analytics\(request: PerformanceAnalyticsRequest\):', 
     '@router.post("/performance-analytics")\nasync def get_performance_analytics(request: PerformanceAnalyticsRequest, user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.get\("/risk-metrics"\)\nasync def get_risk_metrics\(\):', 
     '@router.get("/risk-metrics")\nasync def get_risk_metrics(user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/risk-settings"\)\nasync def update_risk_settings\(settings: RiskSettings\):', 
     '@router.post("/risk-settings")\nasync def update_risk_settings(settings: RiskSettings, user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/emergency-stop"\)\nasync def trigger_emergency_stop\(\):', 
     '@router.post("/emergency-stop")\nasync def trigger_emergency_stop(user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.get\("/learning-insights"\)\nasync def get_learning_insights\(timeframe: str = "1M"\):', 
     '@router.get("/learning-insights")\nasync def get_learning_insights(timeframe: str = "1M", user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.get\("/optimization-recommendations"\)\nasync def get_optimization_recommendations\(\):', 
     '@router.get("/optimization-recommendations")\nasync def get_optimization_recommendations(user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/optimization-recommendations/action"\)\nasync def handle_optimization_action\(action: OptimizationAction\):', 
     '@router.post("/optimization-recommendations/action")\nasync def handle_optimization_action(action: OptimizationAction, user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/analysis/comprehensive"\)\nasync def get_comprehensive_analysis\(timeframe: str = "1M"\):', 
     '@router.post("/analysis/comprehensive")\nasync def get_comprehensive_analysis(timeframe: str = "1M", user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/copilot/analyze"\)\nasync def analyze_portfolio\(portfolio_data: Dict\[str, Any\]\):', 
     '@router.post("/copilot/analyze")\nasync def analyze_portfolio(portfolio_data: Dict[str, Any], user_id: str = Depends(get_current_user_id)):'),
    
    (r'@router\.post\("/copilot/recommendations"\)\nasync def get_portfolio_recommendations\(request_data: Dict\[str, Any\]\):', 
     '@router.post("/copilot/recommendations")\nasync def get_portfolio_recommendations(request_data: Dict[str, Any], user_id: str = Depends(get_current_user_id)):')
]

# Apply the updates
for pattern, replacement in endpoints_to_update:
    content = re.sub(pattern, replacement, content)

# Also update docstrings to mention authentication requirement
auth_docstring_updates = [
    ('"""\\n    Deploy a strategy template', '"""\\n    Deploy a strategy template\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Backtest a strategy template', '"""\\n    Backtest a strategy template\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Get market intelligence and sentiment analysis', '"""\\n    Get market intelligence and sentiment analysis\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Get performance analytics for portfolio', '"""\\n    Get performance analytics for portfolio\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Get current risk metrics', '"""\\n    Get current risk metrics\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Update risk management settings', '"""\\n    Update risk management settings\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Trigger emergency stop for all trading', '"""\\n    Trigger emergency stop for all trading\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Get AI learning insights and progress', '"""\\n    Get AI learning insights and progress\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Get AI optimization recommendations', '"""\\n    Get AI optimization recommendations\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Handle optimization recommendation action', '"""\\n    Handle optimization recommendation action\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Get comprehensive AI analysis', '"""\\n    Get comprehensive AI analysis\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Analyze portfolio using AI copilot', '"""\\n    Analyze portfolio using AI copilot\\n    Requires authentication: JWT token in Authorization header'),
    ('"""\\n    Get portfolio recommendations from AI', '"""\\n    Get portfolio recommendations from AI\\n    Requires authentication: JWT token in Authorization header')
]

for pattern, replacement in auth_docstring_updates:
    content = re.sub(pattern, replacement, content)

# Write the updated content back
with open('app/ai_engine/ai_components_router.py', 'w') as f:
    f.write(content)

print("✅ Updated all AI endpoints with authentication requirements")
print("📊 Updated endpoints:")
for i, (pattern, _) in enumerate(endpoints_to_update, 1):
    endpoint_name = pattern.split('"')[1] if '"' in pattern else f"endpoint_{i}"
    print(f"   {i}. {endpoint_name}")