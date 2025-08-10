"""Example demonstrating Memory Factory usage."""

import json
import tempfile
from pathlib import Path

from vertex_flow.memory import MemoryFactory, create_memory, create_memory_from_config


def demo_factory_basic():
    """Demonstrate basic factory usage."""
    print("=== Basic Factory Usage ===")

    # Create different memory types using factory
    inner_memory = MemoryFactory.create_memory("inner", hist_maxlen=50)
    print(f"Created InnerMemory with maxlen: {inner_memory._hist_maxlen}")

    with tempfile.TemporaryDirectory() as temp_dir:
        file_memory = MemoryFactory.create_memory("file", storage_dir=temp_dir)
        print(f"Created FileMemory with storage_dir: {file_memory._storage_dir}")

    # Show available types
    available_types = MemoryFactory.get_available_types()
    print(f"Available memory types: {available_types}")
    print()


def demo_config_based():
    """Demonstrate configuration-based memory creation."""
    print("=== Configuration-Based Creation ===")

    # Configuration for different environments
    configs = {
        "development": {"type": "inner", "hist_maxlen": 100, "cleanup_interval_sec": 60},
        "production": {"type": "file", "storage_dir": "./prod_memory", "hist_maxlen": 1000},
        "testing": {"type": "inner", "hist_maxlen": 10},
    }

    # Create memory instances based on environment
    for env, config in configs.items():
        print(f"Environment: {env}")
        print(f"Config: {json.dumps(config, indent=2)}")

        if config["type"] == "file":
            # Use temporary directory for demo
            with tempfile.TemporaryDirectory() as temp_dir:
                config_copy = config.copy()
                config_copy["storage_dir"] = temp_dir
                memory = create_memory_from_config(config_copy)
                print(f"Created: {type(memory).__name__}")
                print(f"Storage dir: {memory._storage_dir}")
        else:
            memory = create_memory_from_config(config)
            print(f"Created: {type(memory).__name__}")
            print(f"Max history length: {memory._hist_maxlen}")

        print()


def demo_default_configs():
    """Demonstrate default configuration retrieval."""
    print("=== Default Configurations ===")

    # Get default configs for different memory types
    for memory_type in ["inner", "file"]:
        default_config = MemoryFactory.get_default_config(memory_type)
        print(f"Default config for '{memory_type}':")
        print(json.dumps(default_config, indent=2))
        print()


def demo_runtime_switching():
    """Demonstrate runtime memory type switching."""
    print("=== Runtime Memory Type Switching ===")

    # Simulate switching between memory types based on conditions
    user_preferences = [
        {"user_id": "user1", "prefer_persistent": True},
        {"user_id": "user2", "prefer_persistent": False},
        {"user_id": "user3", "prefer_persistent": True},
    ]

    memories = {}

    for user_pref in user_preferences:
        user_id = user_pref["user_id"]
        prefer_persistent = user_pref["prefer_persistent"]

        if prefer_persistent:
            # Use file-based memory for persistent storage
            with tempfile.TemporaryDirectory() as temp_dir:
                config = {"type": "file", "storage_dir": temp_dir, "hist_maxlen": 200}
                memory = create_memory_from_config(config)
                memory_type = "FileMemory (persistent)"
        else:
            # Use in-memory storage for faster access
            config = {"type": "inner", "hist_maxlen": 100}
            memory = create_memory_from_config(config)
            memory_type = "InnerMemory (fast)"

        memories[user_id] = memory
        print(f"{user_id}: Using {memory_type}")

        # Test the memory
        memory.append_history(user_id, "user", "text", {"text": f"Hello from {user_id}"})
        history = memory.recent_history(user_id)
        print(f"  History length: {len(history)}")
        if history:
            print(f"  Latest message: {history[0]['content']['text']}")

    print()


def demo_custom_memory_registration():
    """Demonstrate custom memory type registration."""
    print("=== Custom Memory Type Registration ===")

    # Define a simple custom memory class
    class MockMemory:
        def __init__(self, mock_param="default"):
            self.mock_param = mock_param
            self._data = {}

        def seen(self, user_id, key, ttl_sec=3600):
            return False

        def append_history(self, user_id, role, mtype, content, maxlen=200):
            if user_id not in self._data:
                self._data[user_id] = []
            self._data[user_id].append({"role": role, "type": mtype, "content": content})

        def recent_history(self, user_id, n=20):
            return self._data.get(user_id, [])[-n:][::-1]

    # Register the custom memory type
    MemoryFactory.register_memory_type("mock", MockMemory)

    # Create instance of custom memory
    custom_memory = create_memory("mock", mock_param="custom_value")
    print(f"Created custom memory: {type(custom_memory).__name__}")
    print(f"Custom parameter: {custom_memory.mock_param}")

    # Test the custom memory
    custom_memory.append_history("test_user", "user", "text", {"text": "Custom memory test"})
    history = custom_memory.recent_history("test_user")
    print(f"Custom memory history: {history}")

    # Show updated available types
    available_types = MemoryFactory.get_available_types()
    print(f"Available types after registration: {available_types}")
    print()


def demo_convenience_functions():
    """Demonstrate convenience functions."""
    print("=== Convenience Functions ===")

    # Using convenience functions instead of factory class
    memory1 = create_memory("inner", hist_maxlen=75)
    print(f"Created via create_memory(): {type(memory1).__name__}")

    config = {"type": "inner", "hist_maxlen": 125}
    memory2 = create_memory_from_config(config)
    print(f"Created via create_memory_from_config(): {type(memory2).__name__}")

    # Test both memories
    for i, memory in enumerate([memory1, memory2], 1):
        memory.append_history(f"user{i}", "user", "text", {"text": f"Message {i}"})
        history = memory.recent_history(f"user{i}")
        print(f"Memory {i} history length: {len(history)}")

    print()


if __name__ == "__main__":
    print("Memory Factory Examples\n")

    demo_factory_basic()
    demo_config_based()
    demo_default_configs()
    demo_runtime_switching()
    demo_custom_memory_registration()
    demo_convenience_functions()

    print("All examples completed successfully!")
