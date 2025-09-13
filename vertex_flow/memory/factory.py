# Factory for creating memory implementations

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .file_store import FileMemory
from .hybrid_store import HybridMemory
from .inmem_store import InnerMemory
from .memory import Memory
from .rds_store import RDSMemory
from .redis_store import RedisMemory


class MemoryFactory:
    """Factory for creating memory implementations.

    This class provides a convenient way to create different memory implementations
    based on configuration parameters. It also helps with type mapping and default
    configurations.

    Available types:
    - "inner", "memory", "inmem": In-memory implementation for fast access and testing
    - "file": File-based implementation for persistence without external dependencies
    - "redis": Redis-based implementation for distributed caching
    - "rds": Relational database implementation for persistent storage
    - "hybrid": Hybrid implementation combining Redis for cache and RDS for persistence
    """

    _memory_types = {
        "inner": InnerMemory,
        "memory": InnerMemory,  # alias for backward compatibility
        "inmem": InnerMemory,  # alias for backward compatibility
        "file": FileMemory,
        "redis": RedisMemory,
        "rds": RDSMemory,
        "hybrid": HybridMemory,
    }

    @classmethod
    def create_memory(cls, memory_type: str = "inner", **kwargs) -> Memory:
        """Create a memory instance based on type.

        Args:
            memory_type: Type of memory to create
            **kwargs: Additional configuration parameters depending on type

        Returns:
            Memory instance
        """
        memory_type = memory_type.lower()

        if memory_type not in cls._memory_types:
            available_types = ", ".join(cls._memory_types.keys())
            raise ValueError(f"Unsupported memory type: {memory_type}. " f"Available types: {available_types}")

        # For hybrid, pass through specific parameters
        if memory_type == "hybrid":
            return HybridMemory(
                redis_url=kwargs.get("redis_url"),
                db_url=kwargs.get("db_url"),
                hist_maxlen=kwargs.get("hist_maxlen", 200),
                prefix=kwargs.get("prefix", "vf:"),
                redis_client=kwargs.get("redis_client"),
            )

        # Other types use direct constructor
        impl_class = cls._memory_types[memory_type]
        return impl_class(**kwargs)

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> Memory:
        """Create a memory instance from a configuration dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            Memory instance
        """
        memory_type = config.get("type", "inner")
        kwargs = {k: v for k, v in config.items() if k != "type"}
        return cls.create_memory(memory_type, **kwargs)

    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get a list of available memory types.

        Returns:
            List[str]: A list of supported memory type identifiers.
        """
        return list(cls._memory_types.keys())

    @classmethod
    def register_memory_type(cls, name: str, impl_class: Any) -> None:
        """Register a new memory implementation type at runtime.

        Args:
            name: Identifier used when calling create_memory
            impl_class: The class to instantiate for this type
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        cls._memory_types[name.lower()] = impl_class

    @classmethod
    def get_default_config(cls, memory_type: str = "inner") -> Dict[str, Any]:
        """Get default configuration for a memory type.

        Args:
            memory_type: Type of memory

        Returns:
            Default configuration parameters for the specified memory type

        Examples:
            >>> config = MemoryFactory.get_default_config("inner")
            >>> print(config)
            {'type': 'inner', 'hist_maxlen': 200, 'cleanup_interval_sec': 300}
        """
        memory_type = memory_type.lower()

        # Build redis url from environment variables to avoid hardcoding sensitive strings
        default_redis_url = (
            f"redis://{os.getenv('VF_REDIS_HOST', 'localhost')}:{os.getenv('VF_REDIS_PORT', '6379')}/"
            f"{os.getenv('VF_REDIS_DB', '0')}"
        )
        default_rds_url = os.getenv("VF_RDS_URL", "sqlite:///:memory:")

        if memory_type in ["inner", "memory", "inmem"]:
            return {"type": "inner", "hist_maxlen": 200, "cleanup_interval_sec": 300}
        elif memory_type == "file":
            return {"type": "file", "storage_dir": "./memory_data", "hist_maxlen": 200}
        elif memory_type == "redis":
            return {"type": "redis", "url": default_redis_url, "hist_maxlen": 200}
        elif memory_type == "rds":
            return {"type": "rds", "db_url": default_rds_url, "hist_maxlen": 200}
        elif memory_type == "hybrid":
            return {
                "type": "hybrid",
                "redis_url": default_redis_url,
                "db_url": default_rds_url,
                "hist_maxlen": 200,
            }
        else:
            available_types = ", ".join(cls._memory_types.keys())
            raise ValueError(f"Unsupported memory type: {memory_type}. " f"Available types: {available_types}")


# Convenience functions for easier usage


def create_memory(memory_type: str = "inner", **kwargs) -> Memory:
    """Convenience function to create a memory instance.

    Args:
        memory_type: Type of memory to create
        **kwargs: Additional configuration parameters

    Returns:
        Memory instance
    """
    return MemoryFactory.create_memory(memory_type, **kwargs)


def create_memory_from_config(config: Dict[str, Any]) -> Memory:
    """Convenience function to create a memory instance from config.

    Args:
        config: Configuration dictionary

    Returns:
        Memory instance
    """
    return MemoryFactory.create_from_config(config)
