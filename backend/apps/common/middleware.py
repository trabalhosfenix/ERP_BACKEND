from django.conf import settings
from django.http import JsonResponse

from apps.common.redis import get_redis


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            ip = request.META.get("REMOTE_ADDR", "unknown")
            key = f"rate_limit:{ip}"
            try:
                client = get_redis()
                count = client.incr(key)
                if count == 1:
                    client.expire(key, 60)
                if count > settings.RATE_LIMIT_PER_MINUTE:
                    return JsonResponse({"detail": "rate limit exceeded"}, status=429)
            except Exception:
                pass
        return self.get_response(request)
