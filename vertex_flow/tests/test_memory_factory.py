"""Tests for Memory Factory."""

import shutil
import tempfile
from pathlib import Path

import importlib
import pytest

from vertex_flow.memory import (
    FileMemory,
    HybridMemory,
    InnerMemory,
    RDSMemory,
    RedisMemory,
    Memory,
    MemoryFactory,
    create_memory,
    create_memory_from_config,
)

has_sqlalchemy = importlib.util.find_spec("sqlalchemy") is not None


class TestMemoryFactory:
    """Test cases for MemoryFactory."""

    def test_create_inner_memory(self):
        """Test creating InnerMemory through factory."""
        memory = MemoryFactory.create_memory("inner", hist_maxlen=100)
        assert isinstance(memory, InnerMemory)
        assert memory._hist_maxlen == 100

    def test_create_inner_memory_aliases(self):
        """Test creating InnerMemory through aliases."""
        # Test different aliases
        memory1 = MemoryFactory.create_memory("memory")
        memory2 = MemoryFactory.create_memory("inmem")
        memory3 = MemoryFactory.create_memory("INNER")  # case insensitive

        assert isinstance(memory1, InnerMemory)
        assert isinstance(memory2, InnerMemory)
        assert isinstance(memory3, InnerMemory)

    def test_create_file_memory(self):
        """Test creating FileMemory through factory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryFactory.create_memory("file", storage_dir=temp_dir)
            assert isinstance(memory, FileMemory)
            assert memory._storage_dir == Path(temp_dir)

    def test_create_redis_memory(self):
        """Test creating RedisMemory through factory."""
        class DummyRedis:
            pass

        memory = MemoryFactory.create_memory("redis", client=DummyRedis())
        assert isinstance(memory, RedisMemory)

    @pytest.mark.skipif(not has_sqlalchemy, reason="sqlalchemy required")
    def test_create_rds_memory(self):
        """Test creating RDSMemory through factory."""
        memory = MemoryFactory.create_memory("rds", db_url="sqlite:///:memory:")
        assert isinstance(memory, RDSMemory)

    @pytest.mark.skipif(not has_sqlalchemy, reason="sqlalchemy required")
    def test_create_hybrid_memory(self):
        class DummyRedis:
            pass

        memory = MemoryFactory.create_memory(
            "hybrid", redis_client=DummyRedis(), db_url="sqlite:///:memory:"
        )
        assert isinstance(memory, HybridMemory)

    def test_create_memory_invalid_type(self):
        """Test creating memory with invalid type."""
        with pytest.raises(ValueError, match="Unsupported memory type: invalid"):
            MemoryFactory.create_memory("invalid")

    def test_create_from_config_inner(self):
        """Test creating InnerMemory from config."""
        config = {"type": "inner", "hist_maxlen": 150, "cleanup_interval_sec": 600}
        memory = MemoryFactory.create_from_config(config)
        assert isinstance(memory, InnerMemory)
        assert memory._hist_maxlen == 150

    def test_create_from_config_file(self):
        """Test creating FileMemory from config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"type": "file", "storage_dir": temp_dir, "hist_maxlen": 300}
            memory = MemoryFactory.create_from_config(config)
            assert isinstance(memory, FileMemory)
            assert memory._storage_dir == Path(temp_dir)
            assert memory._hist_maxlen == 300

    def test_create_from_config_default_type(self):
        """Test creating memory from config without type (should default to inner)."""
        config = {"hist_maxlen": 250}
        memory = MemoryFactory.create_from_config(config)
        assert isinstance(memory, InnerMemory)
        assert memory._hist_maxlen == 250

    def test_create_from_config_preserves_original(self):
        """Test that create_from_config doesn't modify original config."""
        config = {"type": "inner", "hist_maxlen": 100}
        original_config = config.copy()

        MemoryFactory.create_from_config(config)
        assert config == original_config

    def test_register_memory_type(self):
        """Test registering a new memory type."""

        class CustomMemory:
            def __init__(self, custom_param=None):
                self.custom_param = custom_param

        MemoryFactory.register_memory_type("custom", CustomMemory)

        # Test creating the custom memory
        memory = MemoryFactory.create_memory("custom", custom_param="test")
        assert isinstance(memory, CustomMemory)
        assert memory.custom_param == "test"

        # Test case insensitive
        memory2 = MemoryFactory.create_memory("CUSTOM")
        assert isinstance(memory2, CustomMemory)

    def test_get_available_types(self):
        """Test getting available memory types."""
        types = MemoryFactory.get_available_types()
        assert "inner" in types
        assert "memory" in types
        assert "inmem" in types
        assert "file" in types
        assert "redis" in types
        assert "rds" in types
        assert "hybrid" in types
        assert isinstance(types, list)

    def test_get_default_config_inner(self):
        """Test getting default config for inner memory."""
        config = MemoryFactory.get_default_config("inner")
        expected = {"type": "inner", "hist_maxlen": 200, "cleanup_interval_sec": 300}
        assert config == expected

    def test_get_default_config_file(self):
        """Test getting default config for file memory."""
        config = MemoryFactory.get_default_config("file")
        expected = {"type": "file", "storage_dir": "./memory_data", "hist_maxlen": 200}
        assert config == expected

    def test_get_default_config_redis(self):
        """Test getting default config for redis memory."""
        config = MemoryFactory.get_default_config("redis")
        expected = {"type": "redis", "url": "redis://localhost:6379/0", "hist_maxlen": 200}
        assert config == expected

    @pytest.mark.skipif(not has_sqlalchemy, reason="sqlalchemy required")
    def test_get_default_config_rds(self):
        """Test getting default config for rds memory."""
        config = MemoryFactory.get_default_config("rds")
        expected = {"type": "rds", "db_url": "sqlite:///:memory:", "hist_maxlen": 200}
        assert config == expected

    @pytest.mark.skipif(not has_sqlalchemy, reason="sqlalchemy required")
    def test_get_default_config_hybrid(self):
        config = MemoryFactory.get_default_config("hybrid")
        expected = {
            "type": "hybrid",
            "redis_url": "redis://localhost:6379/0",
            "db_url": "sqlite:///:memory:",
            "hist_maxlen": 200,
        }
        assert config == expected

    def test_get_default_config_invalid_type(self):
        """Test getting default config for invalid type."""
        with pytest.raises(ValueError, match="Unsupported memory type: invalid"):
            MemoryFactory.get_default_config("invalid")

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test create_memory function
        memory1 = create_memory("inner", hist_maxlen=123)
        assert isinstance(memory1, InnerMemory)
        assert memory1._hist_maxlen == 123

        # Test create_memory_from_config function
        config = {"type": "inner", "hist_maxlen": 456}
        memory2 = create_memory_from_config(config)
        assert isinstance(memory2, InnerMemory)
        assert memory2._hist_maxlen == 456

    def test_memory_interface_compliance(self):
        """Test that created memories implement Memory interface."""
        inner_memory = MemoryFactory.create_memory("inner")
        # Test that memory is instance of Memory abstract base class
        assert isinstance(inner_memory, Memory)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_memory = MemoryFactory.create_memory("file", storage_dir=temp_dir)
            assert isinstance(file_memory, Memory)

        class DummyRedis:
            pass

        redis_memory = MemoryFactory.create_memory("redis", client=DummyRedis())
        assert isinstance(redis_memory, Memory)

        if has_sqlalchemy:
            rds_memory = MemoryFactory.create_memory("rds", db_url="sqlite:///:memory:")
            assert isinstance(rds_memory, Memory)

            hybrid_memory = MemoryFactory.create_memory(
                "hybrid", redis_client=DummyRedis(), db_url="sqlite:///:memory:"
            )
            assert isinstance(hybrid_memory, Memory)

    def test_factory_integration(self):
        """Test end-to-end factory usage."""
        # Test with inner memory
        config1 = {"type": "inner", "hist_maxlen": 50}
        memory1 = create_memory_from_config(config1)

        memory1.append_history("user1", "user", "text", {"text": "Hello"})
        memory1.append_history("user1", "assistant", "text", {"text": "World"})
        history = memory1.recent_history("user1")
        assert len(history) == 2
        assert history[0]["content"]["text"] == "World"  # newest first
        assert history[1]["content"]["text"] == "Hello"

        # Test with file memory
        with tempfile.TemporaryDirectory() as temp_dir:
            config2 = {"type": "file", "storage_dir": temp_dir}
            memory2 = create_memory_from_config(config2)

            memory2.append_history("user2", "user", "text", {"text": "File test"})
            history = memory2.recent_history("user2")
            assert len(history) == 1
            assert history[0]["content"]["text"] == "File test"
