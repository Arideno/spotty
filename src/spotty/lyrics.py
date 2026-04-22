import re
import requests
from concurrent.futures import ThreadPoolExecutor

from .types import LyricLine

_HEADERS = {"User-Agent": "spotty-cli/0.0.5"}
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


def _try_lrclib(artist: str, title: str) -> tuple[list[LyricLine] | None, str | None]:
    try:
        r = requests.get(
            "https://lrclib.net/api/get",
            params={"artist_name": artist, "track_name": title},
            timeout=5,
            headers=_HEADERS,
        )
        if not r.ok or len(r.content) > _MAX_BYTES:
            return None, None
        data = r.json()
        synced_raw = data.get("syncedLyrics") or ""
        plain_raw = (data.get("plainLyrics") or "").strip()
        synced = (_parse_lrc(synced_raw) or None) if synced_raw else None
        return synced, plain_raw or None
    except Exception:
        return None, None


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


def fetch_all(artist: str, title: str) -> tuple[list[LyricLine] | None, str | None]:
    """Fetch lrclib and lyrics.ovh in parallel. Return (synced_lines, plain_text)."""
    clean = _clean_title(title)
    with ThreadPoolExecutor(max_workers=2) as executor:
        lrclib_fut = executor.submit(_try_lrclib, artist, clean)
        ovh_fut = executor.submit(_try_lyrics_ovh, artist, clean)
        synced, plain_lrclib = lrclib_fut.result()
        plain_ovh = ovh_fut.result()
    return synced, plain_lrclib or plain_ovh
