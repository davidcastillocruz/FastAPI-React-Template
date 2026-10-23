from slowapi import Limiter

from src.api.dependencies import get_client_ip
from src.core.settings import settings

# Rate limiter, its counters are stored in RATE_LIMIT_STORAGE_URI (Redis in Docker)
# If Redis is down it keeps working with counters in memory until Redis is back
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    in_memory_fallback_enabled=True,
    # The Redis calls block the event loop: a Redis that doesn't answer stops every request
    # for this long instead of redis-py's default 5 seconds (memory:// ignores these options)
    storage_options={"socket_timeout": 0.5, "socket_connect_timeout": 0.5},  # pyright: ignore[reportArgumentType]
)
