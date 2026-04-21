import base64
import hashlib
import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from . import config as cfg
from .types import SpotifyToken

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = "user-read-currently-playing user-read-playback-state"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _code_verifier() -> str:
    return _b64url(secrets.token_bytes(48))


def _code_challenge(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode()).digest())


def _require(key: str) -> str:
    value = cfg.get(key)
    if not value:
        raise RuntimeError(
            f"Missing '{key}'. Run `spotty init` to configure your Spotify credentials."
        )
    return value


def _start_auth() -> SpotifyToken:
    client_id = _require("client_id")
    redirect_uri = _require("redirect_uri")
    verifier = _code_verifier()
    challenge = _code_challenge(verifier)
    state = secrets.token_hex(8)
    port = int(redirect_uri.split(":")[-1].split("/")[0])

    params = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
    })

    auth_code: list[str] = []
    server_error: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            if "code" in qs:
                auth_code.append(qs["code"][0])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>Authenticated! You can close this tab.</h2>")
            else:
                server_error.append(qs.get("error", ["unknown"])[0])
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<h2>Authentication failed.</h2>")

    httpd = HTTPServer(("localhost", port), Handler)
    httpd.timeout = 120

    webbrowser.open(f"{AUTH_URL}?{params}")
    print("Opening browser for Spotify login...")

    while not auth_code and not server_error:
        httpd.handle_request()

    httpd.server_close()

    if server_error:
        raise RuntimeError(f"Spotify auth error: {server_error[0]}")

    r = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code[0],
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": verifier,
    })
    r.raise_for_status()
    data = r.json()
    token = SpotifyToken(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=time.time() + data["expires_in"] - 60,
    )
    _save_tokens(token)
    return token


def _save_tokens(token: SpotifyToken) -> None:
    cfg.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg.TOKEN_FILE.write_text(json.dumps({
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "expires_at": token.expires_at,
    }))


def _load_tokens() -> SpotifyToken | None:
    if not cfg.TOKEN_FILE.exists():
        return None
    data = json.loads(cfg.TOKEN_FILE.read_text())
    return SpotifyToken(**data)


def _refresh_tokens(token: SpotifyToken) -> SpotifyToken:
    client_id = _require("client_id")
    r = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
        "client_id": client_id,
    })
    r.raise_for_status()
    data = r.json()
    updated = SpotifyToken(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", token.refresh_token),
        expires_at=time.time() + data["expires_in"] - 60,
    )
    _save_tokens(updated)
    return updated


def get_valid_token() -> SpotifyToken:
    token = _load_tokens()
    if token is None:
        return _start_auth()
    if time.time() >= token.expires_at:
        return _refresh_tokens(token)
    return token
