"""
Rate Limiting Middleware for TransformDash
Prevents brute-force attacks and DoS by limiting request rates per IP address
"""
import os
import time
import threading
from collections import defaultdict
from typing import Dict, Tuple, Set
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# Trusted proxy IPs - only accept X-Forwarded-For from these sources
# Configure via TRUSTED_PROXIES env var (comma-separated IPs)
# Examples: 127.0.0.1, internal load balancer IPs, Cloudflare IPs
TRUSTED_PROXIES: Set[str] = set(
    filter(None, os.getenv('TRUSTED_PROXIES', '127.0.0.1,::1').split(','))
)


class RateLimiter:
    """
    Thread-safe in-memory rate limiter using sliding window algorithm.

    WARNING: Not suitable for distributed deployments. Request counts
    are stored in-process and not shared across multiple instances.

    For distributed systems, use a Redis-backed rate limiter.
    """

    def __init__(self):
        # Store: {ip_address: {endpoint: (request_count, window_start_time)}}
        self.requests: Dict[str, Dict[str, Tuple[int, float]]] = defaultdict(lambda: defaultdict(lambda: (0, time.time())))
        self.cleanup_interval = 3600  # Clean up old entries every hour
        self.last_cleanup = time.time()
        # Thread lock for thread-safe access
        self._lock = threading.Lock()

    def is_rate_limited(self, client_ip: str, endpoint: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if a request should be rate limited (thread-safe)

        Args:
            client_ip: Client IP address
            endpoint: API endpoint path
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()

        with self._lock:
            # Periodic cleanup
            if current_time - self.last_cleanup > self.cleanup_interval:
                self._cleanup_old_entries(current_time)

            # Get current request count and window start time
            count, window_start = self.requests[client_ip][endpoint]

            # Reset window if expired
            if current_time - window_start > window_seconds:
                self.requests[client_ip][endpoint] = (1, current_time)
                return False

            # Check if limit exceeded
            if count >= max_requests:
                logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}: {count} requests in {current_time - window_start:.2f}s")
                return True

            # Increment counter
            self.requests[client_ip][endpoint] = (count + 1, window_start)
            return False

    def _cleanup_old_entries(self, current_time: float):
        """Remove entries older than 1 hour to prevent memory leak"""
        ips_to_remove = []

        for ip, endpoints in self.requests.items():
            endpoints_to_remove = []
            for endpoint, (count, window_start) in endpoints.items():
                if current_time - window_start > 3600:  # 1 hour
                    endpoints_to_remove.append(endpoint)

            for endpoint in endpoints_to_remove:
                del endpoints[endpoint]

            if not endpoints:
                ips_to_remove.append(ip)

        for ip in ips_to_remove:
            del self.requests[ip]

        self.last_cleanup = current_time
        logger.info(f"Rate limiter cleanup: removed {len(ips_to_remove)} IPs")


# Global rate limiter instance
rate_limiter = RateLimiter()


# Rate limit configurations for different endpoints
RATE_LIMITS = {
    "/api/auth/login": (5, 300),      # 5 requests per 5 minutes (brute-force protection)
    "/api/auth/logout": (10, 60),     # 10 requests per minute
    "/api/auth/me": (120, 60),        # 120 requests per minute (increased for SPA polling)
    "/api/query": (20, 60),           # 20 queries per minute
    "/api/query/execute": (20, 60),   # 20 queries per minute
    "/api/dashboard/*/export": (10, 60),  # 10 exports per minute
    "/api/charts/*/export": (10, 60),     # 10 exports per minute
}


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request securely.

    Only trusts X-Forwarded-For header when the direct connection
    comes from a known/trusted proxy to prevent IP spoofing.
    """
    direct_ip = request.client.host if request.client else "unknown"

    # Only trust X-Forwarded-For if request comes from a trusted proxy
    if direct_ip in TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
            # Take the first one (original client)
            return forwarded.split(",")[0].strip()

    # Use direct connection IP (don't trust X-Forwarded-For from untrusted sources)
    return direct_ip


def check_rate_limit(request: Request, max_requests: int = 10, window_seconds: int = 60):
    """
    Dependency function to check rate limits

    Usage:
        @app.post("/api/endpoint", dependencies=[Depends(lambda r: check_rate_limit(r, 5, 300))])

    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    client_ip = get_client_ip(request)
    endpoint = request.url.path

    if rate_limiter.is_rate_limited(client_ip, endpoint, max_requests, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
            headers={"Retry-After": str(window_seconds)}
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically apply rate limits to configured endpoints
    """

    async def dispatch(self, request: Request, call_next):
        client_ip = get_client_ip(request)
        path = request.url.path

        # Check if this endpoint has rate limiting configured
        for endpoint_pattern, (max_req, window) in RATE_LIMITS.items():
            if self._matches_pattern(path, endpoint_pattern):
                if rate_limiter.is_rate_limited(client_ip, path, max_req, window):
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": f"Rate limit exceeded. Maximum {max_req} requests per {window} seconds."},
                        headers={"Retry-After": str(window)}
                    )

        response = await call_next(request)
        return response

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern (supports * wildcard)"""
        if "*" not in pattern:
            return path == pattern

        # Simple wildcard matching
        pattern_parts = pattern.split("*")
        if len(pattern_parts) == 2:
            return path.startswith(pattern_parts[0]) and path.endswith(pattern_parts[1])

        return False
