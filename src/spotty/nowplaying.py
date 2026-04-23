from importlib.metadata import version

import requests

from .types import SpotifyToken, Track

NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
_UA = {"User-Agent": f"spotty-cli/{version('spotty-cli')}"}


def get_now_playing(token: SpotifyToken) -> Track | None:
    r = requests.get(
        NOW_PLAYING_URL,
        headers={**_UA, "Authorization": f"Bearer {token.access_token}"},
        timeout=15,
    )
    if r.status_code == 204 or r.status_code == 200 and not r.content:
        return None
    r.raise_for_status()
    data = r.json()
    item = data.get("item")
    if not item:
        return None
    artists = ", ".join(a["name"] for a in item.get("artists", []))
    return Track(
        id=item["id"],
        title=item["name"],
        artist=artists,
        album=item.get("album", {}).get("name", ""),
        is_playing=data.get("is_playing", False),
        progress_ms=data.get("progress_ms") or 0,
        duration_ms=item.get("duration_ms") or 0,
    )
