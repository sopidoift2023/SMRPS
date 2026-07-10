# Rate Limiting Implementation Guide

## Overview

This document describes the enterprise-grade rate limiting system implemented in SMRPS to protect against abuse and improve scalability of expensive operations.

## Architecture

### Core Components

1. **`config/rate_limiter.py`** - Main rate limiting module
   - `RateLimiter` class: Core logic using Django's cache framework
   - Flexible decorators for protecting views
   - Automatic Redis support in production, in-memory fallback in dev

2. **Login Protection** - Custom rate-limited login view
   - File: `accounts/views.py`
   - Limits: 5 attempts per 15 minutes per IP
   - Prevents brute force attacks

3. **Heavy Endpoint Protection** - Portal view decorators
   - File: `portal/views.py`
   - Adaptive rate limiting based on user role
   - Different limits for different operations

## Rate Limit Policies

### Login Endpoint
- **Location**: `/login/`
- **Limit**: 5 attempts per 15 minutes per IP
- **Strategy**: IP-based (catches distributed attacks)
- **Response**: 429 Too Many Requests with Retry-After header

### Download Endpoints
- **Endpoints**:
  - `/download-class-cumulative-zip/<class_id>/`
  - `/download-cumulative-result/`
- **Base Limit**: 10 per hour
- **Admin Multiplier**: 2x (20 per hour)
- **Purpose**: Prevent resource exhaustion from large ZIP generation

### Heavy Computation Endpoints
- **Endpoints**:
  - `/teacher/<class_id>/results/` (teacher_generate_results)
  - `/teacher/<class_id>/final-results/` (form_teacher_generate_final_results)
- **Base Limit**: 5 per hour
- **Admin Multiplier**: 3x (15 per hour)
- **Purpose**: Protect database from expensive aggregation queries

### AI Generation Endpoint
- **Endpoint**: `/ai-assistant/generate/`
- **Base Limit**: 3 per hour
- **Admin Multiplier**: 5x (15 per hour)
- **Purpose**: Limit external API calls to DeepSeek

### Auto Comments Endpoint
- **Endpoint**: `/teacher/<class_id>/assessments/auto-comments/`
- **Base Limit**: 5 per hour
- **Admin Multiplier**: 2x (10 per hour)
- **Purpose**: Prevent spam of comment generation

## How It Works

### Identification

Rate limits are applied based on user identity:
- **Authenticated Users**: Identified by `user:{user_id}`
- **Anonymous Users**: Identified by `ip:{IP_ADDRESS}`

### Time Windows

- Uses fixed time windows (sliding window approach)
- Window size specified in seconds (e.g., 3600 = 1 hour)
- Each window is tracked independently in cache
- Current time automatically determines which window applies

### Cache Backend

- **Production (Redis)**: Automatically used if configured in Django cache
- **Development (SQLite)**: Falls back to Django's default cache
- **Configuration**: Edit `CACHES` in `config/settings.py` to use Redis

```python
# Production example (in settings.py)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## Usage Examples

### Basic Rate Limiting

```python
from config.rate_limiter import rate_limit

@rate_limit(max_requests=5, window_seconds=3600)
def expensive_operation(request):
    # Only 5 requests per hour per user/IP
    return JsonResponse({'status': 'ok'})
```

### Adaptive Rate Limiting (Role-Based)

```python
from config.rate_limiter import adaptive_rate_limit

@adaptive_rate_limit(
    base_max_requests=5,
    window_seconds=3600,
    premium_multiplier=3.0
)
def compute_results(request):
    # Regular users: 5/hour
    # Admins: 15/hour (5 * 3.0)
    return JsonResponse({'status': 'ok'})
```

### Custom Identifier Functions

```python
from config.rate_limiter import rate_limit

@rate_limit(
    identifier_func=lambda r: f"{r.user.id}:{r.POST.get('class_id')}",
    max_requests=3,
    window_seconds=300
)
def submit_grades(request):
    # Limit per user per class - 3 submissions per 5 minutes
    return JsonResponse({'status': 'ok'})
```

## Response Format

When rate limit is exceeded, clients receive:

```json
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1672531200
Retry-After: 300

{
  "error": "Rate limit exceeded. Please try again later.",
  "limit": 5,
  "remaining": 0,
  "reset_in": 300
}
```

### Response Headers

- `X-RateLimit-Limit`: Maximum requests allowed in current window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets
- `Retry-After`: Seconds to wait before retrying (for 429 responses)

## Testing

### Manual Testing

```python
# Test in Django shell
python manage.py shell

