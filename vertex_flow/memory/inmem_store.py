"""In-memory implementation of Memory interface."""

import json
import threading
import time
from collections import defaultdict, deque
from typing import Any

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
        self._histories: dict[str, deque] = defaultdict(lambda: deque(maxlen=hist_maxlen))
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

    def _cleanup_expired(self, storage: dict[str, dict[str, dict]]) -> None:
        """Remove expired items from storage."""
        for user_id in list(storage.keys()):
            user_data = storage[user_id]
            for key in list(user_data.keys()):
                if self._is_expired(user_data[key]):
                    del user_data[key]
            # Remove empty user data
            if not user_data:
                del storage[user_id]

    def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            time.sleep(self._cleanup_interval)
            with self._lock:
                self._cleanup_expired(self._ctx)
                self._cleanup_expired(self._ephemeral)
                self._cleanup_expired(self._dedup)
                self._cleanup_expired(self._rate)

    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        """Check if a key has been seen before for deduplication."""
        with self._lock:
            user_dedup = self._dedup[user_id]

            # Check if key exists and not expired
            if key in user_dedup:
                if not self._is_expired(user_dedup[key]):
                    return True
                else:
                    # Remove expired entry
                    del user_dedup[key]

            # First time seeing this key, store it
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            user_dedup[key] = {"value": True, "expires_at": expires_at}
            return False

    def append_history(self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200) -> None:
        """Append a message to user's history."""
        with self._lock:
            # Create message dict
            message = {"role": role, "type": mtype, "content": content, "timestamp": time.time()}

            # Serialize message
            serialized_message = self._serialize_value(message)

            # Get or create history deque with specified maxlen
            if user_id not in self._histories:
                self._histories[user_id] = deque(maxlen=maxlen)
            elif self._histories[user_id].maxlen != maxlen:
                # Update maxlen if different
                old_deque = self._histories[user_id]
                new_deque = deque(old_deque, maxlen=maxlen)
                self._histories[user_id] = new_deque

            # Append to history
            self._histories[user_id].append(serialized_message)

    def recent_history(self, user_id: str, n: int = 20) -> list[dict]:
        """Get recent history messages."""
        with self._lock:
            if user_id not in self._histories:
                return []

            history = self._histories[user_id]
            # Get last n messages and reverse to have newest first
            recent = list(history)[-n:]
            recent.reverse()

            # Deserialize messages
            return [self._deserialize_value(msg) for msg in recent]

    def ctx_set(self, user_id: str, key: str, value: Any, ttl_sec: int | None = None) -> None:
        """Set context value."""
        with self._lock:
            expires_at = time.time() + ttl_sec if ttl_sec is not None and ttl_sec > 0 else None
            self._ctx[user_id][key] = {"value": self._serialize_value(value), "expires_at": expires_at}

    def ctx_get(self, user_id: str, key: str) -> Any | None:
        """Get context value."""
        with self._lock:
            if user_id not in self._ctx or key not in self._ctx[user_id]:
                return None

            item = self._ctx[user_id][key]
            if self._is_expired(item):
                del self._ctx[user_id][key]
                return None

            return self._deserialize_value(item["value"])

    def ctx_del(self, user_id: str, key: str) -> None:
        """Delete context value."""
        with self._lock:
            if user_id in self._ctx and key in self._ctx[user_id]:
                del self._ctx[user_id][key]

    def set_ephemeral(self, user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None:
        """Set ephemeral (temporary) value."""
        with self._lock:
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            self._ephemeral[user_id][key] = {"value": self._serialize_value(value), "expires_at": expires_at}

    def get_ephemeral(self, user_id: str, key: str) -> Any | None:
        """Get ephemeral value."""
        with self._lock:
            if user_id not in self._ephemeral or key not in self._ephemeral[user_id]:
                return None

            item = self._ephemeral[user_id][key]
            if self._is_expired(item):
                del self._ephemeral[user_id][key]
                return None

            return self._deserialize_value(item["value"])

    def del_ephemeral(self, user_id: str, key: str) -> None:
        """Delete ephemeral value."""
        with self._lock:
            if user_id in self._ephemeral and key in self._ephemeral[user_id]:
                del self._ephemeral[user_id][key]

    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        """Increment rate counter."""
        with self._lock:
            user_rate = self._rate[user_id]

            # Check if bucket exists and not expired
            if bucket in user_rate:
                item = user_rate[bucket]
                if self._is_expired(item):
                    # Reset counter if expired
                    del user_rate[bucket]
                else:
                    # Increment existing counter
                    current_count = self._deserialize_value(item["value"])
                    new_count = current_count + 1
                    item["value"] = self._serialize_value(new_count)
                    return new_count

            # First increment or after expiration
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            user_rate[bucket] = {"value": self._serialize_value(1), "expires_at": expires_at}
            return 1
