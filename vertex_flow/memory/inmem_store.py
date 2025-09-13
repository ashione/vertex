"""In-memory implementation of Memory interface."""

import json
import threading
import time
from collections import defaultdict, deque
from typing import Any, List, Optional

from .memory import Memory


class InnerMemory(Memory):
    """In-memory implementation of Memory interface.

    Features:
    - Thread-safe operations with RLock
    - TTL support with lazy cleanup
    - Background thread for periodic cleanup
    - JSON serialization for all stored values
    """

    def __init__(self, hist_maxlen: int = 200, cleanup_interval_sec: int = 300):
        """Initialize InnerMemory.

        Args:
            hist_maxlen: Default maximum history length
            cleanup_interval_sec: Interval for background cleanup in seconds
        """
        self._hist_maxlen = hist_maxlen
        self._cleanup_interval = cleanup_interval_sec

        # Thread safety
        self._lock = threading.RLock()

        # Storage structures
        # 历史记录不使用固定 maxlen 的 deque，避免实例级别强裁剪影响按调用传入的 maxlen 行为
        self._histories: dict[str, deque] = defaultdict(lambda: deque())
        self._ctx: dict[str, dict[str, dict]] = defaultdict(dict)
        self._ephemeral: dict[str, dict[str, dict]] = defaultdict(dict)
        self._dedup: dict[str, dict[str, dict]] = defaultdict(dict)
        self._rate: dict[str, dict[str, dict]] = defaultdict(dict)

        # Start background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _serialize_value(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, ensure_ascii=False)

    def _deserialize_value(self, value_str: str) -> Any:
        """Deserialize JSON string to value."""
        return json.loads(value_str)

    def _is_expired(self, item: dict) -> bool:
        """Check if an item is expired."""
        expires_at = item.get("expires_at")
        if expires_at is None:
            return False
        return time.time() > expires_at

    # Deduplication -----------------------------------------------------------------
    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        with self._lock:
            dedup = self._dedup[user_id]
            item = dedup.get(key)
            if item and not self._is_expired(item):
                return True
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            dedup[key] = {"expires_at": expires_at}
            return False

    # History ----------------------------------------------------------------------
    def append_history(self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200) -> None:
        with self._lock:
            hist = self._histories[user_id]
            hist.appendleft({"role": role, "type": mtype, "content": content})
            # 仅在此按调用传入的 maxlen 进行裁剪，避免实例初始化时就限制为固定长度
            while len(hist) > maxlen:
                hist.pop()

    def recent_history(self, user_id: str, n: int = 20) -> List[dict]:
        with self._lock:
            hist = self._histories[user_id]
            return list(list(hist)[:n])

    # Context ----------------------------------------------------------------------
    def ctx_set(self, user_id: str, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        with self._lock:
            store = self._ctx[user_id]
            expires_at = time.time() + ttl_sec if ttl_sec is not None and ttl_sec > 0 else None
            store[key] = {"value": self._serialize_value(value), "expires_at": expires_at}

    def ctx_get(self, user_id: str, key: str) -> Optional[Any]:
        with self._lock:
            store = self._ctx[user_id]
            item = store.get(key)
            if not item or self._is_expired(item):
                if key in store:
                    del store[key]
                return None
            return self._deserialize_value(item["value"])

    def ctx_del(self, user_id: str, key: str) -> None:
        with self._lock:
            store = self._ctx[user_id]
            if key in store:
                del store[key]

    # Ephemeral --------------------------------------------------------------------
    def set_ephemeral(self, user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None:
        with self._lock:
            store = self._ephemeral[user_id]
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            store[key] = {"value": self._serialize_value(value), "expires_at": expires_at}

    def get_ephemeral(self, user_id: str, key: str) -> Optional[Any]:
        with self._lock:
            store = self._ephemeral[user_id]
            item = store.get(key)
            if not item or self._is_expired(item):
                if key in store:
                    del store[key]
                return None
            return self._deserialize_value(item["value"])

    def del_ephemeral(self, user_id: str, key: str) -> None:
        with self._lock:
            store = self._ephemeral[user_id]
            if key in store:
                del store[key]

    # Rate limiting ----------------------------------------------------------------
    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        with self._lock:
            store = self._rate[user_id]
            item = store.get(bucket)
            now = time.time()
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            if item and not self._is_expired(item):
                item["value"] += 1
                if ttl_sec > 0:
                    item["expires_at"] = now + ttl_sec
                return item["value"]
            store[bucket] = {"value": 1, "expires_at": expires_at}
            return 1

    # Cleanup ----------------------------------------------------------------------
    def _cleanup_loop(self) -> None:
        while True:
            time.sleep(self._cleanup_interval)
            self._cleanup()

    def _cleanup(self) -> None:
        with self._lock:
            now = time.time()
            # Clean ctx
            for user_id, store in list(self._ctx.items()):
                for key, item in list(store.items()):
                    if item.get("expires_at") is not None and now > item.get("expires_at"):
                        del store[key]
            # Clean ephemeral
            for user_id, store in list(self._ephemeral.items()):
                for key, item in list(store.items()):
                    if item.get("expires_at") is not None and now > item.get("expires_at"):
                        del store[key]
            # Clean dedup
            for user_id, store in list(self._dedup.items()):
                for key, item in list(store.items()):
                    if item.get("expires_at") is not None and now > item.get("expires_at"):
                        del store[key]
            # Clean rate
            for user_id, store in list(self._rate.items()):
                for bucket, item in list(store.items()):
                    if item.get("expires_at") is not None and now > item.get("expires_at"):
                        del store[bucket]
