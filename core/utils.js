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

/**
 * Normalize user identifier (legacy function for backward compatibility)
 * @param {string} incoming - Input identifier
 * @returns {string|null} - Normalized identifier or null
 */
function normalizeUserIdentifier(incoming) {
  if (!incoming) {
    return null;
  }

  // If it's already a UUID, return as-is
  if (isUUID(incoming)) {
    return incoming;
  }

  // For non-UUID strings, we'll let the resolver handle them
  // This maintains backward compatibility while allowing the new resolver to work
  return incoming;
}

module.exports = { 
  isUUID, 
  normalizeUserIdentifier 
};
