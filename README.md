# spotty

Synchronized lyrics in your terminal for the currently playing Spotify track.

- Line-by-line sync using LRC timestamps from [lrclib.net](https://lrclib.net)
- Falls back to plain lyrics via [lyrics.ovh](https://api.lyrics.ovh) if no synced lyrics found
- Smooth display — progress interpolated between API polls (no jumping)
- Auto-refreshes when track changes
- Handles instrumental sections, multi-artist tracks, featured artists

## Requirements

- Python 3.11+
- A [Spotify Developer App](https://developer.spotify.com/dashboard)

## Installation

```bash
pip install spotty-cli
```

Or from source:

```bash
git clone https://github.com/Arideno/spotty
cd spotty
pip install -e .
```

## Setup

### 1. Create a Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click **Create app**
3. Set **Redirect URI** to `http://127.0.0.1:8888/callback`
4. Copy your **Client ID**

### 2. Configure credentials

```bash
spotty init
```

You will be prompted for:

```
Spotify Client ID: <paste your client ID>
Redirect URI [http://127.0.0.1:8888/callback]: <Enter to keep default>
```

Config is saved to `~/.config/spotty/config.json`.

On first run after init, a browser window opens for Spotify authorization. Tokens are saved to `~/.config/spotty/tokens.json` and refreshed automatically.

## Usage

```bash
# Synchronized mode (default) — live updating display
spotty

# Plain lyrics — print and exit
spotty --plain

# Adjust timing if lyrics feel early or late
spotty --offset 300    # shift 300ms later
spotty --offset -200   # shift 200ms earlier

# Version
spotty --version

# Help
spotty --help
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--plain` | off | Show plain (non-synced) lyrics and exit |
| `--offset MS` | `0` | Shift lyrics by MS milliseconds. Positive = later, negative = earlier |
| `--version` | — | Show version and exit |
| `--help` | — | Show help and exit |

## Configuration

Credentials are stored in `~/.config/spotty/config.json` after running `spotty init`.

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `client_id` | Yes | — | Spotify app client ID |
| `client_secret` | Yes | — | Spotify app client secret |
| `redirect_uri` | No | `http://127.0.0.1:8888/callback` | OAuth callback URI — must match your Spotify app settings |

To update any value, re-run `spotty init`.

### File locations

| File | Purpose |
|------|---------|
| `~/.config/spotty/config.json` | Credentials |
| `~/.config/spotty/tokens.json` | OAuth tokens (auto-managed) |

Delete `tokens.json` to force re-authentication.

## How it works

1. **Auth** — OAuth2 PKCE flow, no client secret needed in the token exchange
2. **Now playing** — polls `GET /me/player/currently-playing` every 500ms
3. **Lyrics** — fetches LRC-timed lyrics from lrclib.net; falls back to lyrics.ovh for plain text
4. **Display** — interpolates playback position between polls using the local clock for smooth highlighting

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run directly
python -m spotty.cli
```

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make changes and add tests
4. Run `pytest` — all tests must pass
5. Open a pull request

## License

MIT — see [LICENSE](LICENSE)
