const express = require('express');
const router = express.Router();

// Version endpoint for rock solid audit enforcement
router.get('/version', (req, res) => {
  try {
    const versionInfo = {
      service: 'quantum-leap-backend',
      commit: process.env.COMMIT_SHA || process.env.VITE_COMMIT_SHA || 'unknown',
      buildTime: process.env.BUILD_TIME || process.env.VITE_BUILD_TIME || 'unknown',
      imageDigest: process.env.IMAGE_DIGEST || 'unknown',
      depsLockHash: process.env.DEPS_LOCK_HASH || process.env.VITE_PACKAGE_LOCK_HASH || 'unknown',
      nodeVersion: process.version,
      environment: process.env.NODE_ENV || 'production',
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      timestamp: new Date().toISOString()
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
