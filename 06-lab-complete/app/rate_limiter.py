"""
Rate limiting (tiêu chí 7) - sliding window bằng Redis sorted set.
"""
import time
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r


def check_rate_limit(key: str) -> None:
    if r is None:
        return  # Redis không có, bỏ qua rate limit

    now = time.time()
    window_start = now - 60
    redis_key = f"rate:{key}"

    pipe = r.pipeline()
    pipe.zremrangebyscore(redis_key, "-inf", window_start)
    pipe.zcard(redis_key)
    pipe.zadd(redis_key, {str(now): now})
    pipe.expire(redis_key, 60)
    results = pipe.execute()

    count = results[1]
    if count >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )
