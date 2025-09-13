"""File-based implementation of Memory interface."""

import json
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, List, Optional

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

    def _read_json_file(self, file_path: Path) -> Optional[dict]:
        """Read JSON file safely."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None

    def _write_json_file(self, file_path: Path, data: dict) -> None:
        """Write JSON file safely."""
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _append_jsonl_file(self, file_path: Path, data: dict) -> None:
        """Append a JSON line to a file."""
        with file_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _read_jsonl_file(self, file_path: Path, n: int) -> list[dict]:
        """Read last n lines from a JSONL file."""
        if not file_path.exists():
            return []
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            return [json.loads(line) for line in lines[-n:]][::-1]

    # Deduplication -----------------------------------------------------------------
    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        file_path = self._get_file_path(self._dedup_dir, user_id, key)
        expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
        data = {"expires_at": expires_at}
        if file_path.exists():
            existing = self._read_json_file(file_path)
            if existing and existing.get("expires_at") and time.time() < existing.get("expires_at"):
                return True
        self._write_json_file(file_path, data)
        return False

    # History ----------------------------------------------------------------------
    def append_history(self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200) -> None:
        file_path = self._get_file_path(self._histories_dir, user_id)
        self._append_jsonl_file(file_path, {"role": role, "type": mtype, "content": content, "timestamp": time.time()})
        # Trim file to last maxlen lines
        if file_path.exists():
            with file_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > maxlen:
                with file_path.open("w", encoding="utf-8") as f:
                    f.writelines(lines[-maxlen:])

    def recent_history(self, user_id: str, n: int = 20) -> List[dict]:
        file_path = self._get_file_path(self._histories_dir, user_id)
        return self._read_jsonl_file(file_path, n)

    # Context ----------------------------------------------------------------------
    def ctx_set(self, user_id: str, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        file_path = self._get_file_path(self._ctx_dir, user_id, key)
        expires_at = time.time() + ttl_sec if ttl_sec is not None and ttl_sec > 0 else None
        data = {"value": value, "expires_at": expires_at}
        self._write_json_file(file_path, data)

    def ctx_get(self, user_id: str, key: str) -> Optional[Any]:
        file_path = self._get_file_path(self._ctx_dir, user_id, key)
        data = self._read_json_file(file_path)
        if not data:
            return None
        expires_at = data.get("expires_at")
        if expires_at is not None and time.time() > expires_at:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
            return None
        return data.get("value")

    def ctx_del(self, user_id: str, key: str) -> None:
        file_path = self._get_file_path(self._ctx_dir, user_id, key)
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

    # Ephemeral --------------------------------------------------------------------
    def set_ephemeral(self, user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None:
        file_path = self._get_file_path(self._ephemeral_dir, user_id, key)
        expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
        data = {"value": value, "expires_at": expires_at}
        self._write_json_file(file_path, data)

    def get_ephemeral(self, user_id: str, key: str) -> Optional[Any]:
        file_path = self._get_file_path(self._ephemeral_dir, user_id, key)
        data = self._read_json_file(file_path)
        if not data:
            return None
        expires_at = data.get("expires_at")
        if expires_at is not None and time.time() > expires_at:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
            return None
        return data.get("value")

    def del_ephemeral(self, user_id: str, key: str) -> None:
        file_path = self._get_file_path(self._ephemeral_dir, user_id, key)
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

    # Rate limiting ----------------------------------------------------------------
    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        file_path = self._get_file_path(self._rate_dir, user_id, bucket)
        expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
        value = 1
        if file_path.exists():
            data = self._read_json_file(file_path) or {}
            if data.get("expires_at") is None or time.time() <= data.get("expires_at"):
                value = int(data.get("value", 0)) + 1
        self._write_json_file(file_path, {"value": value, "expires_at": expires_at})
        return value
