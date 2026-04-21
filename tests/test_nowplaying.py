import unittest
from unittest.mock import MagicMock, patch

from spotty.nowplaying import get_now_playing
from spotty.types import SpotifyToken


def _make_token():
    return SpotifyToken(access_token="tok", refresh_token="ref", expires_at=9999999999.0)


class TestGetNowPlaying(unittest.TestCase):
    def _mock_response(self, status=200, json_data=None, content=b"x"):
        mock = MagicMock()
        mock.status_code = status
        mock.content = content if status != 204 else b""
        mock.json.return_value = json_data or {}
        mock.raise_for_status = MagicMock()
        return mock

    @patch("spotty.nowplaying.requests.get")
    def test_returns_track_when_playing(self, mock_get):
        mock_get.return_value = self._mock_response(json_data={
            "is_playing": True,
            "item": {
                "id": "abc123",
                "name": "Test Song",
                "artists": [{"name": "Test Artist"}],
                "album": {"name": "Test Album"},
            }
        })
        track = get_now_playing(_make_token())
        self.assertIsNotNone(track)
        self.assertEqual(track.title, "Test Song")
        self.assertEqual(track.artist, "Test Artist")
        self.assertEqual(track.album, "Test Album")
        self.assertTrue(track.is_playing)
        self.assertEqual(track.progress_ms, 0)

    @patch("spotty.nowplaying.requests.get")
    def test_returns_none_on_204(self, mock_get):
        mock_get.return_value = self._mock_response(status=204)
        result = get_now_playing(_make_token())
        self.assertIsNone(result)

    @patch("spotty.nowplaying.requests.get")
    def test_returns_none_when_item_is_null(self, mock_get):
        mock_get.return_value = self._mock_response(json_data={"is_playing": False, "item": None})
        result = get_now_playing(_make_token())
        self.assertIsNone(result)

    @patch("spotty.nowplaying.requests.get")
    def test_multiple_artists_joined(self, mock_get):
        mock_get.return_value = self._mock_response(json_data={
            "is_playing": True,
            "item": {
                "id": "x",
                "name": "Collab",
                "artists": [{"name": "A"}, {"name": "B"}],
                "album": {"name": "EP"},
            }
        })
        track = get_now_playing(_make_token())
        self.assertEqual(track.artist, "A, B")


if __name__ == "__main__":
    unittest.main()
