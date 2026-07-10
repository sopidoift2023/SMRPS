from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from config.rate_limiter import rate_limit


@method_decorator(
    rate_limit(
        identifier_func=lambda r: f"login_attempt:{r.META.get('REMOTE_ADDR', 'unknown')}",
        max_requests=5,
        window_seconds=900,  # 15 minutes
        error_message="Too many login attempts. Please try again in 15 minutes."
    ),
    name='post'
)
class RateLimitedLoginView(LoginView):
    """
    Custom LoginView with aggressive rate limiting to prevent brute force attacks.
    - Max 5 login attempts per 15 minutes per IP address
    - Uses IP-based identification to catch distributed attacks
    """
    template_name = 'portal/login.html'
