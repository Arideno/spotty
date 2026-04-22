import re
import requests

from .types import LyricLine

_HEADERS = {"User-Agent": "spotty-cli/0.0.3"}
_MAX_BYTES = 2_000_000


def _clean_title(title: str) -> str:
    title = re.sub(r'\s*\(feat\..*?\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*feat\..*$', '', title, flags=re.IGNORECASE)
    return title.strip()


def _parse_lrc(lrc: str) -> list[LyricLine]:
    lines = []
    for match in re.finditer(r'\[(\d+):(\d+)\.(\d+)\](.*)', lrc):
        minutes, seconds, centis, text = match.groups()
        time_ms = (int(minutes) * 60 + int(seconds)) * \
            1000 + int(centis.ljust(3, '0')[:3])
        lines.append(LyricLine(time_ms=time_ms, text=text.strip()))
    return sorted(lines, key=lambda l: l.time_ms)


def _try_lrclib_synced(artist: str, title: str) -> list[LyricLine] | None:
    try:
        r = requests.get(
            "https://lrclib.net/api/get",
            params={"artist_name": artist, "track_name": title},
            timeout=5,
            headers=_HEADERS,
        )
        if not r.ok or len(r.content) > _MAX_BYTES:
            return None
        data = r.json()
        synced = data.get("syncedLyrics", "")
        if not synced:
            return None
        lines = _parse_lrc(synced)
        return lines or None
    except Exception:
        return None


def _try_lrclib_plain(artist: str, title: str) -> str | None:
    try:
        r = requests.get(
            "https://lrclib.net/api/get",
            params={"artist_name": artist, "track_name": title},
            timeout=5,
            headers=_HEADERS,
        )
        if not r.ok or len(r.content) > _MAX_BYTES:
            return None
        data = r.json()
        return (data.get("plainLyrics") or "").strip() or None
    except Exception:
        return None


def _try_lyrics_ovh(artist: str, title: str) -> str | None:
    try:
        url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(title)}"
        r = requests.get(url, timeout=5, headers=_HEADERS)
        if not r.ok or len(r.content) > _MAX_BYTES:
            return None
        data = r.json()
        lyrics = data.get("lyrics", "").strip()
        return lyrics or None
    except Exception:
        return None


def fetch_synced_lyrics(artist: str, title: str) -> list[LyricLine] | None:
    """Return timestamped LRC lines, or None if unavailable."""
    clean = _clean_title(title)
    return _try_lrclib_synced(artist, clean)


def fetch_lyrics(artist: str, title: str) -> str | None:
    """Return plain-text lyrics as fallback."""
    clean = _clean_title(title)
    return _try_lrclib_plain(artist, clean) or _try_lyrics_ovh(artist, clean)
