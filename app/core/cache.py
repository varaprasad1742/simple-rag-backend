from cachetools import (
    TTLCache
)

embedding_cache = TTLCache(
    maxsize=10000,
    ttl=86400
)

retrieval_cache = TTLCache(
    maxsize=5000,
    ttl=900
)

response_cache = TTLCache(
    maxsize=5000,
    ttl=300
)

user_cache_keys = {}