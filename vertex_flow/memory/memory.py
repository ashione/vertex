"""Memory interface definition."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class Memory(ABC):
    """Memory interface for Vertexflow.

    Provides unified interface for managing:
    - Message deduplication (seen)
    - History records (bounded queue)
    - Context storage (ctx_*)
    - Temporary data (ephemeral_*)
    - Rate limiting (incr_rate)
    """

    @abstractmethod
    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        """Check if a key has been seen before for deduplication.

        Args:
            user_id: User identifier
            key: Deduplication key
            ttl_sec: Time to live in seconds (default: 3600)

        Returns:
            True if key was seen before, False if first time
        """
        pass

    @abstractmethod
    def append_history(self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200) -> None:
        """Append a message to user's history.

        Args:
            user_id: User identifier
            role: Message role (user, assistant, system, etc.)
            mtype: Message type
            content: Message content as dict
            maxlen: Maximum history length (default: 200)
        """
        pass

    @abstractmethod
    def recent_history(self, user_id: str, n: int = 20) -> List[dict]:
        """Get recent history messages.

        Args:
            user_id: User identifier
            n: Number of recent messages to return (default: 20)

        Returns:
            List of recent messages, newest first
        """
        pass

    @abstractmethod
    def ctx_set(self, user_id: str, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        """Set context value.

        Args:
            user_id: User identifier
            key: Context key
            value: Value to store (must be JSON serializable)
            ttl_sec: Time to live in seconds (None for no expiration)
        """
        pass

    @abstractmethod
    def ctx_get(self, user_id: str, key: str) -> Optional[Any]:
        """Get context value.

        Args:
            user_id: User identifier
            key: Context key

        Returns:
            Stored value or None if not found/expired
        """
        pass

    @abstractmethod
    def ctx_del(self, user_id: str, key: str) -> None:
        """Delete context value.

        Args:
            user_id: User identifier
            key: Context key
        """
        pass

    @abstractmethod
    def set_ephemeral(self, user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None:
        """Set ephemeral (temporary) value.

        Args:
            user_id: User identifier
            key: Ephemeral key
            value: Value to store (must be JSON serializable)
            ttl_sec: Time to live in seconds (default: 1800)
        """
        pass

    @abstractmethod
    def get_ephemeral(self, user_id: str, key: str) -> Optional[Any]:
        """Get ephemeral value.

        Args:
            user_id: User identifier
            key: Ephemeral key

        Returns:
            Stored value or None if not found/expired
        """
        pass

    @abstractmethod
    def del_ephemeral(self, user_id: str, key: str) -> None:
        """Delete ephemeral value.

        Args:
            user_id: User identifier
            key: Ephemeral key
        """
        pass

    @abstractmethod
    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        """Increment rate counter.

        Args:
            user_id: User identifier
            bucket: Rate limiting bucket name
            ttl_sec: Time to live in seconds (default: 60)

        Returns:
            Current count after increment
        """
        pass
