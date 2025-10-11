const express = require('express');
const router = express.Router();
const { getAIChatService } = require('../services/aiChatService');

/**
 * AI Chat Routes
 * Handles conversational AI interactions
 */

/**
 * POST /api/v2/ai/chat
 * Send message to AI assistant
 * 
 * Body:
 * {
 *   message: string,
 *   context: {
 *     page: string,
 *     strategyId?: number,
 *     executionId?: number,
 *     holdingSymbol?: string,
 *     userId?: number
 *   },
 *   history?: Array<{role: string, content: string}>
 * }
 */
router.post('/', async (req, res) => {
  try {
    const { message, context = {}, history = [] } = req.body;

    // Validation
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Message is required and must be a non-empty string'
      });
    }

    if (message.length > 1000) {
      return res.status(400).json({
        success: false,
        error: 'Message too long (max 1000 characters)'
      });
    }

    // Get user ID (from session or context)
    const userId = context.userId || req.session?.userId || req.user?.id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required'
      });
    }

    console.log('[AIChatRoutes] Processing message:', {
      userId,
      messageLength: message.length,
      context: context.page,
      historyLength: history.length
    });

    // Get chat service
    const chatService = getAIChatService();

    // Process message
    const result = await chatService.processMessage({
      userId,
      message: message.trim(),
      context,
      history: history.slice(-5) // Keep last 5 messages for context
    });

    if (result.success) {
      console.log('[AIChatRoutes] Message processed successfully');
      
      return res.status(200).json({
        success: true,
        response: result.response,
        suggestions: result.suggestions || [],
        attribution: result.attribution || {}
      });
    } else {
      console.error('[AIChatRoutes] Message processing failed:', result.error);
      
      return res.status(500).json({
        success: false,
        error: result.error || 'Failed to process message',
        response: result.response // Fallback response
      });
    }
  } catch (error) {
    console.error('[AIChatRoutes] Unexpected error:', error);
    
    return res.status(500).json({
      success: false,
      error: 'Internal server error',
      response: "I'm experiencing technical difficulties. Please try again in a moment."
    });
  }
});

/**
 * GET /api/v2/ai/chat/health
 * Check AI chat service health
 */
router.get('/health', async (req, res) => {
  try {
    const chatService = getAIChatService();
    
    return res.status(200).json({
      success: true,
      status: 'operational',
      service: 'AI Chat',
      initialized: !!chatService
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      status: 'error',
      error: error.message
    });
  }
});

/**
 * DELETE /api/v2/ai/chat/history
 * Clear chat history (client-side only, this is just for completeness)
 */
router.delete('/history', async (req, res) => {
  try {
    // This is handled client-side via localStorage
    // This endpoint is here for future server-side history if needed
    
    return res.status(200).json({
      success: true,
      message: 'Chat history cleared (client-side)'
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;

