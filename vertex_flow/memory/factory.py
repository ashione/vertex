"""Memory factory for creating memory instances based on configuration."""

from typing import Any, Dict, Optional

from .file_store import FileMemory
from .inmem_store import InnerMemory
from .memory import Memory


class MemoryFactory:
    """Factory for creating memory instances based on configuration."""

    # Registry of available memory types
    _memory_types = {
        "inner": InnerMemory,
        "memory": InnerMemory,  # alias for backward compatibility
        "inmem": InnerMemory,  # alias for backward compatibility
        "file": FileMemory,
    }

    @classmethod
    def create_memory(cls, memory_type: str = "inner", **kwargs) -> Memory:
        """Create a memory instance based on type and configuration.

        Args:
            memory_type: Type of memory to create ("inner", "file")
            **kwargs: Additional configuration parameters for the memory instance

        Returns:
            Memory instance

        Raises:
            ValueError: If memory_type is not supported

        Examples:
            >>> # Create in-memory storage
            >>> memory = MemoryFactory.create_memory("inner", hist_maxlen=100)

            >>> # Create file-based storage
            >>> memory = MemoryFactory.create_memory("file", storage_dir="./data")
        """
        memory_type = memory_type.lower()

        if memory_type not in cls._memory_types:
            available_types = ", ".join(cls._memory_types.keys())
            raise ValueError(f"Unsupported memory type: {memory_type}. " f"Available types: {available_types}")

        memory_class = cls._memory_types[memory_type]
        return memory_class(**kwargs)

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> Memory:
        """Create a memory instance from configuration dictionary.

        Args:
            config: Configuration dictionary containing memory settings

        Returns:
            Memory instance

        Examples:
            >>> config = {
            ...     "type": "inner",
            ...     "hist_maxlen": 200,
            ...     "cleanup_interval_sec": 300
            ... }
            >>> memory = MemoryFactory.create_from_config(config)

            >>> config = {
            ...     "type": "file",
            ...     "storage_dir": "./memory_data",
            ...     "hist_maxlen": 500
            ... }
            >>> memory = MemoryFactory.create_from_config(config)
        """
        config = config.copy()  # Don't modify original config
        memory_type = config.pop("type", "inner")
        return cls.create_memory(memory_type, **config)

    @classmethod
    def register_memory_type(cls, name: str, memory_class: type) -> None:
        """Register a new memory type.

        Args:
            name: Name of the memory type
            memory_class: Memory class to register

        Examples:
            >>> class CustomMemory:
            ...     pass
            >>> MemoryFactory.register_memory_type("custom", CustomMemory)
        """
        cls._memory_types[name.lower()] = memory_class

    @classmethod
    def get_available_types(cls) -> list[str]:
        """Get list of available memory types.

        Returns:
            List of available memory type names
        """
        return list(cls._memory_types.keys())

    @classmethod
    def get_default_config(cls, memory_type: str = "inner") -> Dict[str, Any]:
        """Get default configuration for a memory type.

        Args:
            memory_type: Type of memory

        Returns:
            Default configuration dictionary

        Examples:
            >>> config = MemoryFactory.get_default_config("inner")
            >>> print(config)
            {'type': 'inner', 'hist_maxlen': 200, 'cleanup_interval_sec': 300}
        """
        memory_type = memory_type.lower()

        if memory_type in ["inner", "memory", "inmem"]:
            return {"type": "inner", "hist_maxlen": 200, "cleanup_interval_sec": 300}
        elif memory_type == "file":
            return {"type": "file", "storage_dir": "./memory_data", "hist_maxlen": 200}
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