from django.test import Client
from django.contrib.auth.models import User
from accounts.models import User as CustomUser

client = Client()

# Test login rate limiting
for i in range(10):
    response = client.post('/login/', {
        'username': 'test',
        'password': 'wrong'
    })
    print(f"Attempt {i+1}: {response.status_code}")

# After 5 attempts: 429 Too Many Requests
```

### Automated Testing

```python
# In tests.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

class RateLimitingTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            role='TEACHER'
        )
    
    def test_login_rate_limiting(self):
        for i in range(5):
            response = self.client.post('/login/', {
                'username': 'testuser',
                'password': 'wrongpass'
            })
            self.assertIn(response.status_code, [200, 302])
        
        # 6th attempt should be rate limited
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 429)
        self.assertIn('error', response.json())
```

## Monitoring

### View Rate Limit Stats

```python
from config.rate_limiter import _rate_limiter

# Check current usage
allowed, info = _rate_limiter.is_allowed(
    identifier='user:123',
    max_requests=10,
    window_seconds=3600
)

print(f"Allowed: {allowed}")
print(f"Current Count: {info['current_count']}")
print(f"Remaining: {info['remaining']}")
print(f"Reset In: {info['reset_in']} seconds")
```

### Logging

Add logging to track rate limit violations:

```python
# In settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'rate_limit.log',
        },
    },
    'loggers': {
        'rate_limiter': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
```

## Configuration

### Adding New Rate-Limited Endpoints

1. Import decorators
```python
from config.rate_limiter import rate_limit, adaptive_rate_limit
```

2. Apply decorator with appropriate limits
```python
@login_required
@adaptive_rate_limit(base_max_requests=10, window_seconds=3600)
def my_expensive_endpoint(request):
    # Implementation
    pass
```

3. Choose limits based on:
   - **Operation Cost**: Heavier operations = lower limits
   - **Business Logic**: How often should legitimate users perform this?
   - **Security**: Is this vulnerable to abuse?

### Adjusting Rate Limits

All rate limit configuration is in decorator parameters:

```python
# Increase limit for heavy computation (might be expensive)
@adaptive_rate_limit(base_max_requests=3, window_seconds=3600)

# Tighten for security-sensitive operation
@rate_limit(max_requests=3, window_seconds=900)  # 3 per 15 min

# Relax for common operations
@rate_limit(max_requests=100, window_seconds=3600)  # 100 per hour
```

## Performance Impact

### Cache Overhead

- **Per Request**: ~1-2ms for cache lookup
- **Memory Usage**: ~100 bytes per tracked identifier
- **CPU**: Minimal - simple counter increment

### Scaling Considerations

**Development (SQLite Cache)**
- Works for ~100 concurrent users
- ~1000 tracked identifiers

**Production (Redis)**
- Scales to millions of concurrent users
- Distributed rate limiting across multiple servers
- Recommended for production deployments

## Troubleshooting

### Rate Limit Not Working

1. Check that decorators are applied in correct order (after `@login_required`)
2. Verify cache backend is configured properly
3. Check Redis connection (if using Redis)
4. View logs for errors

### Users Complaining About Limits

1. Check limit values - may be too aggressive
2. Review `reset_in` value in response - users understand they must wait
3. Consider role-based multipliers for power users
4. Adjust `premium_multiplier` if needed

### Cache Not Clearing

1. Clear cache manually:
```python
from django.core.cache import cache
cache.clear()
```

2. Check cache expiration settings
3. Ensure `window_seconds` is set correctly

## Future Enhancements

1. **Rate Limit Metrics Dashboard** - Monitor usage patterns
2. **Dynamic Rate Limiting** - Adjust based on server load
3. **Whitelist/Blacklist** - Bypass limits for specific IPs/users
4. **Rate Limit Tiers** - Different limits for different subscription levels
5. **Webhook Notifications** - Alert admins of unusual patterns
6. **Geographic Rate Limiting** - Different limits by region

## Security Considerations

⚠️ **Important**: Rate limiting alone is NOT sufficient security. Also implement:

- Strong authentication (already in place)
- CSRF protection (already in place)
- Input validation (implement per endpoint)
- Logging and monitoring
- Regular security audits

## References

- Django Cache Framework: https://docs.djangoproject.com/en/6.0/topics/cache/
- HTTP 429 Status: https://httpwg.org/specs/rfc6585.html#status.429
- Rate Limiting Best Practices: https://cloud.google.com/architecture/rate-limiting-strategies-techniques
