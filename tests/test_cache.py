import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from spotty import cache as cache_mod
from spotty.types import LyricLine


class _CacheTestBase(unittest.TestCase):
    def setUp(self):
        cache_mod._enabled = True
        self._tmpdir = tempfile.mkdtemp()
        self._db = Path(self._tmpdir) / "lyrics.db"
        self._patches = [
            patch.object(cache_mod, "_CACHE_DIR", Path(self._tmpdir)),
            patch.object(cache_mod, "_DB_PATH", self._db),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        cache_mod._enabled = True
        for p in self._patches:
            p.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestCacheHit(_CacheTestBase):

    def test_hit_returns_stored_data(self):
        lines = [LyricLine(time_ms=1000, text="hello"), LyricLine(time_ms=2000, text="world")]
        cache_mod.put("Artist", "Title", lines, "plain text", "lrclib")
        synced, plain, source = cache_mod.get("Artist", "Title")
        self.assertEqual(len(synced), 2)
        self.assertEqual(synced[0].time_ms, 1000)
        self.assertEqual(synced[1].text, "world")
        self.assertEqual(plain, "plain text")
        self.assertEqual(source, "lrclib")

    def test_miss_returns_nones(self):
        result = cache_mod.get("Nobody", "Notitle")
        self.assertEqual(result, (None, None, None))

    def test_expired_entry_returns_nones(self):
        lines = [LyricLine(time_ms=500, text="old")]
        cache_mod.put("Artist", "OldSong", lines, "old plain", "lrclib")
        # Backdate fetched_at beyond TTL
        conn = sqlite3.connect(self._db)
        conn.execute(
            "UPDATE lyrics SET fetched_at=? WHERE artist=? AND title=?",
            (int(time.time()) - cache_mod._TTL - 1, "Artist", "OldSong"),
        )
        conn.commit()
        conn.close()
        result = cache_mod.get("Artist", "OldSong")
        self.assertEqual(result, (None, None, None))

    def test_corrupted_db_returns_nones(self):
        with patch("spotty.cache.sqlite3.connect", side_effect=sqlite3.Error("boom")):
            result = cache_mod.get("Artist", "Song")
        self.assertEqual(result, (None, None, None))

    def test_corrupted_db_put_is_noop(self):
        with patch("spotty.cache.sqlite3.connect", side_effect=sqlite3.Error("boom")):
            # Must not raise
            cache_mod.put("Artist", "Song", None, "plain", "lrclib")

    def test_put_with_synced_none_roundtrips(self):
        cache_mod.put("Artist", "NoSync", None, "just plain", "lyrics.ovh")
        synced, plain, source = cache_mod.get("Artist", "NoSync")
        self.assertIsNone(synced)
        self.assertEqual(plain, "just plain")
        self.assertEqual(source, "lyrics.ovh")


class TestCacheDisable(_CacheTestBase):
    def test_disabled_get_returns_nones(self):
        cache_mod.put("Artist", "Song", None, "plain", "lrclib")
        cache_mod.disable()
        self.assertEqual(cache_mod.get("Artist", "Song"), (None, None, None))

    def test_disabled_put_does_not_write(self):
        cache_mod.disable()
        cache_mod.put("Artist", "Song", None, "plain", "lrclib")
        cache_mod._enabled = True
        self.assertEqual(cache_mod.get("Artist", "Song"), (None, None, None))


if __name__ == "__main__":
    unittest.main()
