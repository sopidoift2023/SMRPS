"""
Rate limiting utilities for SMRPS.

Implements Redis-backed rate limiting with fallback to in-memory cache
for development environments. Provides flexible, reusable decorators and
utilities for protecting expensive operations.
"""

import time
import hashlib
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
from typing import Tuple, Optional


class RateLimiter:
    """
    Rate limiter implementation using Django's cache framework.
    Automatically uses Redis in production, in-memory in development.
    """
    
    def __init__(self, cache_backend='default'):
        self.cache = cache if cache_backend == 'default' else cache
        
    def _get_key(self, identifier: str, window: str) -> str:
        """Generate a cache key for the rate limit window."""
        return f"ratelimit:{identifier}:{window}"
    
    def _get_current_window(self, window_seconds: int) -> int:
        """Get the current time window."""
        return int(time.time() // window_seconds)
    
    def is_allowed(
        self, 
        identifier: str, 
        max_requests: int, 
        window_seconds: int = 3600
    ) -> Tuple[bool, dict]:
        """
        Check if a request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier (user ID, IP, user:action)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds (default: 1 hour)
            
        Returns:
            Tuple of (is_allowed: bool, info: dict with usage stats)
        """
        current_window = self._get_current_window(window_seconds)
        cache_key = self._get_key(identifier, str(current_window))
        
        current_count = cache.get(cache_key, 0)
        remaining = max(0, max_requests - current_count)
        
        info = {
            'limit': max_requests,
            'remaining': remaining,
            'reset_in': window_seconds - (int(time.time()) % window_seconds),
            'current_count': current_count
        }
        
        if current_count < max_requests:
            cache.set(cache_key, current_count + 1, window_seconds)
            info['allowed'] = True
            return True, info
        
        info['allowed'] = False
        return False, info
    
    def reset(self, identifier: str, window_seconds: int = 3600):
        """Reset rate limit for an identifier."""
        current_window = self._get_current_window(window_seconds)
        cache_key = self._get_key(identifier, str(current_window))
        cache.delete(cache_key)


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(
    identifier_func=None,
    max_requests: int = 10,
    window_seconds: int = 3600,
    error_message: str = "Rate limit exceeded"
):
    """
    Decorator for rate-limiting view functions.
    
    Args:
        identifier_func: Callable(request) -> str. Defaults to user ID or IP.
        max_requests: Max requests per window
        window_seconds: Time window in seconds
        error_message: Custom error message
        
    Usage:
        @rate_limit(max_requests=5, window_seconds=3600)
        def my_view(request):
            ...
            
        @rate_limit(
            identifier_func=lambda r: f"{r.user.id}:{r.POST.get('action')}",
            max_requests=3,
            window_seconds=60
        )
        def sensitive_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get identifier
            if identifier_func:
                identifier = identifier_func(request)
            elif request.user.is_authenticated:
                identifier = f"user:{request.user.id}"
            else:
                identifier = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"
            
            # Check rate limit
            allowed, info = _rate_limiter.is_allowed(
                identifier,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            
            if not allowed:
                response = JsonResponse(
                    {
                        'error': error_message,
                        'limit': info['limit'],
                        'remaining': info['remaining'],
                        'reset_in': info['reset_in']
                    },
                    status=429
                )
                response['Retry-After'] = str(info['reset_in'])
                return response
            
            # Add rate limit info to response headers
            response = view_func(request, *args, **kwargs)
            if hasattr(response, '__setitem__'):  # Only if response supports item assignment
                response['X-RateLimit-Limit'] = str(info['limit'])
                response['X-RateLimit-Remaining'] = str(info['remaining'])
                response['X-RateLimit-Reset'] = str(int(time.time()) + info['reset_in'])
            
            return response
        
        return wrapper
    return decorator


def rate_limit_by_ip(max_requests: int = 20, window_seconds: int = 3600):
    """Rate limit by IP address."""
    return rate_limit(
        identifier_func=lambda r: f"ip:{r.META.get('REMOTE_ADDR', 'unknown')}",
        max_requests=max_requests,
        window_seconds=window_seconds
    )


def rate_limit_by_user(max_requests: int = 10, window_seconds: int = 3600):
    """Rate limit by authenticated user ID."""
    return rate_limit(
        identifier_func=lambda r: f"user:{r.user.id}" if r.user.is_authenticated else f"ip:{r.META.get('REMOTE_ADDR')}",
        max_requests=max_requests,
        window_seconds=window_seconds
    )


def adaptive_rate_limit(
    base_max_requests: int = 10,
    window_seconds: int = 3600,
    premium_multiplier: float = 2.0
):
    """
    Adaptive rate limiting based on user role/status.
    
    Args:
        base_max_requests: Base limit for regular users
        window_seconds: Time window
        premium_multiplier: Multiplier for premium users (teachers, admins)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Determine user tier
            is_admin = request.user.is_authenticated and hasattr(request.user, 'role') and (
                request.user.role in ('SCHOOL_ADMIN', 'SUPER_ADMIN')
            )
            
            limit = int(base_max_requests * premium_multiplier) if is_admin else base_max_requests
            
            identifier = f"user:{request.user.id}" if request.user.is_authenticated else f"ip:{request.META.get('REMOTE_ADDR')}"
            
            allowed, info = _rate_limiter.is_allowed(
                identifier,
                max_requests=limit,
                window_seconds=window_seconds
            )
            
            if not allowed:
                response = JsonResponse(
                    {
                        'error': 'Rate limit exceeded. Please try again later.',
                        'limit': info['limit'],
                        'remaining': info['remaining'],
                        'reset_in': info['reset_in']
                    },
                    status=429
                )
                response['Retry-After'] = str(info['reset_in'])
                return response
            
            response = view_func(request, *args, **kwargs)
            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = str(info['limit'])
                response['X-RateLimit-Remaining'] = str(info['remaining'])
                response['X-RateLimit-Reset'] = str(int(time.time()) + info['reset_in'])
            
            return response
        
        return wrapper
    return decorator
