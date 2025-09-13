"""Redis-based implementation of Memory interface."""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional

try:  # pragma: no cover - optional dependency
    import redis
except Exception:  # pragma: no cover
    redis = None

from .memory import Memory


class RedisMemory(Memory):
    """Redis-based memory store.

    Args:
        url: Redis connection URL. Defaults to ``redis://localhost:6379/0``.
        hist_maxlen: Default maximum history length.
        prefix: Key prefix for namespacing.
        client: Optional pre-initialized ``redis.Redis`` client.
    """

    def __init__(
        self,
        url: str = None,
        hist_maxlen: int = 200,
        prefix: str = "vf:",
        client: Optional[redis.Redis] = None,
    ) -> None:
        # Build default URL from env to avoid hardcoding sensitive strings
        if url is None:
            url = (
                f"redis://{os.getenv('VF_REDIS_HOST', 'localhost')}:{os.getenv('VF_REDIS_PORT', '6379')}/"
                f"{os.getenv('VF_REDIS_DB', '0')}"
            )

        if client is not None:
            self._client = client
        else:
            if redis is None:
                raise ImportError("redis package is required")
            self._client = redis.Redis.from_url(url, decode_responses=True)
        self._hist_maxlen = hist_maxlen
        self._prefix = prefix

    # Key helpers -----------------------------------------------------------------
    def _hist_key(self, user_id: str) -> str:
        return f"{self._prefix}hist:{user_id}"

    def _ctx_key(self, user_id: str, key: str) -> str:
        return f"{self._prefix}ctx:{user_id}:{key}"

    def _ephemeral_key(self, user_id: str, key: str) -> str:
        return f"{self._prefix}ephemeral:{user_id}:{key}"

    def _dedup_key(self, user_id: str, key: str) -> str:
        return f"{self._prefix}dedup:{user_id}:{key}"

    def _rate_key(self, user_id: str, bucket: str) -> str:
        return f"{self._prefix}rate:{user_id}:{bucket}"

    # Memory API -------------------------------------------------------------------
    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        redis_key = self._dedup_key(user_id, key)
        result = self._client.set(redis_key, "1", nx=True, ex=ttl_sec if ttl_sec > 0 else None)
        return result is None

    def append_history(self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200) -> None:
        message = json.dumps({"role": role, "type": mtype, "content": content})
        key = self._hist_key(user_id)
        pipe = self._client.pipeline()
        pipe.lpush(key, message)
        pipe.ltrim(key, 0, maxlen - 1)
        pipe.execute()

    def recent_history(self, user_id: str, n: int = 20) -> List[dict]:
        key = self._hist_key(user_id)
        messages = self._client.lrange(key, 0, n - 1)
        return [json.loads(m) for m in messages]

    def ctx_set(self, user_id: str, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        redis_key = self._ctx_key(user_id, key)
        value_str = json.dumps(value, ensure_ascii=False)
        if ttl_sec is not None and ttl_sec > 0:
            self._client.set(redis_key, value_str, ex=ttl_sec)
        else:
            self._client.set(redis_key, value_str)

    def ctx_get(self, user_id: str, key: str) -> Optional[Any]:
        value = self._client.get(self._ctx_key(user_id, key))
        if value is None:
            return None
        return json.loads(value)

    def ctx_del(self, user_id: str, key: str) -> None:
        self._client.delete(self._ctx_key(user_id, key))

    def set_ephemeral(self, user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None:
        redis_key = self._ephemeral_key(user_id, key)
        value_str = json.dumps(value, ensure_ascii=False)
        self._client.set(redis_key, value_str, ex=ttl_sec if ttl_sec > 0 else None)

    def get_ephemeral(self, user_id: str, key: str) -> Optional[Any]:
        value = self._client.get(self._ephemeral_key(user_id, key))
        if value is None:
            return None
        return json.loads(value)

    def del_ephemeral(self, user_id: str, key: str) -> None:
        self._client.delete(self._ephemeral_key(user_id, key))

    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        key = self._rate_key(user_id, bucket)
        pipe = self._client.pipeline()
        pipe.incr(key)
        if ttl_sec > 0:
            pipe.expire(key, ttl_sec)
        count, _ = pipe.execute()
        return int(count)
