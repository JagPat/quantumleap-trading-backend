"""
Simple Analysis Router - Direct AI Integration
Bypasses complex analysis engine for immediate AI portfolio analysis
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any
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
        
        # Check if user has valid AI providers
        has_openai = user_preferences and user_preferences.get('has_openai_key', False)
        has_claude = user_preferences and user_preferences.get('has_claude_key', False)
        has_gemini = user_preferences and user_preferences.get('has_gemini_key', False)
        
        if not (has_openai or has_claude or has_gemini):
            logger.info(f"No valid AI providers for user {user_id}")
            return await generate_fallback_analysis(portfolio_data, user_id)
        
        # Try to use real AI analysis
        try:
            logger.info(f"Attempting real AI analysis for user {user_id}")
            
            # Get AI provider
            if has_openai:
                provider = "openai"
                api_key = user_preferences.get('openai_api_key')
            elif has_claude:
                provider = "claude"
                api_key = user_preferences.get('claude_api_key')
            else:
                provider = "gemini"
                api_key = user_preferences.get('gemini_api_key')
            
            # Generate AI analysis
            analysis_result = await generate_ai_portfolio_analysis(
                portfolio_data, provider, api_key, user_id
            )
            
            if analysis_result:
                logger.info(f"Real AI analysis successful for user {user_id}")
                return analysis_result
            else:
                logger.warning(f"AI analysis failed, using fallback for user {user_id}")
                return await generate_fallback_analysis(portfolio_data, user_id)
                
        except Exception as ai_error:
            logger.error(f"AI analysis error: {ai_error}")
            return await generate_fallback_analysis(portfolio_data, user_id)
            
    except Exception as e:
        logger.error(f"Simple portfolio analysis failed: {e}")
        return await generate_fallback_analysis(portfolio_data, user_id)

async def generate_ai_portfolio_analysis(
    portfolio_data: Dict[str, Any], 
    provider: str, 
    api_key: str, 
    user_id: str
) -> Optional[Dict[str, Any]]:
    """Generate real AI portfolio analysis"""
    try:
        # Prepare portfolio summary for AI
        total_value = portfolio_data.get("total_value", 0)
        holdings = portfolio_data.get("holdings", [])
        
        portfolio_summary = f"""
Portfolio Analysis Request:
Total Value: ₹{total_value:,.2f}
Number of Holdings: {len(holdings)}

Holdings:
"""
        for holding in holdings[:10]:  # Limit to top 10 holdings
            symbol = holding.get('symbol', 'Unknown')
            value = holding.get('current_value', 0)
            allocation = (value / total_value * 100) if total_value > 0 else 0
            portfolio_summary += f"- {symbol}: ₹{value:,.2f} ({allocation:.1f}%)\n"
        
        # Create AI prompt
        prompt = f"""
Analyze this Indian stock portfolio and provide insights in JSON format:

{portfolio_summary}

Please provide analysis in this exact JSON structure:
{{
  "portfolio_health": {{
    "overall_score": <number 0-100>,
    "risk_level": "<LOW/MEDIUM/HIGH>",
    "diversification_score": <number 0-1>,
    "concentration_risk": <number 0-1>
  }},
  "risk_analysis": {{
    "overall_risk_level": "<low/medium/high>",
    "concentration_risk": <number 0-1>,
    "volatility": <number 0-1>,
    "beta": <number>
  }},
  "recommendations": [
    {{
      "type": "<string>",
      "symbol": "<string>",
      "action": "<buy/sell/hold/reduce>",
      "reason": "<string>",
      "confidence": <number 0-1>,
      "target_allocation": <number 0-1>
    }}
  ],
  "key_insights": [
    "<insight 1>",
    "<insight 2>",
    "<insight 3>"
  ]
}}

Focus on Indian market context, sector diversification, and practical recommendations.
"""
        
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
    """Call OpenAI for portfolio analysis"""
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional portfolio analyst specializing in Indian stock markets. Provide detailed, actionable analysis in JSON format."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        
        # Try to parse JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON from response if wrapped in text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
            
    except Exception as e:
        logger.error(f"OpenAI analysis failed: {e}")
        return None

async def call_claude_analysis(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Call Claude for portfolio analysis"""
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text
        
        # Try to parse JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON from response if wrapped in text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
            
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}")
        return None

async def call_gemini_analysis(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Call Gemini for portfolio analysis"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-pro')
        response = await asyncio.to_thread(
            model.generate_content, 
            prompt
        )
        
        content = response.text
        
        # Try to parse JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON from response if wrapped in text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
            
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return None

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