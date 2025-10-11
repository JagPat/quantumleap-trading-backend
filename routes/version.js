const express = require('express');
const router = express.Router();

// Version endpoint for rock solid audit enforcement
router.get('/version', (req, res) => {
  try {
    // Try multiple environment variable sources for commit hash
    const commitSha = process.env.RAILWAY_GIT_COMMIT_SHA || 
                      process.env.COMMIT_SHA || 
                      process.env.VITE_COMMIT_SHA || 
                      process.env.GITHUB_SHA ||
                      'unknown';

    const versionInfo = {
      service: 'quantum-leap-backend',
      commit: commitSha.substring(0, 7), // Show short hash
      commitFull: commitSha, // Full hash for debugging
      buildTime: process.env.BUILD_TIME || process.env.VITE_BUILD_TIME || new Date().toISOString(),
      imageDigest: process.env.IMAGE_DIGEST || 'unknown',
      depsLockHash: process.env.DEPS_LOCK_HASH || process.env.VITE_PACKAGE_LOCK_HASH || 'unknown',
      nodeVersion: process.version,
      environment: process.env.NODE_ENV || 'production',
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      timestamp: new Date().toISOString(),
      // Railway-specific metadata
      railway: {
        projectId: process.env.RAILWAY_PROJECT_ID || 'unknown',
        environmentId: process.env.RAILWAY_ENVIRONMENT_ID || 'unknown',
        serviceId: process.env.RAILWAY_SERVICE_ID || 'unknown',
        replicaId: process.env.RAILWAY_REPLICA_ID || 'unknown'
      }
    };

    res.json({
      success: true,
      data: versionInfo,
      message: 'Rock solid version info'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to get version info',
      message: error.message
    });
  }
});

module.exports = router;
