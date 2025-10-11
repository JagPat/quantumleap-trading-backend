/**
 * Research API Routes
 * Exposes research data, market regime, and learning insights to frontend
 */

const express = require('express');
const router = express.Router();
const ResearchIngestionService = require('../services/researchIngestionService');
const MarketRegimeAnalyzer = require('../services/marketRegimeAnalyzer');
const FeedbackIntegrationService = require('../services/feedbackIntegrationService');
const DailyLearningJob = require('../jobs/dailyLearningJob');

/**
 * GET /api/modules/ai/research/:symbol
 * Get research data for a specific symbol
 */
router.get('/:symbol', async (req, res) => {
  try {
    const { symbol } = req.params;
    const lookbackDays = parseInt(req.query.lookback) || 7;
    
    const researchService = new ResearchIngestionService();
    const research = await researchService.getRelevantResearch(symbol, lookbackDays);
    
    res.json({
      success: true,
      data: {
        symbol,
        lookbackDays,
        research,
        lastUpdated: research.lastUpdated || new Date().toISOString()
      }
    });
    
  } catch (error) {
    console.error('[AI/Research] Error fetching research:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch research data'
    });
  }
});

/**
 * GET /api/modules/ai/research/market-regime/current
 * Get current market regime
 */
router.get('/market-regime/current', async (req, res) => {
  try {
    const regimeAnalyzer = new MarketRegimeAnalyzer();
    const regime = await regimeAnalyzer.getActiveRegime();
    
    res.json({
      success: true,
      data: regime
    });
    
  } catch (error) {
    console.error('[AI/Research] Error fetching regime:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch market regime'
    });
  }
});

/**
 * POST /api/modules/ai/research/market-regime/detect
 * Trigger fresh regime detection (admin/testing)
 */
router.post('/market-regime/detect', async (req, res) => {
  try {
    const regimeAnalyzer = new MarketRegimeAnalyzer();
    const regime = await regimeAnalyzer.detectCurrentRegime();
    
    res.json({
      success: true,
      message: 'Market regime detected successfully',
      data: regime
    });
    
  } catch (error) {
    console.error('[AI/Research] Error detecting regime:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to detect market regime'
    });
  }
});

/**
 * GET /api/modules/ai/research/learnings
 * Get AI learning insights
 */
router.get('/learnings', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const { symbol, taskType, limit } = req.query;
    
    const feedbackService = new FeedbackIntegrationService();
    const learnings = await feedbackService.getContextualLearnings(
      symbol || null,
      taskType || 'general'
    );
    
    res.json({
      success: true,
      data: {
        learnings: learnings.slice(0, parseInt(limit) || 10),
        total: learnings.length
      }
    });
    
  } catch (error) {
    console.error('[AI/Research] Error fetching learnings:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch learning insights'
    });
  }
});

/**
 * POST /api/modules/ai/research/ingest
 * Trigger on-demand research ingestion (admin/testing)
 */
router.post('/ingest', async (req, res) => {
  try {
    const { symbols } = req.body;
    
    if (!symbols || !Array.isArray(symbols)) {
      return res.status(400).json({
        success: false,
        message: 'Symbols array required'
      });
    }
    
    const researchService = new ResearchIngestionService();
    const result = await researchService.ingestDailyResearch(symbols);
    
    res.json({
      success: true,
      message: 'Research ingestion completed',
      data: result
    });
    
  } catch (error) {
    console.error('[AI/Research] Error ingesting research:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to ingest research data'
    });
  }
});

/**
 * POST /api/modules/ai/research/learning-job/run
 * Trigger daily learning job on-demand (admin/testing)
 */
router.post('/learning-job/run', async (req, res) => {
  try {
    const { symbols, lookbackDays } = req.body;
    
    const job = new DailyLearningJob();
    const report = await job.runOnDemand({ symbols, lookbackDays });
    
    res.json({
      success: true,
      message: 'Learning job completed',
      data: report
    });
    
  } catch (error) {
    console.error('[AI/Research] Error running learning job:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to run learning job'
    });
  }
});

/**
 * GET /api/modules/ai/research/learning-job/history
 * Get learning job execution history
 */
router.get('/learning-job/history', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 10;
    
    const job = new DailyLearningJob();
    const history = await job.getExecutionHistory(limit);
    
    res.json({
      success: true,
      data: {
        history,
        total: history.length
      }
    });
    
  } catch (error) {
    console.error('[AI/Research] Error fetching job history:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch job history'
    });
  }
});

/**
 * GET /api/modules/ai/research/macro
 * Get current macroeconomic context
 */
router.get('/macro', async (req, res) => {
  try {
    const researchService = new ResearchIngestionService();
    const macroContext = await researchService.getMacroContext();
    
    res.json({
      success: true,
      data: macroContext
    });
    
  } catch (error) {
    console.error('[AI/Research] Error fetching macro data:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch macro data'
    });
  }
});

module.exports = router;

