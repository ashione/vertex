"""File-based implementation of Memory interface."""

import json
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from .memory import Memory


class FileMemory(Memory):
    """File-based implementation of Memory interface.

    Features:
    - Persistent storage using files
    - Thread-safe operations with file locking
    - TTL support with expiration filtering
    - JSON serialization for all stored values
    - JSONL format for history records
    """

    def __init__(self, storage_dir: str = "./memory_data", hist_maxlen: int = 200):
        """Initialize FileMemory.

        Args:
            storage_dir: Directory to store memory files
            hist_maxlen: Default maximum history length
        """
        self._storage_dir = Path(storage_dir)
        self._hist_maxlen = hist_maxlen

        # Create storage directory
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        # Thread safety
        self._lock = threading.RLock()

        # File paths
        self._histories_dir = self._storage_dir / "histories"
        self._ctx_dir = self._storage_dir / "context"
        self._ephemeral_dir = self._storage_dir / "ephemeral"
        self._dedup_dir = self._storage_dir / "dedup"
        self._rate_dir = self._storage_dir / "rate"

        # Create subdirectories
        for dir_path in [self._histories_dir, self._ctx_dir, self._ephemeral_dir, self._dedup_dir, self._rate_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, base_dir: Path, user_id: str, key: str = None) -> Path:
        """Get file path for user data."""
        if key:
            return base_dir / f"{user_id}_{key}.json"
        else:
            return base_dir / f"{user_id}.jsonl"

    def _read_json_file(self, file_path: Path) -> dict | None:
        """Read JSON file safely."""
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return None

    def _write_json_file(self, file_path: Path, data: dict) -> None:
        """Write JSON file safely."""
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _is_expired(self, item: dict) -> bool:
        """Check if an item is expired."""
        expires_at = item.get("expires_at")
        if expires_at is None:
            return False
        return time.time() > expires_at

    def _read_history_file(self, user_id: str) -> list[dict]:
        """Read history from JSONL file."""
        file_path = self._get_file_path(self._histories_dir, user_id)
        history = []

        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            history.append(json.loads(line))
        except (json.JSONDecodeError, IOError):
            pass

        return history

    def _write_history_file(self, user_id: str, history: list[dict]) -> None:
        """Write history to JSONL file."""
        file_path = self._get_file_path(self._histories_dir, user_id)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            for message in history:
                json.dump(message, f, ensure_ascii=False)
                f.write("\n")

    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        """Check if a key has been seen before for deduplication."""
        with self._lock:
            file_path = self._get_file_path(self._dedup_dir, user_id, key)

            # Check if file exists and not expired
            data = self._read_json_file(file_path)
            if data and not self._is_expired(data):
                return True

            # First time seeing this key, store it
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            new_data = {"value": True, "expires_at": expires_at}
            self._write_json_file(file_path, new_data)
            return False

    def append_history(self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200) -> None:
        """Append a message to user's history."""
        with self._lock:
            # Create message dict
            message = {"role": role, "type": mtype, "content": content, "timestamp": time.time()}

            # Read existing history
            history = self._read_history_file(user_id)

            # Add new message and maintain maxlen
            history.append(message)
            if len(history) > maxlen:
                history = history[-maxlen:]

            # Write back to file
            self._write_history_file(user_id, history)

    def recent_history(self, user_id: str, n: int = 20) -> list[dict]:
        """Get recent history messages."""
        with self._lock:
            history = self._read_history_file(user_id)

            # Get last n messages and reverse to have newest first
            recent = history[-n:] if history else []
            recent.reverse()

            return recent

    def ctx_set(self, user_id: str, key: str, value: Any, ttl_sec: int | None = None) -> None:
        """Set context value."""
        with self._lock:
            file_path = self._get_file_path(self._ctx_dir, user_id, key)
            expires_at = time.time() + ttl_sec if ttl_sec is not None and ttl_sec > 0 else None

            data = {"value": value, "expires_at": expires_at}
            self._write_json_file(file_path, data)

    def ctx_get(self, user_id: str, key: str) -> Any | None:
        """Get context value."""
        with self._lock:
            file_path = self._get_file_path(self._ctx_dir, user_id, key)
            data = self._read_json_file(file_path)

            if not data:
                return None

            if self._is_expired(data):
                # Remove expired file
                try:
                    file_path.unlink()
                except OSError:
                    pass
                return None

            return data["value"]

    def ctx_del(self, user_id: str, key: str) -> None:
        """Delete context value."""
        with self._lock:
            file_path = self._get_file_path(self._ctx_dir, user_id, key)
            try:
                file_path.unlink()
            except OSError:
                pass

    def set_ephemeral(self, user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None:
        """Set ephemeral (temporary) value."""
        with self._lock:
            file_path = self._get_file_path(self._ephemeral_dir, user_id, key)
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None

            data = {"value": value, "expires_at": expires_at}
            self._write_json_file(file_path, data)

    def get_ephemeral(self, user_id: str, key: str) -> Any | None:
        """Get ephemeral value."""
        with self._lock:
            file_path = self._get_file_path(self._ephemeral_dir, user_id, key)
            data = self._read_json_file(file_path)

            if not data:
                return None

            if self._is_expired(data):
                # Remove expired file
                try:
                    file_path.unlink()
                except OSError:
                    pass
                return None

            return data["value"]

    def del_ephemeral(self, user_id: str, key: str) -> None:
        """Delete ephemeral value."""
        with self._lock:
            file_path = self._get_file_path(self._ephemeral_dir, user_id, key)
            try:
                file_path.unlink()
            except OSError:
                pass

    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        """Increment rate counter."""
        with self._lock:
            file_path = self._get_file_path(self._rate_dir, user_id, bucket)
            data = self._read_json_file(file_path)

            # Check if file exists and not expired
            if data and not self._is_expired(data):
                # Increment existing counter
                new_count = data["value"] + 1
                data["value"] = new_count
                self._write_json_file(file_path, data)
                return new_count

            # First increment or after expiration
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            new_data = {"value": 1, "expires_at": expires_at}
            self._write_json_file(file_path, new_data)
            return 1

    def cleanup_expired(self) -> None:
        """Manually cleanup expired files."""
        with self._lock:
            for dir_path in [self._ctx_dir, self._ephemeral_dir, self._dedup_dir, self._rate_dir]:
                for file_path in dir_path.glob("*.json"):
                    data = self._read_json_file(file_path)
                    if data and self._is_expired(data):
                        try:
                            file_path.unlink()
                        except OSError:
                            pass
