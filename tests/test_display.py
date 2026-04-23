import unittest

from spotty.display import render_synced
from spotty.types import LyricLine, Track


def _track():
    return Track(
        id="t1",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration_ms=200000,
        progress_ms=30000,
        is_playing=True,
    )


def _lines():
    return [LyricLine(time_ms=10000, text="hello"), LyricLine(time_ms=20000, text="world")]


class TestRenderSyncedOffset(unittest.TestCase):
    def test_zero_offset_shows_adjust_hint(self):
        result = render_synced(_track(), _lines(), 15000, live_offset=0)
        text = result.plain
        self.assertIn("[ / ]", text)

    def test_positive_offset_shows_value(self):
        result = render_synced(_track(), _lines(), 15000, live_offset=200)
        text = result.plain
        self.assertIn("+200ms", text)

    def test_negative_offset_shows_value(self):
        result = render_synced(_track(), _lines(), 15000, live_offset=-100)
        text = result.plain
        self.assertIn("-100ms", text)

    def test_default_live_offset_is_zero(self):
        result = render_synced(_track(), _lines(), 15000)
        text = result.plain
        self.assertIn("[ / ]", text)
        self.assertNotIn("ms", text.split("/ ")[1] if "/ " in text else text)


if __name__ == "__main__":
    unittest.main()
