import unittest
from unittest.mock import MagicMock, patch

from spotty.lyrics import fetch_lyrics, fetch_synced_lyrics
from spotty.types import LyricLine


class TestFetchSyncedLyrics(unittest.TestCase):
    def _mock_response(self, status=200, json_data=None):
        mock = MagicMock()
        mock.ok = status == 200
        mock.status_code = status
        mock.json.return_value = json_data or {}
        return mock

    @patch("spotty.lyrics.requests.get")
    def test_parses_lrc_format(self, mock_get):
        mock_get.return_value = self._mock_response(json_data={
            "syncedLyrics": "[00:10.50] Hello world\n[00:15.00] Second line\n"
        })
        lines = fetch_synced_lyrics("Artist", "Song")
        self.assertIsNotNone(lines)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].time_ms, 10500)
        self.assertEqual(lines[0].text, "Hello world")
        self.assertEqual(lines[1].time_ms, 15000)

    @patch("spotty.lyrics.requests.get")
    def test_returns_none_when_no_synced(self, mock_get):
        mock_get.return_value = self._mock_response(json_data={"plainLyrics": "plain only"})
        result = fetch_synced_lyrics("Artist", "Song")
        self.assertIsNone(result)

    @patch("spotty.lyrics.requests.get")
    def test_returns_none_on_404(self, mock_get):
        mock_get.return_value = self._mock_response(status=404)
        result = fetch_synced_lyrics("Artist", "Song")
        self.assertIsNone(result)

    @patch("spotty.lyrics.requests.get")
    def test_strips_featuring_from_title(self, mock_get):
        mock_get.return_value = self._mock_response(json_data={
            "syncedLyrics": "[00:01.00] Line"
        })
        fetch_synced_lyrics("Artist", "Song (feat. Someone)")
        call_params = mock_get.call_args[1]["params"]
        self.assertNotIn("feat", call_params["track_name"])


class TestFetchLyrics(unittest.TestCase):
    def _mock_response(self, status=200, json_data=None):
        mock = MagicMock()
        mock.ok = status == 200
        mock.status_code = status
        mock.json.return_value = json_data or {}
        return mock

    @patch("spotty.lyrics.requests.get")
    def test_returns_plain_lyrics_from_lrclib(self, mock_get):
        mock_get.return_value = self._mock_response(json_data={"plainLyrics": "Plain text lyrics"})
        result = fetch_lyrics("Artist", "Song")
        self.assertEqual(result, "Plain text lyrics")

    @patch("spotty.lyrics.requests.get")
    def test_falls_back_to_ovh(self, mock_get):
        fail = self._mock_response(status=404)
        success = self._mock_response(json_data={"lyrics": "OVH lyrics"})
        mock_get.side_effect = [fail, success]
        result = fetch_lyrics("Artist", "Song")
        self.assertEqual(result, "OVH lyrics")

    @patch("spotty.lyrics.requests.get")
    def test_returns_none_when_both_fail(self, mock_get):
        mock_get.return_value = self._mock_response(status=404)
        result = fetch_lyrics("Artist", "Song")
        self.assertIsNone(result)


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


if __name__ == "__main__":
    unittest.main()
