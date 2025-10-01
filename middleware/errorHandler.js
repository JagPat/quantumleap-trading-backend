// Error handling middleware
const errorHandler = (err, req, res, next) => {
  const logger = req.app?.get('logger') || console;
  logger.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
};

module.exports = { errorHandler };