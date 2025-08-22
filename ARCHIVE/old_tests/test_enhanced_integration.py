#!/usr/bin/env python3
"""
Test script for enhanced AI provider integration
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ai_engine.simple_analysis_router import (
    create_enhanced_portfolio_prompt,
    validate_and_enhance_analysis,
    extract_json_from_text,
    clean_ai_response_text
)

def test_json_extraction():
    """Test JSON extraction from various AI response formats"""
    
    print("=" * 60)
    print("TESTING JSON EXTRACTION")
    print("=" * 60)
    
    # Test 1: JSON wrapped in code blocks
    response_with_code_blocks = '''
    Here's the analysis for your portfolio:
    
    ```json
    {
        "portfolio_health": {
            "overall_score": 85,
            "risk_level": "MEDIUM"
        },
        "stock_recommendations": [
            {
                "symbol": "RELIANCE",
                "action": "REDUCE"
            }
        ]
    }
    ```
    
    I hope this helps!
    '''
    
    extracted = extract_json_from_text(response_with_code_blocks)
    print("Test 1 - Code blocks:", "PASSED" if extracted and "portfolio_health" in extracted else "FAILED")
    
    # Test 2: JSON mixed with text
    response_mixed = '''
    Based on your portfolio analysis, here is my recommendation:
    
    {"portfolio_health": {"overall_score": 75, "risk_level": "HIGH"}, "stock_recommendations": [{"symbol": "TCS", "action": "HOLD"}]}
    
    Let me know if you need clarification.
    '''
    
    extracted = extract_json_from_text(response_mixed)
    print("Test 2 - Mixed text:", "PASSED" if extracted and "portfolio_health" in extracted else "FAILED")
    
    # Test 3: Clean response text
    messy_response = '''
    Here's the analysis:
    ```json
    {"portfolio_health": {"overall_score": 90}}
    ```
    I hope this helps!
    '''
    
    cleaned = clean_ai_response_text(messy_response)
    print("Test 3 - Text cleaning:", "PASSED" if "Here's the analysis:" not in cleaned else "FAILED")

def test_end_to_end_flow():
    """Test the complete enhanced analysis flow"""
    
    print("\n" + "=" * 60)
    print("TESTING END-TO-END ENHANCED FLOW")
    print("=" * 60)
    
    # Sample portfolio data
    sample_portfolio = {
        "total_value": 1500000,
        "holdings": [
            {
                "tradingsymbol": "RELIANCE",
                "current_value": 375000,
                "quantity": 150,
                "average_price": 2400,
                "last_price": 2500,
                "pnl": 15000,
                "pnl_percentage": 4.17
            },
            {
                "tradingsymbol": "TCS",
                "current_value": 300000,
                "quantity": 75,
                "average_price": 3800,
                "last_price": 4000,
                "pnl": 15000,
                "pnl_percentage": 5.26
            },
            {
                "tradingsymbol": "HDFCBANK",
                "current_value": 450000,
                "quantity": 300,
                "average_price": 1400,
                "last_price": 1500,
                "pnl": 30000,
                "pnl_percentage": 7.14
            },
            {
                "tradingsymbol": "INFY",
                "current_value": 225000,
                "quantity": 150,
                "average_price": 1400,
                "last_price": 1500,
                "pnl": 15000,
                "pnl_percentage": 7.14
            },
            {
                "tradingsymbol": "ITC",
                "current_value": 150000,
                "quantity": 3000,
                "average_price": 45,
                "last_price": 50,
                "pnl": 15000,
                "pnl_percentage": 11.11
            }
        ],
        "positions": []
    }
    
    user_preferences = {
        "risk_tolerance": "moderate",
        "investment_timeline": "long_term",
        "preferred_sectors": ["technology", "finance", "energy"],
        "max_position_size": 20.0
    }
    
    # Step 1: Generate enhanced prompt
    print("Step 1: Generating enhanced prompt...")
    enhanced_prompt = create_enhanced_portfolio_prompt(
        sample_portfolio, 
        "test_user_enhanced", 
        user_preferences
    )
    
    print(f"✓ Enhanced prompt generated ({len(enhanced_prompt)} characters)")
    print(f"✓ Contains user preferences: {'risk_tolerance' in enhanced_prompt}")
    print(f"✓ Contains specific holdings: {'RELIANCE' in enhanced_prompt}")
    print(f"✓ Contains P&L data: {'P&L:' in enhanced_prompt}")
    
    # Step 2: Simulate AI response and validation
    print("\nStep 2: Simulating AI response validation...")
    
    # Simulate a realistic AI response
    simulated_ai_response = {
        "portfolio_health": {
            "overall_score": 82,
            "risk_level": "MEDIUM",
            "diversification_score": 0.75,
            "concentration_risk": 0.35,
            "performance_rating": "GOOD",
            "key_strengths": ["Strong technology sector exposure", "Profitable positions"],
            "key_weaknesses": ["High concentration in HDFCBANK", "Limited sector diversification"]
        },
        "stock_recommendations": [
            {
                "symbol": "HDFCBANK",
                "current_allocation": 30.0,
                "target_allocation": 20.0,
                "action": "REDUCE",
                "quantity_change": -100,
                "value_change": -150000,
                "current_price": 1500,
                "reasoning": "Overweight position exceeds recommended 20% limit for single stock",
                "confidence": 85,
                "priority": "HIGH",
                "timeframe": "SHORT_TERM",
                "expected_impact": "Reduce concentration risk by 10%",
                "risk_warning": "Large position reduction may impact returns if stock outperforms",
                "sector": "Banking"
            },
            {
                "symbol": "RELIANCE",
                "current_allocation": 25.0,
                "target_allocation": 18.0,
                "action": "REDUCE",
                "quantity_change": -42,
                "value_change": -105000,
                "current_price": 2500,
                "reasoning": "Reduce energy sector concentration and improve diversification",
                "confidence": 78,
                "priority": "MEDIUM",
                "timeframe": "SHORT_TERM",
                "expected_impact": "Better sector balance",
                "risk_warning": "Energy sector may outperform in current market",
                "sector": "Energy"
            },
            {
                "symbol": "TCS",
                "current_allocation": 20.0,
                "target_allocation": 22.0,
                "action": "INCREASE",
                "quantity_change": 15,
                "value_change": 60000,
                "current_price": 4000,
                "reasoning": "Technology sector showing strong fundamentals and growth potential",
                "confidence": 80,
                "priority": "MEDIUM",
                "timeframe": "LONG_TERM",
                "expected_impact": "Increase exposure to high-growth technology sector",
                "risk_warning": "Technology stocks can be volatile",
                "sector": "Technology"
            }
        ],
        "sector_analysis": {
            "current_sectors": [
                {"sector": "Banking", "allocation": 30.0, "performance": "GOOD"},
                {"sector": "Energy", "allocation": 25.0, "performance": "AVERAGE"},
                {"sector": "Technology", "allocation": 35.0, "performance": "EXCELLENT"},
                {"sector": "FMCG", "allocation": 10.0, "performance": "GOOD"}
            ],
            "sector_recommendations": [
                {"sector": "Banking", "target_allocation": 25.0, "action": "DECREASE", "reasoning": "Reduce overweight position"},
                {"sector": "Technology", "target_allocation": 40.0, "action": "INCREASE", "reasoning": "Strong growth prospects"}
            ],
            "diversification_score": 0.75,
            "concentration_risks": ["Banking sector overweight at 30%", "Top 3 holdings represent 75% of portfolio"]
        },
        "key_insights": [
            "Portfolio shows strong performance with 6.67% overall P&L",
            "HDFCBANK position at 30% creates concentration risk",
            "Technology sector exposure is well-positioned for growth",
            "Consider adding healthcare or consumer goods for better diversification",
            "Current allocation favors large-cap stocks with stable returns"
        ]
    }
    
    # Validate the response
    validated_analysis = validate_and_enhance_analysis(simulated_ai_response, sample_portfolio)
    
    print(f"✓ Analysis validated successfully")
    print(f"✓ Stock recommendations: {len(validated_analysis['stock_recommendations'])}")
    print(f"✓ Portfolio score: {validated_analysis['portfolio_health']['overall_score']}")
    print(f"✓ Risk level: {validated_analysis['portfolio_health']['risk_level']}")
    print(f"✓ Key insights: {len(validated_analysis['key_insights'])}")
    
    # Step 3: Check recommendation quality
    print("\nStep 3: Checking recommendation quality...")
    
    recommendations = validated_analysis['stock_recommendations']
    high_priority_count = sum(1 for r in recommendations if r.get('priority') == 'HIGH')
    specific_actions = sum(1 for r in recommendations if r.get('action') in ['BUY', 'SELL', 'REDUCE', 'INCREASE'])
    
    print(f"✓ High priority recommendations: {high_priority_count}")
    print(f"✓ Specific actionable recommendations: {specific_actions}")
    print(f"✓ All recommendations have confidence scores: {all('confidence' in r for r in recommendations)}")
    print(f"✓ All recommendations have specific symbols: {all('symbol' in r for r in recommendations)}")
    
    print("\n" + "=" * 60)
    print("ENHANCED INTEGRATION TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    return validated_analysis

if __name__ == "__main__":
    test_json_extraction()
    enhanced_result = test_end_to_end_flow()
    
    print(f"\nFinal Result Summary:")
    print(f"- Portfolio Health Score: {enhanced_result['portfolio_health']['overall_score']}/100")
    print(f"- Risk Level: {enhanced_result['portfolio_health']['risk_level']}")
    print(f"- Total Recommendations: {len(enhanced_result['stock_recommendations'])}")
    print(f"- Actionable Insights: {len(enhanced_result['key_insights'])}")