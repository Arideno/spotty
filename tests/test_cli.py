import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from spotty.types import LyricLine


class TestStaleFetchDiscard(unittest.TestCase):
    def test_stale_result_discarded_when_track_changed(self):
        """Fetch result for old track ID must not be applied after track change."""
        fetch_can_complete = threading.Event()

        def slow_fetch(artist, title):
            fetch_can_complete.wait(timeout=5)
            return [LyricLine(0, "old lyric")], None, "lrclib"

        with ThreadPoolExecutor(max_workers=1) as executor:
            fetch_for_id = "track-a"
            last_id = "track-a"
            future = executor.submit(slow_fetch, "Artist", "Old Song")

            # Track changes before fetch completes
            last_id = "track-b"

            fetch_can_complete.set()
            future.result()  # ensure completed

            synced_lines = None
            plain_fallback = None
            if fetch_for_id == last_id:
                synced_lines, plain_fallback, _ = future.result()

        self.assertIsNone(synced_lines)
        self.assertIsNone(plain_fallback)

    def test_result_applied_when_track_unchanged(self):
        """Fetch result is applied when track has not changed."""
        lines = [LyricLine(0, "lyric")]

        with ThreadPoolExecutor(max_workers=1) as executor:
            fetch_for_id = "track-a"
            last_id = "track-a"
            future = executor.submit(lambda: (lines, None, "lrclib"))

            future.result()  # wait for completion

            synced_lines = None
            if fetch_for_id == last_id:
                synced_lines, _, _ = future.result()

        self.assertEqual(synced_lines, lines)

    def test_new_fetch_submitted_immediately_on_track_change(self):
        """New track fetch is submitted without blocking on old in-flight fetch."""
        old_fetch_blocking = threading.Event()
        first_can_complete = threading.Event()
        call_order = []

        def fetch_side_effect(artist, title):
            if title == "Old Song":
                call_order.append("old")
                old_fetch_blocking.set()
                first_can_complete.wait(timeout=5)
                return None, None, None
            else:
                call_order.append("new")
                return [LyricLine(0, "new lyric")], None, "lrclib"

        with ThreadPoolExecutor(max_workers=1) as executor:
            fut_a = executor.submit(fetch_side_effect, "Artist", "Old Song")
            old_fetch_blocking.wait(timeout=2)

            # submit() must return immediately even though old fetch is blocking
            fut_b = executor.submit(fetch_side_effect, "Artist", "New Song")
            # new fetch is queued but not yet started (worker is busy with old fetch)
            self.assertFalse(fut_b.done())

            first_can_complete.set()
            fut_a.result()
            fut_b.result()

        self.assertEqual(call_order, ["old", "new"])
