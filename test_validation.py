#!/usr/bin/env python3
"""
Test script for enhanced analysis validation
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ai_engine.simple_analysis_router import validate_and_enhance_analysis

def test_validation():
    """Test the analysis validation system"""
    
    # Sample portfolio data
    sample_portfolio = {
        "total_value": 1000000,
        "holdings": [
            {
                "tradingsymbol": "RELIANCE",
                "current_value": 250000,
                "quantity": 100,
                "average_price": 2400,
                "last_price": 2500,
                "pnl": 10000,
                "pnl_percentage": 4.17
            },
            {
                "tradingsymbol": "TCS",
                "current_value": 200000,
                "quantity": 50,
                "average_price": 3800,
                "last_price": 4000,
                "pnl": 10000,
                "pnl_percentage": 5.26
            }
        ]
    }
    
    # Test 1: Valid analysis
    print("=" * 60)
    print("TEST 1: Valid Analysis")
    print("=" * 60)
    
    valid_analysis = {
        "portfolio_health": {
            "overall_score": 85,
            "risk_level": "MEDIUM",
            "diversification_score": 0.8,
            "concentration_risk": 0.2
        },
        "stock_recommendations": [
            {
                "symbol": "RELIANCE",
                "current_allocation": 25.0,
                "target_allocation": 15.0,
                "action": "REDUCE",
                "quantity_change": -40,
                "value_change": -100000,
                "current_price": 2500,
                "reasoning": "Overweight position needs reduction",
                "confidence": 85,
                "priority": "HIGH",
                "timeframe": "SHORT_TERM"
            }
        ],
        "key_insights": [
            "Portfolio shows good diversification",
            "RELIANCE position is overweight"
        ]
    }
    
    validated = validate_and_enhance_analysis(valid_analysis, sample_portfolio)
    print("Validation successful!")
    print(f"Recommendations: {len(validated['stock_recommendations'])}")
    print(f"Portfolio score: {validated['portfolio_health']['overall_score']}")
    
    # Test 2: Invalid/incomplete analysis
    print("\n" + "=" * 60)
    print("TEST 2: Invalid Analysis")
    print("=" * 60)
    
    invalid_analysis = {
        "portfolio_health": {
            "overall_score": "invalid",  # Should be int
            "risk_level": "INVALID_LEVEL"  # Invalid enum
        },
        "stock_recommendations": [
            {
                "symbol": "RELIANCE",
                "action": "INVALID_ACTION",  # Invalid action
                "confidence": 150  # Out of range
            }
        ]
    }
    
    validated_invalid = validate_and_enhance_analysis(invalid_analysis, sample_portfolio)
    print("Validation handled invalid data!")
    print(f"Corrected score: {validated_invalid['portfolio_health']['overall_score']}")
    print(f"Corrected risk level: {validated_invalid['portfolio_health']['risk_level']}")
    print(f"Corrected action: {validated_invalid['stock_recommendations'][0]['action']}")
    print(f"Corrected confidence: {validated_invalid['stock_recommendations'][0]['confidence']}")
    
    # Test 3: Empty analysis
    print("\n" + "=" * 60)
    print("TEST 3: Empty Analysis")
    print("=" * 60)
    
    empty_analysis = {}
    validated_empty = validate_and_enhance_analysis(empty_analysis, sample_portfolio)
    print("Validation created fallback structure!")
    print(f"Generated recommendations: {len(validated_empty['stock_recommendations'])}")
    print(f"Generated insights: {len(validated_empty['key_insights'])}")
    
    # Test 4: Non-dict analysis
    print("\n" + "=" * 60)
    print("TEST 4: Non-Dict Analysis")
    print("=" * 60)
    
    non_dict_analysis = "invalid"
    validated_non_dict = validate_and_enhance_analysis(non_dict_analysis, sample_portfolio)
    print("Validation handled non-dict input!")
    print(f"Fallback structure created with score: {validated_non_dict['portfolio_health']['overall_score']}")
    
    print("\n" + "=" * 60)
    print("ALL VALIDATION TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_validation()