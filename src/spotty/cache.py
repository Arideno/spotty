import json
import sqlite3
import time
from pathlib import Path

from . import config as _spotty_config
from .types import LyricLine

_cache_dir_cfg = _spotty_config.get("cache_dir")
_CACHE_DIR = Path(_cache_dir_cfg) if _cache_dir_cfg else Path.home() / ".cache" / "spotty"
_DB_PATH = _CACHE_DIR / "lyrics.db"
_TTL = 2_592_000  # 30 days in seconds
_enabled = True


def disable() -> None:
    global _enabled
    _enabled = False


_CREATE = """
CREATE TABLE IF NOT EXISTS lyrics (
    artist     TEXT NOT NULL,
    title      TEXT NOT NULL,
    synced     TEXT,
    plain      TEXT,
    source     TEXT,
    fetched_at INTEGER NOT NULL,
    PRIMARY KEY (artist, title)
)
"""


def _connect() -> sqlite3.Connection:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(_CREATE)
    return conn


def get(artist: str, title: str) -> tuple[list[LyricLine] | None, str | None, str | None]:
    if not _enabled:
        return None, None, None
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT synced, plain, source, fetched_at FROM lyrics WHERE artist=? AND title=?",
                (artist, title),
            ).fetchone()
        if row is None:
            return None, None, None
        synced_json, plain, source, fetched_at = row
        if time.time() - fetched_at > _TTL:
            return None, None, None
        synced: list[LyricLine] | None = None
        if synced_json is not None:
            synced = [LyricLine(**d) for d in json.loads(synced_json)]
        return synced, plain, source
    except (sqlite3.Error, json.JSONDecodeError, ValueError, KeyError):
        return None, None, None


def put(
    artist: str,
    title: str,
    synced: list[LyricLine] | None,
    plain: str | None,
    source: str | None,
) -> None:
    if not _enabled:
        return
    try:
        synced_json = (
            json.dumps([{"time_ms": l.time_ms, "text": l.text} for l in synced])
            if synced is not None
            else None
        )
        with _connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO lyrics (artist, title, synced, plain, source, fetched_at) VALUES (?,?,?,?,?,?)",
                (artist, title, synced_json, plain, source, int(time.time())),
            )
    except Exception:
        pass
