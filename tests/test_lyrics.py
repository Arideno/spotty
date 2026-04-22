import unittest
from unittest.mock import MagicMock, patch

from spotty.lyrics import fetch_all
from spotty.types import LyricLine


def _url_mock(lrclib_data=None, lrclib_status=200, ovh_data=None, ovh_status=200):
    def side_effect(url, **kwargs):
        mock = MagicMock()
        mock.content = b"x"
        if "lrclib.net" in url:
            mock.ok = lrclib_status == 200
            mock.status_code = lrclib_status
            mock.json.return_value = lrclib_data or {}
        else:
            mock.ok = ovh_status == 200
            mock.status_code = ovh_status
            mock.json.return_value = ovh_data or {}
        return mock
    return side_effect


class TestFetchAll(unittest.TestCase):
    @patch("spotty.lyrics.requests.get")
    def test_returns_synced_lines(self, mock_get):
        mock_get.side_effect = _url_mock(
            lrclib_data={"syncedLyrics": "[00:10.50] Hello world\n[00:15.00] Second line\n"}
        )
        synced, plain = fetch_all("Artist", "Song")
        self.assertIsNotNone(synced)
        self.assertEqual(len(synced), 2)
        self.assertEqual(synced[0].time_ms, 10500)
        self.assertEqual(synced[0].text, "Hello world")
        self.assertEqual(synced[1].time_ms, 15000)

    @patch("spotty.lyrics.requests.get")
    def test_returns_plain_from_lrclib_when_no_synced(self, mock_get):
        mock_get.side_effect = _url_mock(
            lrclib_data={"plainLyrics": "Plain text lyrics"}
        )
        synced, plain = fetch_all("Artist", "Song")
        self.assertIsNone(synced)
        self.assertEqual(plain, "Plain text lyrics")

    @patch("spotty.lyrics.requests.get")
    def test_returns_plain_from_ovh_when_lrclib_fails(self, mock_get):
        mock_get.side_effect = _url_mock(
            lrclib_status=404,
            ovh_data={"lyrics": "OVH lyrics"},
        )
        synced, plain = fetch_all("Artist", "Song")
        self.assertIsNone(synced)
        self.assertEqual(plain, "OVH lyrics")

    @patch("spotty.lyrics.requests.get")
    def test_prefers_lrclib_plain_over_ovh(self, mock_get):
        mock_get.side_effect = _url_mock(
            lrclib_data={"plainLyrics": "lrclib plain"},
            ovh_data={"lyrics": "ovh plain"},
        )
        _, plain = fetch_all("Artist", "Song")
        self.assertEqual(plain, "lrclib plain")

    @patch("spotty.lyrics.requests.get")
    def test_returns_none_none_when_both_fail(self, mock_get):
        mock_get.side_effect = _url_mock(lrclib_status=404, ovh_status=404)
        synced, plain = fetch_all("Artist", "Song")
        self.assertIsNone(synced)
        self.assertIsNone(plain)

    @patch("spotty.lyrics.requests.get")
    def test_strips_featuring_from_title(self, mock_get):
        mock_get.side_effect = _url_mock(
            lrclib_data={"syncedLyrics": "[00:01.00] Line"}
        )
        fetch_all("Artist", "Song (feat. Someone)")
        lrclib_call = next(
            c for c in mock_get.call_args_list if "lrclib.net" in c[0][0]
        )
        self.assertNotIn("feat", lrclib_call[1]["params"]["track_name"])

    @patch("spotty.lyrics.requests.get")
    def test_single_lrclib_request(self, mock_get):
        mock_get.side_effect = _url_mock(
            lrclib_data={"syncedLyrics": "[00:01.00] Line", "plainLyrics": "plain"}
        )
        fetch_all("Artist", "Song")
        lrclib_calls = [c for c in mock_get.call_args_list if "lrclib.net" in c[0][0]]
        self.assertEqual(len(lrclib_calls), 1)


class TestCurrentIndex(unittest.TestCase):
    def test_current_index(self):
        from spotty.display import _current_index
        lines = [
            LyricLine(0, "intro"),
            LyricLine(5000, "verse"),
            LyricLine(10000, "chorus"),
        ]
        self.assertEqual(_current_index(lines, 0), 0)
        self.assertEqual(_current_index(lines, 4999), 0)

    def test_before_first_line_returns_minus_one(self):
        from spotty.display import _current_index
        lines = [LyricLine(5000, "verse"), LyricLine(10000, "chorus")]
        self.assertEqual(_current_index(lines, 0), -1)
        self.assertEqual(_current_index(lines, 4999), -1)
        self.assertEqual(_current_index(lines, 5000), 0)
        self.assertEqual(_current_index(lines, 9999), 0)
        self.assertEqual(_current_index(lines, 10000), 1)
        self.assertEqual(_current_index(lines, 99999), 1)


class TestContextWindow(unittest.TestCase):
    def test_centers_active_line_at_40_percent(self):
        from spotty.display import _context_window
        # term_height=40 → available=37, before=14, after=22
        start, end = _context_window(idx=20, total=50, term_height=40)
        self.assertEqual(start, 6)   # 20 - 14
        self.assertEqual(end, 43)    # 20 + 22 + 1

    def test_clamps_at_start(self):
        from spotty.display import _context_window
        start, end = _context_window(idx=2, total=50, term_height=40)
        self.assertEqual(start, 0)
        self.assertEqual(end, 25)    # 2 + 22 + 1

    def test_clamps_at_end(self):
        from spotty.display import _context_window
        start, end = _context_window(idx=48, total=50, term_height=40)
        self.assertEqual(start, 34)  # 48 - 14
        self.assertEqual(end, 50)

    def test_small_terminal_uses_minimum(self):
        from spotty.display import _context_window
        # term_height=5 → available forced to min 10, before=4, after=5
        start, end = _context_window(idx=20, total=50, term_height=5)
        self.assertEqual(start, 16)  # 20 - 4
        self.assertEqual(end, 26)    # 20 + 5 + 1


if __name__ == "__main__":
    unittest.main()
