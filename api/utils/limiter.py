from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time


class RateLimiter(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter that actually works.
    Format: "requests/period" e.g., "200/minute", "10/second"
    """
    
    def __init__(self, app, limit: str = "200/minute"):
        super().__init__(app)
        self.limit, self.period = self._parse_limit(limit)
        self.requests: Dict[str, list] = defaultdict(list)
    
    def _parse_limit(self, limit_str: str) -> Tuple[int, int]:
        """Parse limit string like '200/minute' into (requests, seconds)"""
        parts = limit_str.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid limit format: {limit_str}")
        
        count = int(parts[0])
        period_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        period_name = parts[1].lower()
        if period_name not in period_map:
            raise ValueError(f"Invalid period: {period_name}")
        
        return count, period_map[period_name]
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _cleanup_old_requests(self, timestamps: list, current_time: float):
        """Remove timestamps older than the rate limit period"""
        cutoff = current_time - self.period
        return [ts for ts in timestamps if ts > cutoff]
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limit before processing request"""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        self.requests[client_ip] = self._cleanup_old_requests(
            self.requests[client_ip], 
            current_time
        )
        
        if len(self.requests[client_ip]) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "message": "Rate limit exceeded. Please try again later.",
                    "data": None
                }
            )
        
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        return response