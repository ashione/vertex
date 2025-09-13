"""Relational database backed memory store using SQLAlchemy."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, List, Optional
from urllib.parse import urlparse

from .memory import Memory

try:  # pragma: no cover - optional dependency
    import sqlalchemy as sa
except Exception:  # pragma: no cover
    sa = None


class RDSMemory(Memory):
    """Relational database backed memory store supporting SQLite and MySQL."""

    def __init__(
        self,
        db_url: Optional[str] = None,
        db_path: Optional[str] = None,
        hist_maxlen: int = 200,
    ) -> None:
        if db_url is None:
            # Prefer explicit db_path if provided, else environment override, else memory sqlite
            if db_path is not None:
                db_url = f"sqlite:///{db_path}"
            else:
                db_url = os.getenv("VF_RDS_URL", "sqlite:///:memory:")
        self._db_url = db_url
        self._hist_maxlen = hist_maxlen
        self._lock = threading.RLock()

        if sa is None:  # pragma: no cover - handled in tests
            raise RuntimeError("sqlalchemy is required for RDSMemory")

        parsed = urlparse(db_url)
        scheme = (parsed.scheme or "sqlite").lower()
        if scheme == "mysql":
            # Enforce explicit driver to avoid accidental real connections in tests
            raise RuntimeError("pymysql is required for MySQL support; use 'mysql+pymysql://...' URL")
        elif scheme.startswith("mysql+"):
            driver = scheme.split("+", 1)[1]
            # Only validate common sync drivers; async drivers are out of scope here
            if driver == "pymysql":  # pragma: no cover - optional dependency
                try:
                    import pymysql  # noqa: F401
                except Exception as exc:  # pragma: no cover
                    raise RuntimeError("pymysql is required for MySQL support") from exc
        elif not scheme.startswith("sqlite"):
            raise ValueError(f"Unsupported RDS scheme: {scheme}")

        self._engine = sa.create_engine(db_url, future=True)

        self._meta = sa.MetaData()
        self._dedup = sa.Table(
            "dedup",
            self._meta,
            sa.Column("user_id", sa.String(255), primary_key=True),
            sa.Column("key", sa.String(255), primary_key=True),
            sa.Column("expires_at", sa.Float, nullable=True),
        )
        self._history = sa.Table(
            "history",
            self._meta,
            # NOTE: SQLite 仅在 Integer 主键上支持自增，使用 BigInteger 会导致 NOT NULL 插入错误
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(255)),
            sa.Column("message", sa.Text),
            sa.Column("timestamp", sa.Float),
        )
        self._ctx = sa.Table(
            "ctx",
            self._meta,
            sa.Column("user_id", sa.String(255), primary_key=True),
            sa.Column("key", sa.String(255), primary_key=True),
            sa.Column("value", sa.Text),
            sa.Column("expires_at", sa.Float, nullable=True),
        )
        self._ephemeral = sa.Table(
            "ephemeral",
            self._meta,
            sa.Column("user_id", sa.String(255), primary_key=True),
            sa.Column("key", sa.String(255), primary_key=True),
            sa.Column("value", sa.Text),
            sa.Column("expires_at", sa.Float, nullable=True),
        )
        self._rate = sa.Table(
            "rate",
            self._meta,
            sa.Column("user_id", sa.String(255), primary_key=True),
            sa.Column("bucket", sa.String(255), primary_key=True),
            sa.Column("value", sa.Integer),
            sa.Column("expires_at", sa.Float, nullable=True),
        )
        self._meta.create_all(self._engine)

    def _is_expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.time() > expires_at

    # Deduplication -----------------------------------------------------------------
    def seen(self, user_id: str, key: str, ttl_sec: int = 3600) -> bool:
        with self._lock, self._engine.begin() as conn:
            stmt = sa.select(self._dedup.c.expires_at).where(self._dedup.c.user_id == user_id, self._dedup.c.key == key)
            row = conn.execute(stmt).fetchone()
            if row and not self._is_expired(row.expires_at):
                return True
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            conn.execute(sa.delete(self._dedup).where(self._dedup.c.user_id == user_id, self._dedup.c.key == key))
            conn.execute(self._dedup.insert().values(user_id=user_id, key=key, expires_at=expires_at))
            return False

    # History ----------------------------------------------------------------------
    def append_history(self, user_id: str, role: str, mtype: str, content: dict, maxlen: int = 200) -> None:
        with self._lock, self._engine.begin() as conn:
            ts = time.time()
            message = json.dumps({"role": role, "type": mtype, "content": content, "timestamp": ts})
            conn.execute(self._history.insert().values(user_id=user_id, message=message, timestamp=ts))
            sub = (
                sa.select(self._history.c.id)
                .where(self._history.c.user_id == user_id)
                .order_by(self._history.c.timestamp.desc())
                .limit(maxlen)
                .subquery()
            )
            conn.execute(
                sa.delete(self._history).where(
                    self._history.c.user_id == user_id,
                    self._history.c.id.notin_(sa.select(sub.c.id)),
                )
            )

    def recent_history(self, user_id: str, n: int = 20) -> List[dict]:
        with self._lock, self._engine.begin() as conn:
            stmt = (
                sa.select(self._history.c.message)
                .where(self._history.c.user_id == user_id)
                .order_by(self._history.c.timestamp.desc())
                .limit(n)
            )
            rows = conn.execute(stmt).fetchall()
            return [json.loads(row.message) for row in rows]

    # Context ----------------------------------------------------------------------
    def ctx_set(self, user_id: str, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        with self._lock, self._engine.begin() as conn:
            expires_at = time.time() + ttl_sec if ttl_sec is not None and ttl_sec > 0 else None
            conn.execute(sa.delete(self._ctx).where(self._ctx.c.user_id == user_id, self._ctx.c.key == key))
            conn.execute(
                self._ctx.insert().values(
                    user_id=user_id,
                    key=key,
                    value=json.dumps(value, ensure_ascii=False),
                    expires_at=expires_at,
                )
            )

    def ctx_get(self, user_id: str, key: str) -> Optional[Any]:
        with self._lock, self._engine.begin() as conn:
            stmt = sa.select(self._ctx.c.value, self._ctx.c.expires_at).where(
                self._ctx.c.user_id == user_id, self._ctx.c.key == key
            )
            row = conn.execute(stmt).fetchone()
            if not row:
                return None
            if self._is_expired(row.expires_at):
                conn.execute(sa.delete(self._ctx).where(self._ctx.c.user_id == user_id, self._ctx.c.key == key))
                return None
            return json.loads(row.value)

    def ctx_del(self, user_id: str, key: str) -> None:
        with self._lock, self._engine.begin() as conn:
            conn.execute(sa.delete(self._ctx).where(self._ctx.c.user_id == user_id, self._ctx.c.key == key))

    # Ephemeral --------------------------------------------------------------------
    def set_ephemeral(self, user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None:
        with self._lock, self._engine.begin() as conn:
            expires_at = time.time() + ttl_sec if ttl_sec > 0 else None
            conn.execute(
                sa.delete(self._ephemeral).where(
                    self._ephemeral.c.user_id == user_id,
                    self._ephemeral.c.key == key,
                )
            )
            conn.execute(
                self._ephemeral.insert().values(
                    user_id=user_id,
                    key=key,
                    value=json.dumps(value, ensure_ascii=False),
                    expires_at=expires_at,
                )
            )

    def get_ephemeral(self, user_id: str, key: str) -> Optional[Any]:
        with self._lock, self._engine.begin() as conn:
            stmt = sa.select(self._ephemeral.c.value, self._ephemeral.c.expires_at).where(
                self._ephemeral.c.user_id == user_id,
                self._ephemeral.c.key == key,
            )
            row = conn.execute(stmt).fetchone()
            if not row:
                return None
            if self._is_expired(row.expires_at):
                conn.execute(
                    sa.delete(self._ephemeral).where(
                        self._ephemeral.c.user_id == user_id,
                        self._ephemeral.c.key == key,
                    )
                )
                return None
            return json.loads(row.value)

    def del_ephemeral(self, user_id: str, key: str) -> None:
        with self._lock, self._engine.begin() as conn:
            conn.execute(
                sa.delete(self._ephemeral).where(
                    self._ephemeral.c.user_id == user_id,
                    self._ephemeral.c.key == key,
                )
            )

    # Rate limiting ----------------------------------------------------------------
    def incr_rate(self, user_id: str, bucket: str, ttl_sec: int = 60) -> int:
        with self._lock, self._engine.begin() as conn:
            stmt = sa.select(self._rate.c.value, self._rate.c.expires_at).where(
                self._rate.c.user_id == user_id, self._rate.c.bucket == bucket
            )
            row = conn.execute(stmt).fetchone()
            now = time.time()
            expires_at = now + ttl_sec if ttl_sec > 0 else None
            if not row or self._is_expired(row.expires_at):
                value = 1
            else:
                value = int(row.value) + 1
            conn.execute(sa.delete(self._rate).where(self._rate.c.user_id == user_id, self._rate.c.bucket == bucket))
            conn.execute(
                self._rate.insert().values(
                    user_id=user_id,
                    bucket=bucket,
                    value=value,
                    expires_at=expires_at,
                )
            )
            return int(value)
