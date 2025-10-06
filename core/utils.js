/**
 * Core utility functions
 */

/**
 * Check if a string is a valid UUID
 * @param {string} val - String to check
 * @returns {boolean} - True if valid UUID
 */
function isUUID(val) {
  if (typeof val !== 'string') return false;
  return /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(val);
}

module.exports = { 
  isUUID
};
