"""Tests for RDSMemory implementation."""

import time

import pytest

pytest.importorskip("sqlalchemy")

from vertex_flow.memory import RDSMemory


class TestRDSMemory:
    """Basic test cases for RDSMemory."""

    def setup_method(self):
        self.memory = RDSMemory(db_url="sqlite:///:memory:", hist_maxlen=5)

    def test_seen_deduplication(self):
        user_id = "u"
        key = "k"
        assert self.memory.seen(user_id, key, ttl_sec=1) is False
        assert self.memory.seen(user_id, key, ttl_sec=1) is True
        time.sleep(1.1)
        assert self.memory.seen(user_id, key, ttl_sec=1) is False

    def test_append_history_maxlen(self):
        uid = "u"
        for i in range(10):
            self.memory.append_history(uid, "user", "text", {"text": str(i)}, maxlen=5)
        history = self.memory.recent_history(uid, n=10)
        assert len(history) == 5
        assert history[0]["content"]["text"] == "9"
        assert history[4]["content"]["text"] == "5"

    def test_ctx_operations(self):
        self.memory.ctx_set("u", "k", {"v": 1})
        assert self.memory.ctx_get("u", "k") == {"v": 1}
        self.memory.ctx_del("u", "k")
        assert self.memory.ctx_get("u", "k") is None

    def test_ctx_ttl(self):
        self.memory.ctx_set("u", "k", {"v": 1}, ttl_sec=1)
        time.sleep(1.1)
        assert self.memory.ctx_get("u", "k") is None

    def test_ephemeral_operations(self):
        self.memory.set_ephemeral("u", "k", 1, ttl_sec=1)
        assert self.memory.get_ephemeral("u", "k") == 1
        time.sleep(1.1)
        assert self.memory.get_ephemeral("u", "k") is None

    def test_del_ephemeral(self):
        self.memory.set_ephemeral("u", "k", 1)
        assert self.memory.get_ephemeral("u", "k") == 1
        self.memory.del_ephemeral("u", "k")
        assert self.memory.get_ephemeral("u", "k") is None

    def test_incr_rate_counter(self):
        uid = "u"
        bucket = "b"
        assert self.memory.incr_rate(uid, bucket, ttl_sec=1) == 1
        assert self.memory.incr_rate(uid, bucket, ttl_sec=1) == 2
        time.sleep(1.1)
        assert self.memory.incr_rate(uid, bucket, ttl_sec=1) == 1

    def test_mysql_driver_required(self):
        with pytest.raises(RuntimeError):
            RDSMemory(db_url="mysql://user:pass@localhost/test")
