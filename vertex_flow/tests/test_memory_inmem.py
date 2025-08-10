"""Tests for InMemoryMemory implementation."""

import threading
import time
from unittest.mock import patch

import pytest

from vertex_flow.memory import InnerMemory


class TestInnerMemory:
    """Test cases for InnerMemory."""

    def setup_method(self):
        """Setup test instance."""
        self.memory = InnerMemory(hist_maxlen=5, cleanup_interval_sec=1)

    def test_seen_deduplication(self):
        """Test seen method for deduplication."""
        user_id = "user1"
        key = "test_key"

        # First time should return False
        assert self.memory.seen(user_id, key, ttl_sec=1) is False

        # Second time should return True
        assert self.memory.seen(user_id, key, ttl_sec=1) is True

        # Wait for expiration
        time.sleep(1.1)

        # After expiration should return False again
        assert self.memory.seen(user_id, key, ttl_sec=1) is False

    def test_append_history_maxlen(self):
        """Test append_history with length limit."""
        user_id = "user1"

        # Add more messages than maxlen
        for i in range(10):
            self.memory.append_history(user_id, "user", "text", {"text": f"message {i}"}, maxlen=5)

        # Should only keep last 5 messages
        history = self.memory.recent_history(user_id, n=10)
        assert len(history) == 5

        # Check order (newest first)
        assert history[0]["content"]["text"] == "message 9"
        assert history[4]["content"]["text"] == "message 5"

    def test_recent_history_order(self):
        """Test recent_history returns newest first."""
        user_id = "user1"

        # Add messages
        for i in range(3):
            self.memory.append_history(user_id, "user", "text", {"text": f"message {i}"})

        # Get recent history
        history = self.memory.recent_history(user_id, n=3)

        # Should be newest first
        assert len(history) == 3
        assert history[0]["content"]["text"] == "message 2"
        assert history[1]["content"]["text"] == "message 1"
        assert history[2]["content"]["text"] == "message 0"

    def test_ctx_operations(self):
        """Test context set/get/del operations."""
        user_id = "user1"
        key = "test_key"
        value = {"data": "test_value", "number": 42}

        # Set value
        self.memory.ctx_set(user_id, key, value)

        # Get value
        retrieved = self.memory.ctx_get(user_id, key)
        assert retrieved == value

        # Delete value
        self.memory.ctx_del(user_id, key)

        # Should return None after deletion
        assert self.memory.ctx_get(user_id, key) is None

    def test_ctx_ttl(self):
        """Test context TTL functionality."""
        user_id = "user1"
        key = "test_key"
        value = "test_value"

        # Set with short TTL
        self.memory.ctx_set(user_id, key, value, ttl_sec=1)

        # Should be available immediately
        assert self.memory.ctx_get(user_id, key) == value

        # Wait for expiration
        time.sleep(1.1)

        # Should return None after expiration
        assert self.memory.ctx_get(user_id, key) is None

    def test_ephemeral_operations(self):
        """Test ephemeral set/get/del operations."""
        user_id = "user1"
        key = "test_key"
        value = [1, 2, 3, "test"]

        # Set value
        self.memory.set_ephemeral(user_id, key, value)

        # Get value
        retrieved = self.memory.get_ephemeral(user_id, key)
        assert retrieved == value

        # Delete value
        self.memory.del_ephemeral(user_id, key)

        # Should return None after deletion
        assert self.memory.get_ephemeral(user_id, key) is None

    def test_ephemeral_ttl(self):
        """Test ephemeral TTL functionality."""
        user_id = "user1"
        key = "test_key"
        value = "test_value"

        # Set with short TTL
        self.memory.set_ephemeral(user_id, key, value, ttl_sec=1)

        # Should be available immediately
        assert self.memory.get_ephemeral(user_id, key) == value

        # Wait for expiration
        time.sleep(1.1)

        # Should return None after expiration
        assert self.memory.get_ephemeral(user_id, key) is None

    def test_incr_rate_counter(self):
        """Test rate limiting counter."""
        user_id = "user1"
        bucket = "api_calls"

        # First increment
        count1 = self.memory.incr_rate(user_id, bucket, ttl_sec=2)
        assert count1 == 1

        # Second increment
        count2 = self.memory.incr_rate(user_id, bucket, ttl_sec=2)
        assert count2 == 2

        # Third increment
        count3 = self.memory.incr_rate(user_id, bucket, ttl_sec=2)
        assert count3 == 3

    def test_incr_rate_ttl_reset(self):
        """Test rate counter resets after TTL."""
        user_id = "user1"
        bucket = "api_calls"

        # Increment counter
        count1 = self.memory.incr_rate(user_id, bucket, ttl_sec=1)
        assert count1 == 1

        # Wait for expiration
        time.sleep(1.1)

        # Should reset to 1 after expiration
        count2 = self.memory.incr_rate(user_id, bucket, ttl_sec=1)
        assert count2 == 1

    def test_different_users_isolated(self):
        """Test that different users have isolated data."""
        user1 = "user1"
        user2 = "user2"
        key = "same_key"

        # Set different values for different users
        self.memory.ctx_set(user1, key, "value1")
        self.memory.ctx_set(user2, key, "value2")

        # Should get correct values for each user
        assert self.memory.ctx_get(user1, key) == "value1"
        assert self.memory.ctx_get(user2, key) == "value2"

        # Delete for one user shouldn't affect the other
        self.memory.ctx_del(user1, key)
        assert self.memory.ctx_get(user1, key) is None
        assert self.memory.ctx_get(user2, key) == "value2"

    def test_json_serialization(self):
        """Test JSON serialization of complex objects."""
        user_id = "user1"
        key = "complex_data"

        # Complex nested data
        value = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"inner": "value", "unicode": "测试中文"},
        }

        # Store and retrieve
        self.memory.ctx_set(user_id, key, value)
        retrieved = self.memory.ctx_get(user_id, key)

        # Should be identical
        assert retrieved == value

    def test_concurrent_append_history(self):
        """Test thread safety of append_history."""
        user_id = "user1"
        num_threads = 10
        messages_per_thread = 5

        def append_messages(thread_id):
            for i in range(messages_per_thread):
                self.memory.append_history(user_id, "user", "text", {"text": f"thread_{thread_id}_msg_{i}"})

        # Start multiple threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=append_messages, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that all messages were added
        history = self.memory.recent_history(user_id, n=100)
        assert len(history) == num_threads * messages_per_thread

    def test_background_cleanup(self):
        """Test background cleanup of expired items."""
        user_id = "user1"

        # Set items with short TTL
        self.memory.ctx_set(user_id, "key1", "value1", ttl_sec=1)
        self.memory.set_ephemeral(user_id, "key2", "value2", ttl_sec=1)
        self.memory.seen(user_id, "key3", ttl_sec=1)
        self.memory.incr_rate(user_id, "bucket1", ttl_sec=1)

        # Items should be available
        assert self.memory.ctx_get(user_id, "key1") == "value1"
        assert self.memory.get_ephemeral(user_id, "key2") == "value2"

        # Wait for expiration and cleanup
        time.sleep(2)

        # Items should be cleaned up
        assert self.memory.ctx_get(user_id, "key1") is None
        assert self.memory.get_ephemeral(user_id, "key2") is None

    def test_empty_history(self):
        """Test behavior with empty history."""
        user_id = "nonexistent_user"

        # Should return empty list for non-existent user
        history = self.memory.recent_history(user_id, n=10)
        assert history == []

    def test_zero_ttl(self):
        """Test behavior with zero TTL."""
        user_id = "user1"

        # Zero TTL should mean no expiration
        self.memory.ctx_set(user_id, "key1", "value1", ttl_sec=0)

        # Should still be available after some time
        time.sleep(0.1)
        assert self.memory.ctx_get(user_id, "key1") == "value1"

    def test_negative_ttl(self):
        """Test behavior with negative TTL."""
        user_id = "user1"

        # Negative TTL should mean no expiration
        self.memory.ctx_set(user_id, "key1", "value1", ttl_sec=-1)

        # Should still be available
        assert self.memory.ctx_get(user_id, "key1") == "value1"
