from django_ratelimit.exceptions import Ratelimited
from django.shortcuts import render

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            return render(request, 'conta/rate_limit.html', status=429)
        return None
