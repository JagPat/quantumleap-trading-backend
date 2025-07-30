"""
Simple Analysis Router - Direct AI Integration
Bypasses complex analysis engine for immediate AI portfolio analysis
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/simple-analysis", tags=["Simple AI Analysis"])

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    return "default_user"

@router.post("/portfolio")
async def simple_portfolio_analysis(
    portfolio_data: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate portfolio analysis using direct AI integration"""
    try:
        # Import AI service for user preferences
        from .service import AIService
        ai_service = AIService()
        
        # Get user preferences
        user_preferences = await ai_service.get_user_preferences(user_id)
        
        # Check if user has valid AI providers (user keys OR environment variables)
        import os
        has_openai = (user_preferences and user_preferences.get('has_openai_key', False)) or bool(os.getenv('OPENAI_API_KEY'))
        has_claude = (user_preferences and user_preferences.get('has_claude_key', False)) or bool(os.getenv('ANTHROPIC_API_KEY'))
        has_gemini = (user_preferences and user_preferences.get('has_gemini_key', False)) or bool(os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'))
        
        if not (has_openai or has_claude or has_gemini):
            logger.info(f"No valid AI providers for user {user_id} - no user keys or environment variables found")
            return await generate_fallback_analysis(portfolio_data, user_id)
        
        # Try to use enhanced AI analysis
        try:
            logger.info(f"Attempting enhanced AI analysis for user {user_id}")
            
            # Get AI provider (prefer user keys, fallback to environment)
            if has_openai:
                provider = "openai"
                api_key = (user_preferences and user_preferences.get('openai_api_key')) or os.getenv('OPENAI_API_KEY')
            elif has_claude:
                provider = "claude"
                api_key = (user_preferences and user_preferences.get('claude_api_key')) or os.getenv('ANTHROPIC_API_KEY')
            else:
                provider = "gemini"
                api_key = (user_preferences and user_preferences.get('gemini_api_key')) or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            
            # Generate enhanced AI analysis
            analysis_result = await generate_ai_portfolio_analysis(
                portfolio_data, provider, api_key, user_id
            )
            
            if analysis_result:
                logger.info(f"Enhanced AI analysis successful for user {user_id} using {provider}")
                
                # Store successful analysis for performance tracking
                try:
                    await store_analysis_for_tracking(user_id, analysis_result, provider)
                except Exception as e:
                    logger.warning(f"Failed to store analysis for tracking: {e}")
                
                # Generate trading signals from analysis (if auto-trading enabled)
                try:
                    from .signal_generator_integration import generate_trading_signals_from_analysis
                    signals = await generate_trading_signals_from_analysis(user_id, portfolio_data, analysis_result)
                    if signals:
                        logger.info(f"Generated {len(signals)} trading signals for user {user_id}")
                        # Add signal information to analysis result
                        analysis_result['trading_signals_generated'] = len(signals)
                        analysis_result['signals_summary'] = [
                            {
                                'symbol': signal.symbol,
                                'type': signal.signal_type.value,
                                'confidence': signal.confidence_score,
                                'priority': signal.priority.value
                            } for signal in signals[:5]  # Include first 5 signals in summary
                        ]
                except Exception as signal_error:
                    logger.warning(f"Failed to generate trading signals: {signal_error}")
                
                return analysis_result
            else:
                logger.warning(f"Enhanced AI analysis failed, using fallback for user {user_id}")
                return await generate_fallback_analysis(portfolio_data, user_id)
                
        except Exception as ai_error:
            logger.error(f"AI analysis error: {ai_error}")
            return await generate_fallback_analysis(portfolio_data, user_id)
            
    except Exception as e:
        logger.error(f"Simple portfolio analysis failed: {e}")
        return await generate_fallback_analysis(portfolio_data, user_id)

async def create_enhanced_portfolio_prompt(
    portfolio_data: Dict[str, Any], 
    user_id: str,
    user_preferences: Optional[Dict[str, Any]] = None,
    market_context: Optional[Dict[str, Any]] = None
) -> str:
    """Create enhanced, specific portfolio analysis prompt with detailed context and market intelligence"""
    
    total_value = portfolio_data.get("total_value", 0)
    holdings = portfolio_data.get("holdings", [])
    positions = portfolio_data.get("positions", [])
    
    # Build detailed portfolio context
    portfolio_context = f"""
ENHANCED PORTFOLIO ANALYSIS - SPECIFIC RECOMMENDATIONS REQUIRED

CURRENT PORTFOLIO OVERVIEW:
- Total Portfolio Value: ₹{total_value:,.2f}
- Number of Holdings: {len(holdings)}
- Number of Active Positions: {len(positions)}
- User ID: {user_id}
- Analysis Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}

DETAILED HOLDINGS BREAKDOWN:
"""
    
    # Add specific holdings with comprehensive data
    total_pnl = 0
    for i, holding in enumerate(holdings[:15], 1):  # Top 15 holdings for detailed analysis
        symbol = holding.get('tradingsymbol', holding.get('symbol', 'Unknown'))
        current_value = holding.get('current_value', 0)
        allocation = (current_value / total_value * 100) if total_value > 0 else 0
        pnl = holding.get('pnl', 0)
        pnl_pct = holding.get('pnl_percentage', 0)
        quantity = holding.get('quantity', 0)
        average_price = holding.get('average_price', 0)
        last_price = holding.get('last_price', current_value / quantity if quantity > 0 else 0)
        
        total_pnl += pnl
        
        portfolio_context += f"""
{i}. {symbol}:
   - Current Value: ₹{current_value:,.0f} ({allocation:.2f}% of portfolio)
   - Quantity: {quantity} shares
   - Average Price: ₹{average_price:.2f}
   - Current Price: ₹{last_price:.2f}
   - P&L: ₹{pnl:,.0f} ({pnl_pct:.2f}%)
   - Position Status: {'PROFIT' if pnl > 0 else 'LOSS' if pnl < 0 else 'NEUTRAL'}
"""
    
    # Add positions data if available
    if positions:
        portfolio_context += f"\nACTIVE TRADING POSITIONS:\n"
        for i, position in enumerate(positions[:10], 1):  # Top 10 positions
            symbol = position.get('tradingsymbol', position.get('symbol', 'Unknown'))
            quantity = position.get('net_quantity', position.get('quantity', 0))
            current_value = position.get('current_value', 0)
            unrealised = position.get('unrealised', position.get('pnl', 0))
            day_change = position.get('day_change', 0)
            day_change_pct = position.get('day_change_percentage', 0)
            
            portfolio_context += f"""
{i}. {symbol}:
   - Net Quantity: {quantity} shares
   - Current Value: ₹{current_value:,.0f}
   - Unrealized P&L: ₹{unrealised:,.0f}
   - Day Change: ₹{day_change:,.0f} ({day_change_pct:.2f}%)
"""
    
    # Add portfolio performance summary
    total_pnl_pct = (total_pnl / total_value * 100) if total_value > 0 else 0
    portfolio_context += f"""
PORTFOLIO PERFORMANCE SUMMARY:
- Total P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:.2f}%)
- Portfolio Status: {'PROFITABLE' if total_pnl > 0 else 'LOSS-MAKING' if total_pnl < 0 else 'BREAK-EVEN'}
"""
    
    # Add user preferences if available
    if user_preferences:
        risk_tolerance = user_preferences.get('risk_tolerance', 'medium')
        investment_timeline = user_preferences.get('investment_timeline', 'medium_term')
        preferred_sectors = user_preferences.get('preferred_sectors', [])
        max_position_size = user_preferences.get('max_position_size', 15.0)
        
        portfolio_context += f"""
USER INVESTMENT PROFILE:
- Risk Tolerance: {risk_tolerance.upper()}
- Investment Timeline: {investment_timeline.replace('_', ' ').title()}
- Preferred Sectors: {', '.join(preferred_sectors) if preferred_sectors else 'Not specified'}
- Maximum Position Size: {max_position_size}%
"""
    
    # Add comprehensive market context if available
    if market_context:
        market_data = market_context.get('market_data', {})
        sector_data = market_context.get('sector_performance', {})
        sentiment_data = market_context.get('market_sentiment', {})
        events_data = market_context.get('recent_events', [])
        
        nifty = market_data.get('nifty_50', {})
        sensex = market_data.get('sensex', {})
        
        portfolio_context += f"""

CURRENT MARKET INTELLIGENCE:
- Market Status: {market_data.get('market_status', 'unknown').upper()}
- Trading Session: {market_context.get('trading_session', 'unknown').replace('_', ' ').title()}
- Data Quality Score: {market_context.get('data_quality', 0)}/100

MARKET INDICES:
- Nifty 50: {nifty.get('value', 0):,.0f} ({nifty.get('change', 0):+.0f}, {nifty.get('change_percent', 0):+.2f}%)
- Sensex: {sensex.get('value', 0):,.0f} ({sensex.get('change', 0):+.0f}, {sensex.get('change_percent', 0):+.2f}%)
- Market Trend: {nifty.get('trend', 'neutral').upper()}
- Volatility Index: {market_data.get('volatility_index', 0):.1f}

MARKET BREADTH:
- Advancing Stocks: {market_data.get('market_breadth', {}).get('advances', 0):,}
- Declining Stocks: {market_data.get('market_breadth', {}).get('declines', 0):,}
- Unchanged: {market_data.get('market_breadth', {}).get('unchanged', 0):,}
- Market Volume: ₹{market_data.get('volume', 0):,}

SECTOR PERFORMANCE TODAY:
"""
        
        # Add sector performance data
        sectors = sector_data.get('sectors', {})
        for sector_name, sector_info in sectors.items():
            change_pct = sector_info.get('change_percent', 0)
            trend = sector_info.get('trend', 'neutral')
            rating = sector_info.get('analyst_rating', 'hold')
            momentum = sector_info.get('momentum_score', 50)
            
            portfolio_context += f"""- {sector_name}: {change_pct:+.2f}% ({trend.upper()}, Rating: {rating.upper()}, Momentum: {momentum}/100)
"""
        
        # Add market sentiment
        sentiment = sentiment_data.get('overall_sentiment', 'neutral')
        sentiment_score = sentiment_data.get('sentiment_score', 0)
        fear_greed = sentiment_data.get('fear_greed_index', 50)
        
        portfolio_context += f"""
MARKET SENTIMENT ANALYSIS:
- Overall Sentiment: {sentiment.upper()} (Score: {sentiment_score:+.2f})
- Fear & Greed Index: {fear_greed}/100
- Confidence Level: {sentiment_data.get('confidence_level', 70)}%
- Key Sentiment Drivers: {', '.join(sentiment_data.get('key_factors', []))}

"""
        
        # Add recent market events
        if events_data:
            portfolio_context += f"""RECENT MARKET EVENTS (Impact on Analysis):
"""
            for event in events_data[:3]:  # Top 3 events
                portfolio_context += f"""- {event.get('title', 'Unknown Event')} ({event.get('type', 'general')})
  Impact Level: {event.get('impact_level', 'medium').upper()}
  Date: {event.get('date', 'recent')}
  Affected Sectors: {', '.join(event.get('affected_sectors', []))}
  Description: {event.get('description', 'No details available')}

"""
        
        # Add AI context summary
        ai_summary = market_context.get('ai_context_summary', '')
        if ai_summary:
            portfolio_context += f"""MARKET CONTEXT FOR AI ANALYSIS:
{ai_summary}

"""
    
    # Enhanced analysis requirements with specific output format
    analysis_requirements = """
CRITICAL ANALYSIS REQUIREMENTS - MUST BE SPECIFIC AND ACTIONABLE:

1. STOCK-LEVEL RECOMMENDATIONS (MANDATORY):
   For EACH major holding (>3% allocation), provide:
   - Exact NSE trading symbol (e.g., RELIANCE, TCS, HDFCBANK)
   - Current allocation percentage (calculated from above data)
   - Recommended target allocation percentage
   - Specific action: BUY/SELL/HOLD/REDUCE/INCREASE
   - Exact quantity to buy/sell (in shares)
   - Rupee amount involved in the transaction
   - Clear reasoning based on current market conditions and stock fundamentals
   - Confidence score (0-100%)
   - Priority level: HIGH/MEDIUM/LOW
   - Timeframe: IMMEDIATE (1-7 days)/SHORT_TERM (1-4 weeks)/LONG_TERM (1-3 months)

2. PORTFOLIO REBALANCING STRATEGY:
   - Identify overweight positions (>15% allocation) with specific reduction targets
   - Suggest underweight sectors that need increased allocation
   - Recommend new stocks to add with exact target allocations
   - Provide sector diversification improvements with specific percentages

3. RISK ASSESSMENT WITH THRESHOLDS:
   - Concentration risk analysis with specific percentage thresholds
   - Identify stocks contributing to high correlation risk
   - Volatility concerns with specific mitigation strategies
   - Sector concentration risks with recommended limits

4. PRIORITIZED ACTION ITEMS:
   - IMMEDIATE actions (1-7 days) marked as HIGH priority
   - SHORT-TERM actions (1-4 weeks) marked as MEDIUM priority  
   - LONG-TERM strategic moves (1-3 months) marked as LOW priority
   - Each action item must include expected impact on portfolio metrics

5. MARKET CONTEXT INTEGRATION (MANDATORY):
   - MUST reference current market indices performance and trend direction
   - Consider sector rotation opportunities based on today's sector performance data
   - Factor in market sentiment (bullish/bearish/neutral) for timing recommendations
   - Account for recent high-impact market events in stock-specific advice
   - Adjust risk levels based on current volatility index and market breadth
   - Use sector momentum scores to prioritize sector allocation changes
   - Consider trading session timing for execution recommendations
   - Reference analyst ratings and PE ratios for valuation context

MANDATORY OUTPUT FORMAT - MUST BE VALID JSON:
{
  "portfolio_health": {
    "overall_score": <number 0-100>,
    "risk_level": "<LOW/MEDIUM/HIGH>",
    "diversification_score": <number 0-1>,
    "concentration_risk": <number 0-1>,
    "performance_rating": "<EXCELLENT/GOOD/AVERAGE/POOR>",
    "key_strengths": ["<strength 1>", "<strength 2>"],
    "key_weaknesses": ["<weakness 1>", "<weakness 2>"]
  },
  "stock_recommendations": [
    {
      "symbol": "<EXACT_NSE_SYMBOL>",
      "current_allocation": <percentage>,
      "target_allocation": <percentage>,
      "action": "<BUY/SELL/HOLD/REDUCE/INCREASE>",
      "quantity_change": <shares_to_buy_or_sell>,
      "value_change": <rupees_amount>,
      "current_price": <estimated_current_price>,
      "reasoning": "<specific_market_based_reason>",
      "confidence": <0-100>,
      "priority": "<HIGH/MEDIUM/LOW>",
      "timeframe": "<IMMEDIATE/SHORT_TERM/LONG_TERM>",
      "expected_impact": "<specific_impact_on_portfolio>",
      "risk_warning": "<specific_risk_if_any>",
      "sector": "<stock_sector>"
    }
  ],
  "sector_analysis": {
    "current_sectors": [
      {"sector": "<sector_name>", "allocation": <percentage>, "performance": "<GOOD/AVERAGE/POOR>"}
    ],
    "sector_recommendations": [
      {"sector": "<sector_name>", "target_allocation": <percentage>, "action": "<INCREASE/DECREASE/MAINTAIN>", "reasoning": "<specific_reason>"}
    ],
    "diversification_score": <0-1>,
    "concentration_risks": ["<specific_concentration_risk_1>", "<specific_concentration_risk_2>"]
  },
  "risk_analysis": {
    "overall_risk_level": "<LOW/MEDIUM/HIGH>",
    "concentration_risk": <0-1>,
    "volatility_assessment": "<LOW/MEDIUM/HIGH>",
    "correlation_risks": [
      {"stocks": ["<symbol1>", "<symbol2>"], "correlation_level": "<HIGH/MEDIUM/LOW>", "risk_impact": "<description>"}
    ],
    "risk_mitigation_actions": [
      {"action": "<specific_action>", "expected_impact": "<impact_description>", "priority": "<HIGH/MEDIUM/LOW>"}
    ]
  },
  "action_items": [
    {
      "description": "<specific_actionable_item>",
      "priority": "<HIGH/MEDIUM/LOW>",
      "timeframe": "<IMMEDIATE/SHORT_TERM/LONG_TERM>",
      "expected_outcome": "<specific_expected_result>",
      "stocks_involved": ["<symbol1>", "<symbol2>"],
      "estimated_value": <rupees_amount>
    }
  ],
  "key_insights": [
    "<specific_actionable_insight_1>",
    "<specific_actionable_insight_2>",
    "<specific_actionable_insight_3>",
    "<specific_actionable_insight_4>",
    "<specific_actionable_insight_5>"
  ],
  "performance_prediction": {
    "expected_return_3m": <percentage>,
    "expected_return_6m": <percentage>,
    "expected_return_1y": <percentage>,
    "confidence_level": <0-100>,
    "key_assumptions": ["<assumption_1>", "<assumption_2>"]
  }
}

CRITICAL INSTRUCTIONS:
- Use ONLY exact NSE trading symbols (RELIANCE, TCS, HDFCBANK, INFY, ITC, etc.)
- Include specific percentages, rupee amounts, and share quantities
- Avoid generic advice - be specific about quantities and actions
- Reference current Indian market conditions in reasoning
- Ensure all recommendations are implementable with exact numbers
- Focus on actionable insights that can be executed immediately
- Consider the user's risk profile and investment timeline in recommendations
- Provide confidence scores based on market analysis and stock fundamentals
"""
    
    return portfolio_context + analysis_requirements

async def generate_ai_portfolio_analysis(
    portfolio_data: Dict[str, Any], 
    provider: str, 
    api_key: str, 
    user_id: str
) -> Optional[Dict[str, Any]]:
    """Generate enhanced AI portfolio analysis with specific recommendations and market context"""
    try:
        # Get user preferences for personalization
        user_preferences = None
        try:
            from .service import AIService
            ai_service = AIService()
            user_prefs = await ai_service.get_user_preferences(user_id)
            if user_prefs:
                user_preferences = {
                    'risk_tolerance': user_prefs.get('risk_tolerance', 'medium'),
                    'investment_timeline': user_prefs.get('trading_style', 'medium_term'),
                    'preferred_sectors': [],  # Can be enhanced later
                    'max_position_size': 15.0  # Default value
                }
        except Exception as e:
            logger.warning(f"Could not fetch user preferences: {e}")
        
        # Get comprehensive market context
        market_context = None
        try:
            from .market_context_service import market_context_service
            market_context = await market_context_service.get_comprehensive_market_context()
            logger.info(f"Retrieved market context with quality score: {market_context.get('data_quality', 0)}")
        except Exception as e:
            logger.warning(f"Could not fetch market context: {e}")
        
        # Create enhanced prompt with detailed context and market intelligence
        enhanced_prompt = await create_enhanced_portfolio_prompt(
            portfolio_data, user_id, user_preferences, market_context
        )
        
        logger.info(f"Generated enhanced prompt for user {user_id} with {len(portfolio_data.get('holdings', []))} holdings and market context")
        
        # Get AI analysis using enhanced prompt
        if provider == "openai":
            analysis = await call_openai_analysis(enhanced_prompt, api_key)
        elif provider == "claude":
            analysis = await call_claude_analysis(enhanced_prompt, api_key)
        elif provider == "gemini":
            analysis = await call_gemini_analysis(enhanced_prompt, api_key)
        else:
            return None
        
        if analysis:
            # Validate and enhance the response
            validated_analysis = validate_and_enhance_analysis(analysis, portfolio_data)
            
            return {
                "status": "success",
                "analysis_id": f"enhanced_{user_id}_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "analysis": validated_analysis,
                "provider_used": provider,
                "confidence_score": calculate_overall_confidence(validated_analysis),
                "fallback_mode": False,
                "enhanced_features": True,
                "market_context_used": market_context is not None,
                "market_data_quality": market_context.get('data_quality', 0) if market_context else 0,
                "market_session": market_context.get('trading_session', 'unknown') if market_context else 'unknown',
                "message": f"Enhanced AI analysis completed using {provider} with market intelligence"
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Enhanced AI analysis generation failed: {e}")
        return None
        
        # Call AI provider
        if provider == "openai":
            analysis = await call_openai_analysis(prompt, api_key)
        elif provider == "claude":
            analysis = await call_claude_analysis(prompt, api_key)
        elif provider == "gemini":
            analysis = await call_gemini_analysis(prompt, api_key)
        else:
            return None
        
        if analysis:
            return {
                "status": "success",
                "analysis_id": f"ai_{user_id}_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "provider_used": provider,
                "confidence_score": 0.85,
                "fallback_mode": False,
                "message": f"AI analysis completed using {provider}"
            }
        
        return None
        
    except Exception as e:
        logger.error(f"AI analysis generation failed: {e}")
        return None

async def call_openai_analysis(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Call OpenAI for enhanced portfolio analysis"""
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)
        
        system_message = """You are an expert portfolio analyst specializing in Indian stock markets with deep knowledge of NSE-listed companies. 

CRITICAL REQUIREMENTS:
1. Provide ONLY valid JSON responses - no markdown, no explanations, just pure JSON
2. Use exact NSE trading symbols (RELIANCE, TCS, HDFCBANK, INFY, ITC, etc.)
3. Include specific numbers: percentages, rupee amounts, share quantities
4. Base recommendations on current Indian market conditions
5. Consider sector rotation, market trends, and stock fundamentals
6. Provide actionable insights that can be implemented immediately
7. Ensure all numeric values are realistic and based on actual market data

Focus on practical, implementable recommendations with clear reasoning."""
        
        response = await client.chat.completions.create(
            model="gpt-4",  # Use GPT-4 for better analysis quality
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,  # Increased for detailed analysis
            temperature=0.2,  # Lower temperature for more consistent output
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        content = response.choices[0].message.content
        
        # Clean and parse JSON response
        try:
            cleaned_content = clean_ai_response_text(content)
            parsed_response = json.loads(cleaned_content)
            logger.info(f"OpenAI analysis successful, generated {len(parsed_response.get('stock_recommendations', []))} recommendations")
            return parsed_response
        except json.JSONDecodeError as e:
            logger.warning(f"OpenAI returned invalid JSON, attempting extraction: {e}")
            # Try advanced JSON extraction
            extracted_json = extract_json_from_text(content)
            if extracted_json:
                logger.info("Successfully extracted JSON from OpenAI response")
                return extracted_json
            else:
                logger.error("Failed to extract valid JSON from OpenAI response")
                return None
            
    except Exception as e:
        logger.error(f"OpenAI analysis failed: {e}")
        return None

async def call_claude_analysis(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Call Claude for enhanced portfolio analysis"""
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        enhanced_prompt = f"""You are an expert portfolio analyst specializing in Indian stock markets. Analyze the provided portfolio data and return ONLY a valid JSON response with specific, actionable recommendations.

CRITICAL REQUIREMENTS:
- Return ONLY valid JSON - no explanations, no markdown formatting
- Use exact NSE trading symbols (RELIANCE, TCS, HDFCBANK, etc.)
- Include specific numbers: percentages, rupee amounts, share quantities
- Base recommendations on current Indian market conditions
- Provide actionable insights with clear reasoning

{prompt}

Remember: Return ONLY the JSON object, nothing else."""
        
        response = await client.messages.create(
            model="claude-3-sonnet-20240229",  # Use Sonnet for better analysis
            max_tokens=3000,  # Increased for detailed analysis
            messages=[
                {"role": "user", "content": enhanced_prompt}
            ]
        )
        
        content = response.content[0].text
        
        # Clean and parse JSON response
        try:
            cleaned_content = clean_ai_response_text(content)
            parsed_response = json.loads(cleaned_content)
            logger.info(f"Claude analysis successful, generated {len(parsed_response.get('stock_recommendations', []))} recommendations")
            return parsed_response
        except json.JSONDecodeError as e:
            logger.warning(f"Claude returned invalid JSON, attempting extraction: {e}")
            # Try advanced JSON extraction
            extracted_json = extract_json_from_text(content)
            if extracted_json:
                logger.info("Successfully extracted JSON from Claude response")
                return extracted_json
            else:
                logger.error("Failed to extract valid JSON from Claude response")
                return None
            
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}")
        return None

async def call_gemini_analysis(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Call Gemini for enhanced portfolio analysis"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Configure model for JSON output
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 3000,
        }
        
        model = genai.GenerativeModel(
            model_name='gemini-pro',
            generation_config=generation_config
        )
        
        enhanced_prompt = f"""You are an expert portfolio analyst specializing in Indian stock markets. Analyze the provided portfolio and return a valid JSON response with specific recommendations.

CRITICAL INSTRUCTIONS:
- Return ONLY valid JSON format - no explanations or markdown
- Use exact NSE trading symbols (RELIANCE, TCS, HDFCBANK, INFY, ITC, etc.)
- Include specific numbers: percentages, rupee amounts, share quantities
- Base analysis on current Indian market conditions and sector trends
- Provide actionable recommendations with clear reasoning

{prompt}

Return only the JSON object with the required structure."""
        
        response = await asyncio.to_thread(
            model.generate_content, 
            enhanced_prompt
        )
        
        content = response.text
        
        # Clean and parse JSON response
        try:
            cleaned_content = clean_ai_response_text(content)
            parsed_response = json.loads(cleaned_content)
            logger.info(f"Gemini analysis successful, generated {len(parsed_response.get('stock_recommendations', []))} recommendations")
            return parsed_response
        except json.JSONDecodeError as e:
            logger.warning(f"Gemini returned invalid JSON, attempting extraction: {e}")
            # Try advanced JSON extraction
            extracted_json = extract_json_from_text(content)
            if extracted_json:
                logger.info("Successfully extracted JSON from Gemini response")
                return extracted_json
            else:
                logger.error("Failed to extract valid JSON from Gemini response")
                return None
            
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return None

def validate_required_fields(data: Dict[str, Any], required_fields: Dict[str, type], section_name: str) -> Dict[str, Any]:
    """Validate required fields in a data section"""
    validated_data = {}
    
    for field, expected_type in required_fields.items():
        if field in data:
            try:
                if expected_type == int:
                    validated_data[field] = int(data[field])
                elif expected_type == float:
                    validated_data[field] = float(data[field])
                elif expected_type == str:
                    validated_data[field] = str(data[field])
                elif expected_type == list:
                    validated_data[field] = list(data[field]) if isinstance(data[field], list) else []
                else:
                    validated_data[field] = data[field]
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid type for {field} in {section_name}: {e}")
                validated_data[field] = get_default_value(expected_type)
        else:
            validated_data[field] = get_default_value(expected_type)
    
    return validated_data

def get_default_value(expected_type: type):
    """Get default value for a given type"""
    if expected_type == int:
        return 0
    elif expected_type == float:
        return 0.0
    elif expected_type == str:
        return ""
    elif expected_type == list:
        return []
    elif expected_type == dict:
        return {}
    else:
        return None

def validate_stock_recommendation(rec: Dict[str, Any], portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and enhance a single stock recommendation"""
    holdings = portfolio_data.get("holdings", [])
    total_value = portfolio_data.get("total_value", 0)
    
    # Required fields for stock recommendations
    required_fields = {
        "symbol": str,
        "current_allocation": float,
        "target_allocation": float,
        "action": str,
        "quantity_change": int,
        "value_change": float,
        "current_price": float,
        "reasoning": str,
        "confidence": int,
        "priority": str,
        "timeframe": str
    }
    
    validated_rec = validate_required_fields(rec, required_fields, "stock_recommendation")
    
    # Find matching holding for additional context
    matching_holding = None
    for holding in holdings:
        if holding.get('tradingsymbol', holding.get('symbol', '')) == validated_rec["symbol"]:
            matching_holding = holding
            break
    
    # Enhance with calculated values if missing
    if validated_rec["current_allocation"] == 0.0 and matching_holding:
        current_value = matching_holding.get('current_value', 0)
        validated_rec["current_allocation"] = (current_value / total_value * 100) if total_value > 0 else 0
    
    if validated_rec["current_price"] == 0.0 and matching_holding:
        quantity = matching_holding.get('quantity', 0)
        current_value = matching_holding.get('current_value', 0)
        validated_rec["current_price"] = current_value / quantity if quantity > 0 else 0
    
    # Validate action types
    valid_actions = ["BUY", "SELL", "HOLD", "REDUCE", "INCREASE"]
    if validated_rec["action"] not in valid_actions:
        validated_rec["action"] = "HOLD"
    
    # Validate priority levels
    valid_priorities = ["HIGH", "MEDIUM", "LOW"]
    if validated_rec["priority"] not in valid_priorities:
        validated_rec["priority"] = "MEDIUM"
    
    # Validate timeframes
    valid_timeframes = ["IMMEDIATE", "SHORT_TERM", "LONG_TERM"]
    if validated_rec["timeframe"] not in valid_timeframes:
        validated_rec["timeframe"] = "SHORT_TERM"
    
    # Validate confidence score
    validated_rec["confidence"] = min(100, max(0, validated_rec["confidence"]))
    
    # Validate allocation percentages
    validated_rec["current_allocation"] = min(100.0, max(0.0, validated_rec["current_allocation"]))
    validated_rec["target_allocation"] = min(100.0, max(0.0, validated_rec["target_allocation"]))
    
    # Add additional fields if missing
    if "expected_impact" not in validated_rec:
        validated_rec["expected_impact"] = f"Adjust {validated_rec['symbol']} allocation from {validated_rec['current_allocation']:.1f}% to {validated_rec['target_allocation']:.1f}%"
    
    if "risk_warning" not in validated_rec:
        if validated_rec["target_allocation"] > 15.0:
            validated_rec["risk_warning"] = "High concentration risk - position exceeds 15% of portfolio"
        else:
            validated_rec["risk_warning"] = "Standard market risk applies"
    
    if "sector" not in validated_rec:
        validated_rec["sector"] = get_stock_sector(validated_rec["symbol"])
    
    return validated_rec

def get_stock_sector(symbol: str) -> str:
    """Get sector for a stock symbol (basic mapping for Indian stocks)"""
    sector_mapping = {
        "RELIANCE": "Energy",
        "TCS": "Technology",
        "HDFCBANK": "Banking",
        "INFY": "Technology",
        "ITC": "FMCG",
        "HINDUNILVR": "FMCG",
        "SBIN": "Banking",
        "ICICIBANK": "Banking",
        "BHARTIARTL": "Telecom",
        "KOTAKBANK": "Banking",
        "LT": "Infrastructure",
        "ASIANPAINT": "Paints",
        "MARUTI": "Automotive",
        "WIPRO": "Technology",
        "HCLTECH": "Technology",
        "TECHM": "Technology",
        "TITAN": "Consumer Goods",
        "NESTLEIND": "FMCG",
        "ULTRACEMCO": "Cement",
        "POWERGRID": "Utilities"
    }
    return sector_mapping.get(symbol, "Others")

def calculate_overall_confidence(analysis: Dict[str, Any]) -> float:
    """Calculate overall confidence score for the analysis"""
    try:
        confidence_scores = []
        
        # Portfolio health confidence
        portfolio_health = analysis.get('portfolio_health', {})
        if 'overall_score' in portfolio_health:
            confidence_scores.append(portfolio_health['overall_score'] / 100.0)
        
        # Stock recommendations confidence
        stock_recs = analysis.get('stock_recommendations', [])
        if stock_recs:
            rec_confidences = [rec.get('confidence', 70) / 100.0 for rec in stock_recs]
            if rec_confidences:
                confidence_scores.append(sum(rec_confidences) / len(rec_confidences))
        
        # Performance prediction confidence
        perf_pred = analysis.get('performance_prediction', {})
        if 'confidence_level' in perf_pred:
            confidence_scores.append(perf_pred['confidence_level'] / 100.0)
        
        # Calculate weighted average
        if confidence_scores:
            return round(sum(confidence_scores) / len(confidence_scores), 2)
        else:
            return 0.75  # Default confidence
            
    except Exception as e:
        logger.warning(f"Failed to calculate confidence score: {e}")
        return 0.70  # Fallback confidence

def validate_and_enhance_analysis(analysis: Dict[str, Any], portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Comprehensive validation and enhancement of AI analysis response"""
    try:
        # Ensure required structure exists
        if not isinstance(analysis, dict):
            logger.error("Analysis must be a dictionary")
            return create_fallback_analysis_structure()
        
        validated_analysis = {}
        
        # 1. Validate portfolio_health section
        portfolio_health_fields = {
            "overall_score": int,
            "risk_level": str,
            "diversification_score": float,
            "concentration_risk": float,
            "performance_rating": str,
            "key_strengths": list,
            "key_weaknesses": list
        }
        
        if "portfolio_health" in analysis:
            validated_analysis["portfolio_health"] = validate_required_fields(
                analysis["portfolio_health"], portfolio_health_fields, "portfolio_health"
            )
        else:
            validated_analysis["portfolio_health"] = {
                "overall_score": 75,
                "risk_level": "MEDIUM",
                "diversification_score": 0.7,
                "concentration_risk": 0.3,
                "performance_rating": "GOOD",
                "key_strengths": ["Diversified holdings", "Profitable positions"],
                "key_weaknesses": ["Concentration risk", "Sector imbalance"]
            }
        
        # Validate risk level
        valid_risk_levels = ["LOW", "MEDIUM", "HIGH"]
        if validated_analysis["portfolio_health"]["risk_level"] not in valid_risk_levels:
            validated_analysis["portfolio_health"]["risk_level"] = "MEDIUM"
        
        # Validate performance rating
        valid_ratings = ["EXCELLENT", "GOOD", "AVERAGE", "POOR"]
        if validated_analysis["portfolio_health"]["performance_rating"] not in valid_ratings:
            validated_analysis["portfolio_health"]["performance_rating"] = "GOOD"
        
        # Ensure score is within bounds
        validated_analysis["portfolio_health"]["overall_score"] = min(100, max(0, validated_analysis["portfolio_health"]["overall_score"]))
        
        # 2. Validate stock_recommendations section
        validated_analysis["stock_recommendations"] = []
        if "stock_recommendations" in analysis and isinstance(analysis["stock_recommendations"], list):
            for rec in analysis["stock_recommendations"]:
                if isinstance(rec, dict) and "symbol" in rec:
                    validated_rec = validate_stock_recommendation(rec, portfolio_data)
                    validated_analysis["stock_recommendations"].append(validated_rec)
        
        # Ensure we have at least some recommendations for major holdings
        if len(validated_analysis["stock_recommendations"]) == 0:
            validated_analysis["stock_recommendations"] = generate_basic_recommendations(portfolio_data)
        
        # 3. Validate sector_analysis section
        sector_analysis_fields = {
            "current_sectors": list,
            "sector_recommendations": list,
            "diversification_score": float,
            "concentration_risks": list
        }
        
        if "sector_analysis" in analysis:
            validated_analysis["sector_analysis"] = validate_required_fields(
                analysis["sector_analysis"], sector_analysis_fields, "sector_analysis"
            )
        else:
            validated_analysis["sector_analysis"] = generate_sector_analysis(portfolio_data)
        
        # 4. Validate risk_analysis section
        risk_analysis_fields = {
            "overall_risk_level": str,
            "concentration_risk": float,
            "volatility_assessment": str,
            "correlation_risks": list,
            "risk_mitigation_actions": list
        }
        
        if "risk_analysis" in analysis:
            validated_analysis["risk_analysis"] = validate_required_fields(
                analysis["risk_analysis"], risk_analysis_fields, "risk_analysis"
            )
        else:
            validated_analysis["risk_analysis"] = {
                "overall_risk_level": "MEDIUM",
                "concentration_risk": 0.3,
                "volatility_assessment": "MEDIUM",
                "correlation_risks": [],
                "risk_mitigation_actions": []
            }
        
        # 5. Validate action_items section
        if "action_items" not in analysis or not isinstance(analysis["action_items"], list):
            validated_analysis["action_items"] = generate_action_items(validated_analysis["stock_recommendations"])
        else:
            validated_analysis["action_items"] = analysis["action_items"]
        
        # 6. Validate key_insights section
        if "key_insights" not in analysis or not isinstance(analysis["key_insights"], list):
            validated_analysis["key_insights"] = generate_key_insights(portfolio_data, validated_analysis)
        else:
            validated_analysis["key_insights"] = analysis["key_insights"][:5]  # Limit to 5 insights
        
        # 7. Validate performance_prediction section
        if "performance_prediction" in analysis:
            prediction_fields = {
                "expected_return_3m": float,
                "expected_return_6m": float,
                "expected_return_1y": float,
                "confidence_level": int,
                "key_assumptions": list
            }
            validated_analysis["performance_prediction"] = validate_required_fields(
                analysis["performance_prediction"], prediction_fields, "performance_prediction"
            )
        else:
            validated_analysis["performance_prediction"] = {
                "expected_return_3m": 5.0,
                "expected_return_6m": 10.0,
                "expected_return_1y": 15.0,
                "confidence_level": 70,
                "key_assumptions": ["Market remains stable", "No major economic disruptions"]
            }
        
        logger.info(f"Analysis validation completed successfully with {len(validated_analysis['stock_recommendations'])} recommendations")
        return validated_analysis
        
    except Exception as e:
        logger.error(f"Analysis validation failed: {e}")
        return create_fallback_analysis_structure()

def create_fallback_analysis_structure() -> Dict[str, Any]:
    """Create fallback analysis structure when validation fails"""
    return {
        "portfolio_health": {
            "overall_score": 70,
            "risk_level": "MEDIUM",
            "diversification_score": 0.7,
            "concentration_risk": 0.3,
            "performance_rating": "AVERAGE",
            "key_strengths": ["Portfolio has some diversification"],
            "key_weaknesses": ["Analysis validation failed - limited insights available"]
        },
        "stock_recommendations": [],
        "sector_analysis": {
            "current_sectors": [],
            "sector_recommendations": [],
            "diversification_score": 0.7,
            "concentration_risks": []
        },
        "risk_analysis": {
            "overall_risk_level": "MEDIUM",
            "concentration_risk": 0.3,
            "volatility_assessment": "MEDIUM",
            "correlation_risks": [],
            "risk_mitigation_actions": []
        },
        "action_items": [],
        "key_insights": ["Analysis validation encountered issues - using fallback structure"],
        "performance_prediction": {
            "expected_return_3m": 0.0,
            "expected_return_6m": 0.0,
            "expected_return_1y": 0.0,
            "confidence_level": 0,
            "key_assumptions": ["Fallback mode - no predictions available"]
        }
    }

def generate_basic_recommendations(portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate basic recommendations when AI doesn't provide any"""
    recommendations = []
    holdings = portfolio_data.get("holdings", [])
    total_value = portfolio_data.get("total_value", 0)
    
    for holding in holdings[:5]:  # Top 5 holdings
        symbol = holding.get('tradingsymbol', holding.get('symbol', 'Unknown'))
        current_value = holding.get('current_value', 0)
        allocation = (current_value / total_value * 100) if total_value > 0 else 0
        
        if allocation > 20:  # High concentration
            action = "REDUCE"
            target_allocation = 15.0
        elif allocation < 5:  # Low allocation
            action = "INCREASE"
            target_allocation = 8.0
        else:
            action = "HOLD"
            target_allocation = allocation
        
        recommendations.append({
            "symbol": symbol,
            "current_allocation": allocation,
            "target_allocation": target_allocation,
            "action": action,
            "quantity_change": 0,
            "value_change": 0,
            "current_price": holding.get('last_price', 0),
            "reasoning": f"Basic recommendation based on allocation analysis",
            "confidence": 60,
            "priority": "MEDIUM",
            "timeframe": "SHORT_TERM",
            "expected_impact": f"Optimize {symbol} allocation",
            "risk_warning": "Standard market risk applies",
            "sector": get_stock_sector(symbol)
        })
    
    return recommendations

def generate_sector_analysis(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate basic sector analysis"""
    holdings = portfolio_data.get("holdings", [])
    total_value = portfolio_data.get("total_value", 0)
    
    sector_allocation = {}
    for holding in holdings:
        symbol = holding.get('tradingsymbol', holding.get('symbol', 'Unknown'))
        current_value = holding.get('current_value', 0)
        allocation = (current_value / total_value * 100) if total_value > 0 else 0
        sector = get_stock_sector(symbol)
        
        if sector in sector_allocation:
            sector_allocation[sector] += allocation
        else:
            sector_allocation[sector] = allocation
    
    current_sectors = [
        {"sector": sector, "allocation": allocation, "performance": "AVERAGE"}
        for sector, allocation in sector_allocation.items()
    ]
    
    return {
        "current_sectors": current_sectors,
        "sector_recommendations": [],
        "diversification_score": 0.7,
        "concentration_risks": []
    }

def generate_action_items(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate action items from recommendations"""
    action_items = []
    
    high_priority_recs = [r for r in recommendations if r.get("priority") == "HIGH"]
    if high_priority_recs:
        action_items.append({
            "description": f"Review {len(high_priority_recs)} high-priority recommendations",
            "priority": "HIGH",
            "timeframe": "IMMEDIATE",
            "expected_outcome": "Reduce portfolio risk and improve allocation",
            "stocks_involved": [r["symbol"] for r in high_priority_recs],
            "estimated_value": sum(abs(r.get("value_change", 0)) for r in high_priority_recs)
        })
    
    return action_items

def generate_key_insights(portfolio_data: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
    """Generate key insights based on portfolio and analysis"""
    insights = []
    
    total_value = portfolio_data.get("total_value", 0)
    holdings_count = len(portfolio_data.get("holdings", []))
    recommendations_count = len(analysis.get("stock_recommendations", []))
    
    insights.append(f"Portfolio contains {holdings_count} holdings worth ₹{total_value:,.0f}")
    insights.append(f"Generated {recommendations_count} specific stock recommendations")
    
    # Add concentration insights
    holdings = portfolio_data.get("holdings", [])
    if holdings:
        max_holding = max(holdings, key=lambda h: h.get('current_value', 0))
        max_symbol = max_holding.get('tradingsymbol', max_holding.get('symbol', 'Unknown'))
        max_allocation = (max_holding.get('current_value', 0) / total_value * 100) if total_value > 0 else 0
        
        if max_allocation > 20:
            insights.append(f"{max_symbol} represents {max_allocation:.1f}% of portfolio - consider reducing concentration")
        else:
            insights.append(f"Largest holding {max_symbol} at {max_allocation:.1f}% shows good diversification")
    
    # Add performance insights
    total_pnl = sum(h.get('pnl', 0) for h in holdings)
    if total_pnl > 0:
        insights.append(f"Portfolio showing positive P&L of ₹{total_pnl:,.0f}")
    else:
        insights.append("Portfolio performance needs improvement - consider rebalancing")
    
    return insights[:5]  # Limit to 5 insights

def calculate_overall_confidence(analysis: Dict[str, Any]) -> float:
    """Calculate overall confidence score for the analysis"""
    try:
        recommendations = analysis.get("stock_recommendations", [])
        if not recommendations:
            return 0.7  # Default confidence
        
        # Calculate average confidence from recommendations
        total_confidence = sum(rec.get("confidence", 75) for rec in recommendations)
        avg_confidence = total_confidence / len(recommendations) / 100  # Convert to 0-1 scale
        
        # Factor in number of recommendations (more recommendations = higher confidence)
        recommendation_factor = min(1.0, len(recommendations) / 5)  # Optimal around 5 recommendations
        
        # Combine factors
        overall_confidence = (avg_confidence * 0.7) + (recommendation_factor * 0.3)
        
        return min(1.0, max(0.0, overall_confidence))
        
    except Exception as e:
        logger.error(f"Confidence calculation failed: {e}")
        return 0.7

async def generate_fallback_analysis(portfolio_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Generate fallback analysis when AI is not available"""
    total_value = portfolio_data.get("total_value", 0)
    holdings = portfolio_data.get("holdings", [])
    num_holdings = len(holdings)
    
    return {
        "status": "success",
        "analysis_id": f"fallback_{user_id}_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat(),
        "analysis": {
            "portfolio_health": {
                "overall_score": min(85.0, max(60.0, 75.0 + (num_holdings - 5) * 2)),
                "risk_level": "MEDIUM" if num_holdings >= 5 else "HIGH",
                "diversification_score": min(0.9, num_holdings * 0.15),
                "concentration_risk": max(0.1, 1.0 - (num_holdings * 0.1))
            },
            "risk_analysis": {
                "overall_risk_level": "medium" if num_holdings >= 5 else "high",
                "concentration_risk": max(0.1, 1.0 - (num_holdings * 0.1)),
                "volatility": 0.25,
                "beta": 1.1
            },
            "recommendations": [
                {
                    "type": "diversification",
                    "symbol": "PORTFOLIO",
                    "action": "rebalance",
                    "reason": f"Portfolio has {num_holdings} holdings. Consider {'maintaining' if num_holdings >= 8 else 'adding'} diversification.",
                    "confidence": 0.8,
                    "target_allocation": 0.1
                }
            ],
            "key_insights": [
                f"Portfolio contains {num_holdings} holdings with total value of ₹{total_value:,.0f}",
                "Diversification can be improved by adding holdings from different sectors",
                "Regular rebalancing recommended to maintain target allocations",
                "Consider risk assessment based on individual stock volatility"
            ]
        },
        "fallback_mode": True,
        "message": "Analysis generated in fallback mode - configure AI providers for enhanced analysis"
    }

async def store_analysis_for_tracking(user_id: str, analysis_result: Dict[str, Any], provider: str) -> None:
    """Store analysis result for performance tracking"""
    try:
        # Import here to avoid circular imports
        from app.database.service import get_db_connection
        
        analysis_data = {
            "analysis_id": analysis_result.get("analysis_id"),
            "provider_used": provider,
            "confidence_score": analysis_result.get("confidence_score", 0.0),
            "recommendations_count": len(analysis_result.get("analysis", {}).get("stock_recommendations", [])),
            "enhanced_features": analysis_result.get("enhanced_features", False)
        }
        
        # Store in database for tracking
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_analysis_results 
            (user_id, analysis_type, symbols, input_data, analysis_result, provider_used, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            "enhanced_portfolio",
            None,  # Portfolio-wide analysis
            json.dumps({"total_recommendations": analysis_data["recommendations_count"]}),
            json.dumps(analysis_data),
            provider,
            analysis_data["confidence_score"]
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored enhanced analysis for tracking: user={user_id}, provider={provider}")
        
    except Exception as e:
        logger.error(f"Failed to store analysis for tracking: {e}")

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from text response using multiple strategies"""
    import re
    
    # Strategy 1: Look for JSON object wrapped in code blocks
    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    code_match = re.search(code_block_pattern, text, re.DOTALL | re.IGNORECASE)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Strategy 2: Look for JSON object in the text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    json_matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in json_matches:
        try:
            # Try to parse each potential JSON match
            parsed = json.loads(match)
            # Validate it looks like our expected structure
            if isinstance(parsed, dict) and any(key in parsed for key in ['portfolio_health', 'stock_recommendations', 'analysis']):
                return parsed
        except json.JSONDecodeError:
            continue
    
    # Strategy 3: Look for the largest JSON-like structure
    brace_pattern = r'\{.*\}'
    brace_match = re.search(brace_pattern, text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass
    
    return None

def clean_ai_response_text(text: str) -> str:
    """Clean AI response text to improve JSON parsing"""
    # Remove common AI response prefixes/suffixes
    prefixes_to_remove = [
        "Here's the analysis:",
        "Based on the portfolio data:",
        "Here is the JSON response:",
        "```json",
        "```"
    ]
    
    suffixes_to_remove = [
        "```",
        "I hope this helps!",
        "Let me know if you need any clarification."
    ]
    
    cleaned_text = text.strip()
    
    # Remove prefixes
    for prefix in prefixes_to_remove:
        if cleaned_text.lower().startswith(prefix.lower()):
            cleaned_text = cleaned_text[len(prefix):].strip()
    
    # Remove suffixes
    for suffix in suffixes_to_remove:
        if cleaned_text.lower().endswith(suffix.lower()):
            cleaned_text = cleaned_text[:-len(suffix)].strip()
    
    return cleaned_text