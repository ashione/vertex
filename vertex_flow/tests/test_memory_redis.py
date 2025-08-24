"""Tests for RedisMemory implementation."""

import time

from vertex_flow.memory import RedisMemory


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


class TestRedisMemory:
    """Basic test cases for RedisMemory."""

    def setup_method(self):
        self.redis = DummyRedis()
        self.memory = RedisMemory(client=self.redis, hist_maxlen=5)

    def test_seen_deduplication(self):
        user_id = "user1"
        key = "k"
        assert self.memory.seen(user_id, key, ttl_sec=1) is False
        assert self.memory.seen(user_id, key, ttl_sec=1) is True
        time.sleep(1.1)
        assert self.memory.seen(user_id, key, ttl_sec=1) is False

    def test_append_history_maxlen(self):
        user_id = "user1"
        for i in range(10):
            self.memory.append_history(user_id, "user", "text", {"text": str(i)}, maxlen=5)
        history = self.memory.recent_history(user_id, n=10)
        assert len(history) == 5
        assert history[0]["content"]["text"] == "9"
        assert history[4]["content"]["text"] == "5"

    def test_ctx_operations(self):
        self.memory.ctx_set("u", "k", {"v": 1})
        assert self.memory.ctx_get("u", "k") == {"v": 1}
        self.memory.ctx_del("u", "k")
        assert self.memory.ctx_get("u", "k") is None

    def test_ephemeral_operations(self):
        self.memory.set_ephemeral("u", "k", 1, ttl_sec=1)
        assert self.memory.get_ephemeral("u", "k") == 1
        time.sleep(1.1)
        assert self.memory.get_ephemeral("u", "k") is None

    def test_incr_rate_counter(self):
        user_id = "u"
        bucket = "b"
        assert self.memory.incr_rate(user_id, bucket, ttl_sec=1) == 1
        assert self.memory.incr_rate(user_id, bucket, ttl_sec=1) == 2
        time.sleep(1.1)
        assert self.memory.incr_rate(user_id, bucket, ttl_sec=1) == 1
