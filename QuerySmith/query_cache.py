import time
from typing import Any, Dict, Optional, Tuple, Callable
import functools

class QueryCache:
    def __init__(self, ttl: int = 60):
        self.cache: Dict[Tuple, Dict[str, Any]] = {}
        self.ttl = ttl

    def _make_key(self, query: str, params: Optional[Tuple] = None) -> Tuple:
        return (query, params)

    def get(self, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
        key = self._make_key(query, params)
        item = self.cache.get(key)
        if item and (time.time() - item['timestamp'] < self.ttl):
            return item['value']
        if key in self.cache:
            del self.cache[key]
        return None

    def set(self, query: str, params: Optional[Tuple], value: Any):
        key = self._make_key(query, params)
        self.cache[key] = {'value': value, 'timestamp': time.time()}

    def clear(self):
        self.cache.clear()

# Декоратор для кэширования SELECT-запросов
cache = QueryCache()
def cache_query(ttl: int = 60):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(self, query, *args, **kwargs):
            if not query.strip().lower().startswith('select'):
                return await func(self, query, *args, **kwargs)
            params = tuple(args) if args else None
            result = cache.get(query, params)
            if result is not None:
                return result
            result = await func(self, query, *args, **kwargs)
            cache.set(query, params, result)
            return result
        return wrapper
    return decorator 