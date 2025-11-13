/**
 * Simple in-memory rate limiting for Next.js API routes
 * Tracks requests by IP address
 */

interface RateLimitStore {
  [key: string]: {
    count: number;
    resetTime: number;
  };
}

// In-memory store (clears on server restart)
// For production, consider using Redis or a persistent store
const rateLimitStore: RateLimitStore = {};

// Clean up old entries periodically (every 5 minutes)
if (typeof setInterval !== 'undefined') {
  setInterval(() => {
    const now = Date.now();
    Object.keys(rateLimitStore).forEach((key) => {
      if (rateLimitStore[key].resetTime < now) {
        delete rateLimitStore[key];
      }
    });
  }, 5 * 60 * 1000);
}

export interface RateLimitResult {
  success: boolean;
  limit: number;
  remaining: number;
  reset: number;
}

/**
 * Check rate limit for a given key (IP address)
 * @param key - Identifier for rate limiting (typically IP address)
 * @param limit - Maximum number of requests
 * @param windowMs - Time window in milliseconds
 * @returns Rate limit result
 */
export function checkRateLimit(
  key: string,
  limit: number,
  windowMs: number
): RateLimitResult {
  const now = Date.now();
  const entry = rateLimitStore[key];

  if (!entry || entry.resetTime < now) {
    // Create new entry or reset expired entry
    rateLimitStore[key] = {
      count: 1,
      resetTime: now + windowMs,
    };
    return {
      success: true,
      limit,
      remaining: limit - 1,
      reset: now + windowMs,
    };
  }

  if (entry.count >= limit) {
    // Rate limit exceeded
    return {
      success: false,
      limit,
      remaining: 0,
      reset: entry.resetTime,
    };
  }

  // Increment count
  entry.count += 1;
  return {
    success: true,
    limit,
    remaining: limit - entry.count,
    reset: entry.resetTime,
  };
}

/**
 * Get client IP address from Next.js request
 * @param req - Next.js API request
 * @returns IP address string
 */
export function getClientIP(req: { headers: { [key: string]: string | string[] | undefined }, socket?: { remoteAddress?: string } }): string {
  // Check X-Forwarded-For header (from proxy/load balancer)
  const forwardedFor = req.headers['x-forwarded-for'];
  if (forwardedFor) {
    const ips = Array.isArray(forwardedFor) ? forwardedFor[0] : forwardedFor;
    return ips.split(',')[0].trim();
  }

  // Check X-Real-IP header
  const realIP = req.headers['x-real-ip'];
  if (realIP) {
    return Array.isArray(realIP) ? realIP[0] : realIP;
  }

  // Fall back to socket remote address
  if (req.socket?.remoteAddress) {
    return req.socket.remoteAddress;
  }

  // Default fallback
  return 'unknown';
}

/**
 * Rate limit middleware for Next.js API routes
 * @param req - Next.js API request
 * @param limit - Maximum requests per window
 * @param windowMs - Time window in milliseconds
 * @returns Rate limit result or throws error if exceeded
 */
export function rateLimit(
  req: { headers: { [key: string]: string | string[] | undefined }, socket?: { remoteAddress?: string } },
  limit: number,
  windowMs: number
): RateLimitResult {
  const ip = getClientIP(req);
  const result = checkRateLimit(ip, limit, windowMs);

  if (!result.success) {
    const error: any = new Error('Rate limit exceeded');
    error.statusCode = 429;
    error.rateLimit = result;
    throw error;
  }

  return result;
}


