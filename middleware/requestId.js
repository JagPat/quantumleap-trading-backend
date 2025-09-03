const { v4: uuidv4 } = require('uuid');

// Request ID middleware
const requestId = (req, res, next) => {
  req.id = req.get('X-Request-ID') || uuidv4();
  res.set('X-Request-ID', req.id);
  next();
};

module.exports = { requestId };