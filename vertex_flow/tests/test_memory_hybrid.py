"""Tests for HybridMemory combining Redis and RDS."""

import time

import pytest

pytest.importorskip("sqlalchemy")

from vertex_flow.memory import HybridMemory


class DummyPipeline:
    def __init__(self, client):
        self._client = client
        self._commands = []

    def lpush(self, *args):
        self._commands.append(("lpush", args))
        return self

    def ltrim(self, *args):
        self._commands.append(("ltrim", args))
        return self

    def incr(self, *args):
        self._commands.append(("incr", args))
        return self

    def expire(self, *args):
        self._commands.append(("expire", args))
        return self

    def execute(self):
        results = []
        for cmd, args in self._commands:
            results.append(getattr(self._client, cmd)(*args))
        self._commands.clear()
        return results


class DummyRedis:
    def __init__(self):
        self._store = {}
        self._lists = {}

    def _check_expired(self, key):
        if key in self._store:
            value, exp = self._store[key]
            if exp is not None and time.time() > exp:
                del self._store[key]

    def set(self, key, value, nx=False, ex=None):
        self._check_expired(key)
        if nx and key in self._store:
            return None
        expires_at = time.time() + ex if ex else None
        self._store[key] = (value, expires_at)
        return True

    def get(self, key):
        self._check_expired(key)
        if key not in self._store:
            return None
        return self._store[key][0]

    def delete(self, key):
        self._store.pop(key, None)

    def lpush(self, key, value):
        self._lists.setdefault(key, [])
        self._lists[key].insert(0, value)

    def ltrim(self, key, start, end):
        self._lists.setdefault(key, [])
        self._lists[key] = self._lists[key][start : end + 1]

    def lrange(self, key, start, end):
        lst = self._lists.get(key, [])
        if end == -1:
            end = len(lst) - 1
        return lst[start : end + 1]

    def pipeline(self):
        return DummyPipeline(self)

    def incr(self, key):
        self._check_expired(key)
        value = int(self._store.get(key, ("0", None))[0]) + 1
        _, exp = self._store.get(key, (None, None))
        self._store[key] = (str(value), exp)
        return value

    def expire(self, key, ttl):
        if key in self._store:
            value, _ = self._store[key]
            self._store[key] = (value, time.time() + ttl)
            return True
        return False


class TestHybridMemory:
    def setup_method(self):
        self.redis = DummyRedis()
        self.memory = HybridMemory(redis_client=self.redis, db_url="sqlite:///:memory:", hist_maxlen=5)

    def test_seen_deduplication_eventual(self):
        assert self.memory.seen("u", "k", ttl_sec=1) is False
        # simulate redis loss
        self.redis._store.clear()
        assert self.memory.seen("u", "k", ttl_sec=1) is True

    def test_history_fallback(self):
        uid = "u"
        for i in range(3):
            self.memory.append_history(uid, "user", "text", {"text": str(i)}, maxlen=5)
        # drop redis history
        self.redis._lists.clear()
        history = self.memory.recent_history(uid, n=5)
        assert len(history) == 3
        # redis should be repopulated
        assert self.redis.lrange(self.memory._redis._hist_key(uid), 0, -1)

    def test_ctx_eventual(self):
        self.memory.ctx_set("u", "k", {"v": 1})
        self.redis._store.clear()
        assert self.memory.ctx_get("u", "k") == {"v": 1}

    def test_ctx_delete_sync(self):
        self.memory.ctx_set("u", "k", {"v": 1})
        self.memory.ctx_del("u", "k")
        assert self.memory.ctx_get("u", "k") is None
        assert self.redis.get(self.memory._redis._ctx_key("u", "k")) is None

    def test_ephemeral_operations(self):
        self.memory.set_ephemeral("u", "k", 1, ttl_sec=1)
        self.redis._store.clear()
        assert self.memory.get_ephemeral("u", "k") == 1
        time.sleep(1.1)
        assert self.memory.get_ephemeral("u", "k") is None

    def test_del_ephemeral_sync(self):
        self.memory.set_ephemeral("u", "k", 1, ttl_sec=10)
        self.memory.del_ephemeral("u", "k")
        assert self.memory.get_ephemeral("u", "k") is None
        assert self.redis.get(self.memory._redis._ephemeral_key("u", "k")) is None

    def test_rate_counter_eventual(self):
        assert self.memory.incr_rate("u", "b", ttl_sec=10) == 1
        self.redis._store.clear()
        assert self.memory.incr_rate("u", "b", ttl_sec=10) == 2
