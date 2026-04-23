import time
from concurrent.futures import Future, ThreadPoolExecutor

import click

from . import cache, config as cfg
from .display import clear_screen, make_live, print_lyrics, render_error, render_loading, render_no_track, render_plain, render_synced
from .lyrics import fetch_all
from .nowplaying import get_now_playing
from .spotify import get_valid_token
from .types import LyricLine, Track

POLL_INTERVAL = 0.5
RENDER_INTERVAL = 0.1


@click.group(invoke_without_command=True)
@click.version_option(package_name="spotty-cli", prog_name="spotty")
@click.option("--plain", is_flag=True, help="Show plain (non-synced) lyrics and exit.")
@click.option(
    "--offset",
    default=0,
    show_default=True,
    metavar="MS",
    help="Shift lyrics by MS milliseconds. Positive = later, negative = earlier.",
)
@click.option("--no-cache", is_flag=True, help="Disable lyrics cache for this run.")
@click.pass_context
def main(ctx: click.Context, plain: bool, offset: int, no_cache: bool) -> None:
    """Display synchronized lyrics for the currently playing Spotify track.

    \b
    Run `spotty init` first to configure credentials.

    \b
    Config:   ~/.config/spotty/config.json
    Tokens:   ~/.config/spotty/tokens.json
    """
    if no_cache or cfg.get("cache_enabled") is False:
        cache.disable()

    if ctx.invoked_subcommand is None:
        if plain:
            _run_once()
        else:
            _run_synced(offset)


@main.command()
def init() -> None:
    """Configure Spotify credentials interactively.

    \b
    You need a Spotify Developer app:
      1. Go to https://developer.spotify.com/dashboard
      2. Create an app
      3. Add http://127.0.0.1:8888/callback as a Redirect URI
      4. Copy Client ID
    """
    click.echo("Spotify Lyrics — setup\n")

    existing = cfg.load_config()

    client_id = click.prompt(
        "Spotify Client ID",
        default=existing.get("client_id", ""),
    )
    redirect_uri = click.prompt(
        "Redirect URI",
        default=existing.get("redirect_uri", "http://127.0.0.1:8888/callback"),
    )

    cfg.save_config({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    })

    click.echo(f"\nConfig saved to {cfg.CONFIG_FILE}")
    click.echo("Run `spotty` to start.")


def _run_once() -> None:
    token = get_valid_token()
    track = get_now_playing(token)
    _, lyrics, _ = fetch_all(track.artist, track.title) if track else (None, None, None)
    clear_screen()
    print_lyrics(track, lyrics)


def _run_synced(offset: int = 0) -> None:
    last_id: str | None = None
    synced_lines: list[LyricLine] | None = None
    plain_fallback: str | None = None
    current_track: Track | None = None
    lyrics_source: str | None = None
    fetch_future: Future | None = None
    fetch_for_id: str | None = None

    fetched_progress_ms: int = 0
    fetched_at: float = 0.0
    last_poll: float = 0.0

    with make_live() as live, ThreadPoolExecutor(max_workers=1) as executor:
        while True:
            try:
                now = time.time()

                if now - last_poll >= POLL_INTERVAL:
                    last_poll = now
                    token = get_valid_token()
                    track = get_now_playing(token)

                    if track is None:
                        live.update(render_no_track())
                        time.sleep(2)
                        last_id = None
                        fetched_at = 0.0
                        fetch_future = None
                        fetch_for_id = None
                        continue

                    fetched_progress_ms = track.progress_ms
                    fetched_at = time.time()
                    current_track = track

                    if track.id != last_id:
                        last_id = track.id
                        synced_lines = None
                        plain_fallback = None
                        lyrics_source = None
                        fetch_for_id = track.id
                        fetch_future = executor.submit(fetch_all, track.artist, track.title)

                if fetch_future is not None and fetch_future.done():
                    if fetch_for_id == last_id:
                        synced_lines, plain_fallback, lyrics_source = fetch_future.result()
                    fetch_future = None

                if current_track is None:
                    time.sleep(RENDER_INTERVAL)
                    continue

                elapsed_since_fetch = int((time.time() - fetched_at) * 1000) if (fetched_at and current_track.is_playing) else 0
                effective_progress = fetched_progress_ms + elapsed_since_fetch + offset

                if synced_lines:
                    live.update(render_synced(current_track, synced_lines, effective_progress, lyrics_source))
                elif fetch_future is not None:
                    live.update(render_loading(current_track))
                else:
                    live.update(render_plain(current_track, plain_fallback, lyrics_source))

            except KeyboardInterrupt:
                break
            except Exception as e:
                live.update(render_error(e))

            time.sleep(RENDER_INTERVAL)


if __name__ == "__main__":
    main()
