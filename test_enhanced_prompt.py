#!/usr/bin/env python3
"""
Test script for enhanced portfolio prompt generation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ai_engine.simple_analysis_router import create_enhanced_portfolio_prompt

def test_enhanced_prompt():
    """Test the enhanced portfolio prompt generation"""
    
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
            },
            {
                "tradingsymbol": "HDFCBANK",
                "current_value": 300000,
                "quantity": 200,
                "average_price": 1400,
                "last_price": 1500,
                "pnl": 20000,
                "pnl_percentage": 7.14
            },
            {
                "tradingsymbol": "INFY",
                "current_value": 150000,
                "quantity": 100,
                "average_price": 1400,
                "last_price": 1500,
                "pnl": 10000,
                "pnl_percentage": 7.14
            },
            {
                "tradingsymbol": "ITC",
                "current_value": 100000,
                "quantity": 2000,
                "average_price": 45,
                "last_price": 50,
                "pnl": 10000,
                "pnl_percentage": 11.11
            }
        ],
        "positions": [
            {
                "tradingsymbol": "WIPRO",
                "net_quantity": 50,
                "current_value": 25000,
                "unrealised": 2500,
                "day_change": 500,
                "day_change_percentage": 2.04
            }
        ]
    }
    
    # Sample user preferences
    user_preferences = {
        "risk_tolerance": "moderate",
        "investment_timeline": "long_term",
        "preferred_sectors": ["technology", "finance"],
        "max_position_size": 15.0
    }
    
    # Generate enhanced prompt
    user_id = "test_user_123"
    enhanced_prompt = create_enhanced_portfolio_prompt(
        sample_portfolio, 
        user_id, 
        user_preferences
    )
    
    print("=" * 80)
    print("ENHANCED PORTFOLIO ANALYSIS PROMPT")
    print("=" * 80)
    print(enhanced_prompt)
    print("=" * 80)
    print(f"Prompt length: {len(enhanced_prompt)} characters")
    print(f"Holdings analyzed: {len(sample_portfolio['holdings'])}")
    print(f"Positions analyzed: {len(sample_portfolio['positions'])}")
    print("=" * 80)

if __name__ == "__main__":
    test_enhanced_prompt()