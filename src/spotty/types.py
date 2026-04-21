from dataclasses import dataclass


@dataclass
class Track:
    id: str
    title: str
    artist: str
    album: str
    is_playing: bool
    progress_ms: int = 0


@dataclass
class LyricLine:
    time_ms: int
    text: str


@dataclass
class SpotifyToken:
    access_token: str
    refresh_token: str
    expires_at: float
