import hashlib

from app.core.cache import (
    embedding_cache,
    retrieval_cache,
    response_cache
)
from app.observability.collector import (
    add_step
)
import json 
user_cache_keys = {}
class CacheService:
    @staticmethod
    def build_key(
        *parts
    ):

        text = "|".join(
            str(x)
            for x in parts
        )

        return hashlib.sha256(
            text.encode()
        ).hexdigest()
    
    @staticmethod
    def register_user_key(
        user_id,
        cache_type,
        key
    ):

        if user_id not in user_cache_keys:

            user_cache_keys[user_id] = {
                "retrieval": set(),
                "response": set()
            }

        user_cache_keys[user_id][cache_type].add(key)


    @staticmethod
    def get_embedding(
        query: str
    ):

        key = (
            CacheService
            .build_key(query)
        )

        return (
            embedding_cache
            .get(key)
        )
    
    @staticmethod
    def set_embedding(
        query,
        embedding
    ):

        key = (
            CacheService
            .build_key(query)
        )

        embedding_cache[
            key
        ] = embedding

    @staticmethod
    def get_retrieval(
        user_id,
        query
    ):

        key = (
            CacheService
            .build_key(
                user_id,
                query
            )
        )

        return retrieval_cache.get(
            key
        )
    @staticmethod
    def set_retrieval(
        user_id,
        query,
        results
    ):

        key = (
            CacheService
            .build_key(
                user_id,
                query
            )
        )

        retrieval_cache[
            key
        ] = results
        CacheService.register_user_key(
        user_id,
        "retrieval",
        key
    )


    @staticmethod
    def get_response(
        user_id,
        query
    ):

        key = (
            CacheService
            .build_key(
                user_id,
                query
            )
        )

        return json.loads(response_cache.get(
            key
        ))
    
    @staticmethod
    def set_response(
        user_id,
        query,
        answer, citations
    ):

        key = (
            CacheService
            .build_key(
                user_id,
                query
            )
        )

        response_cache[
            key
        ] = json.dumps([answer,citations])
        CacheService.register_user_key(
            user_id,
            "response",
            key
        )   

    @staticmethod
    def invalidate_user(
        user_id
    ):

        data = user_cache_keys.get(
            user_id
        )

        if not data:
            return
        for key in data["retrieval"]:
            retrieval_cache.pop(
                key,
                None
            )
        for key in data["response"]:
            response_cache.pop(
                key,
                None
            )


    @staticmethod
    def trace_cache(
        cache_name,
        hit
    ):

        add_step(
            {
                "name":
                cache_name,

                "duration":
                0,

                "status":
                "success",

                "trace_metadata":
                {
                    "cache_hit":
                    hit
                }
            }
        )