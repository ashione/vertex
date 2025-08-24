"""Hybrid memory store combining Redis for caching and RDS for persistence."""

from __future__ import annotations

from typing import Any, Optional

from .memory import Memory
from .redis_store import RedisMemory
from .rds_store import RDSMemory


class HybridMemory(Memory):
    """Memory implementation using Redis as cache and RDS as persistent storage."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        db_url: str = "sqlite:///:memory:",
        hist_maxlen: int = 200,
        prefix: str = "vf:",
        redis_client=None,
    ) -> None:
        self._redis = RedisMemory(
            url=redis_url, hist_maxlen=hist_maxlen, prefix=prefix, client=redis_client
        )
        self._rds = RDSMemory(db_url=db_url, hist_maxlen=hist_maxlen)
        self._hist_maxlen = hist_maxlen

    # Deduplication -----------------------------------------------------------------
    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        result = self._rds.seen(user_id, key, ttl_sec)
        self._redis.seen(user_id, key, ttl_sec)
        return result

    # History ----------------------------------------------------------------------
    def append_history(
        self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200
    ) -> None:
        self._rds.append_history(user_id, role, mtype, content, maxlen)
        self._redis.append_history(user_id, role, mtype, content, maxlen)

    def recent_history(self, user_id: str, n: int = 20) -> list[dict]:
        history = self._redis.recent_history(user_id, n)
        if history:
            return history
        history = self._rds.recent_history(user_id, n)
        for msg in reversed(history):
            self._redis.append_history(
                user_id, msg["role"], msg["type"], msg["content"], self._hist_maxlen
            )
        return history

    # Context ----------------------------------------------------------------------
    def ctx_set(
        self, user_id: str, key: str, value: Any, ttl_sec: Optional[int] = None
    ) -> None:
        self._rds.ctx_set(user_id, key, value, ttl_sec)
        self._redis.ctx_set(user_id, key, value, ttl_sec)

    def ctx_get(self, user_id: str, key: str) -> Optional[Any]:
        value = self._redis.ctx_get(user_id, key)
        if value is not None:
            return value
        value = self._rds.ctx_get(user_id, key)
        if value is not None:
            self._redis.ctx_set(user_id, key, value)
        return value

    def ctx_del(self, user_id: str, key: str) -> None:
        self._rds.ctx_del(user_id, key)
        self._redis.ctx_del(user_id, key)

    # Ephemeral --------------------------------------------------------------------
    def set_ephemeral(
        self, user_id: str, key: str, value: Any, ttl_sec: int = 1800
    ) -> None:
        self._rds.set_ephemeral(user_id, key, value, ttl_sec)
        self._redis.set_ephemeral(user_id, key, value, ttl_sec)

    def get_ephemeral(self, user_id: str, key: str) -> Optional[Any]:
        value = self._redis.get_ephemeral(user_id, key)
        if value is not None:
            return value
        return self._rds.get_ephemeral(user_id, key)

    def del_ephemeral(self, user_id: str, key: str) -> None:
        self._rds.del_ephemeral(user_id, key)
        self._redis.del_ephemeral(user_id, key)

    # Rate limiting ----------------------------------------------------------------
    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        count = self._rds.incr_rate(user_id, bucket, ttl_sec)
        redis_key = self._redis._rate_key(user_id, bucket)
        self._redis._client.set(redis_key, str(count))
        if ttl_sec > 0:
            self._redis._client.expire(redis_key, ttl_sec)
        return count
