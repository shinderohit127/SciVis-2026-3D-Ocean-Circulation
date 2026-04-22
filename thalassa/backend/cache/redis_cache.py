"""Content-addressed Redis cache for THALASSA query results.

Falls back to a no-op when Redis is unavailable so every endpoint still
works without a running Redis instance (e.g. during tests).

Cache key format: thalassa:{endpoint}:{sha256(params)[:16]}
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Optional

log = logging.getLogger(__name__)

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL: int = 3600  # seconds

try:
    import redis as _redis
    _client: Optional[Any] = _redis.Redis.from_url(
        REDIS_URL, decode_responses=True, socket_connect_timeout=2
    )
    _client.ping()
    _AVAILABLE = True
    log.info("Redis cache connected: %s", REDIS_URL)
except Exception as _exc:
    _client = None
    _AVAILABLE = False
    log.warning("Redis not available (%s) — cache disabled", _exc)


def is_available() -> bool:
    return _AVAILABLE


def _key(endpoint: str, params: dict) -> str:
    digest = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode()
    ).hexdigest()[:16]
    return f"thalassa:{endpoint}:{digest}"


def get(endpoint: str, params: dict) -> Optional[Any]:
    """Return cached value for this endpoint + params, or None on miss/error."""
    if not _AVAILABLE:
        return None
    try:
        raw = _client.get(_key(endpoint, params))
        if raw is not None:
            log.debug("Cache HIT %s", _key(endpoint, params))
            return json.loads(raw)
    except Exception as exc:
        log.warning("Cache get error: %s", exc)
    return None


def set(endpoint: str, params: dict, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store value under this endpoint + params key with the given TTL."""
    if not _AVAILABLE:
        return
    k = _key(endpoint, params)
    try:
        _client.setex(k, ttl, json.dumps(value))
        log.debug("Cache SET %s ttl=%ds", k, ttl)
    except Exception as exc:
        log.warning("Cache set error: %s", exc)
