"""
Kết nối Redis dùng chung cho rate limiter và cost guard.
App vẫn khởi động được khi Redis chưa sẵn sàng.
"""
import redis as _redis
from app.config import settings

try:
    r = _redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
except Exception:
    r = None


def redis_healthy() -> bool:
    try:
        if r is None:
            return False
        r.ping()
        return True
    except Exception:
        return False
