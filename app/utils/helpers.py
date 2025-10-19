from typing import Optional, Any, Dict, Callable
from functools import wraps
import time
import sys
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

#----------------------------------
# Cache
#----------------------------------
class CacheManager:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
            
        cache_data = self.cache[key]
        if time.time() > cache_data['expires_at']:
            del self.cache[key]
            return None
            
        return cache_data['value']
    
    def clear(self) -> None:
        self.cache.clear()

cache_manager = CacheManager()
def cache(ttl: int = 300):
    """
    Decorator for caching FastAPI endpoint responses.
    
    Args:
        ttl (int): Time to live in seconds. Defaults to 300 seconds (5 minutes).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_response = cache_manager.get(cache_key)
            if cached_response is not None:
                print("found in cache, size: ",sys.getsizeof(cached_response))                
                return cached_response
            
            print("NOT found in cache")
            # If not in cache, execute the function
            response = await func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, response, ttl)
            
            return response
        return wrapper
    return decorator

#----------------------------------
# Redirect aquilon to www.aquilon.fi
#----------------------------------
WWW_DOMAIN = "www.aquilon.fi"
class WWWRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect non-WWW traffic to the WWW domain.
    This ensures that all requests go through the preferred www.aquilon.fi domain.
    """
    async def dispatch(self, request: Request, call_next):
        # Get the host from the request headers
        host = request.url.hostname

        # Check if the host is not the desired WWW_DOMAIN
        # Also ensure it's not already localhost or a test environment
        if host and host != WWW_DOMAIN and not host.startswith("localhost") and not host.startswith("127.0.0.1"):
            # Construct the new URL with the WWW_DOMAIN, preserving path and query parameters
            # Example: https://aquilon.fi/some/path?param=value -> https://www.aquilon.fi/some/path?param=value
            redirect_url = request.url.replace(netloc=WWW_DOMAIN)._url

            # Return a 301 Permanent Redirect response
            print(f"Redirecting from {request.url} to {redirect_url}") # For debugging
            return RedirectResponse(url=redirect_url, status_code=301)

        # If the host is already the WWW_DOMAIN or a local development host, proceed with the request
        response = await call_next(request)
        return response