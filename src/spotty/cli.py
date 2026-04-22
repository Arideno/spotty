import time

import click

from . import config as cfg
from .display import clear_screen, make_live, print_lyrics, render_synced
from .lyrics import fetch_lyrics, fetch_synced_lyrics
from .nowplaying import get_now_playing
from .spotify import get_valid_token
from .types import LyricLine, Track

POLL_INTERVAL = 0.5
RENDER_INTERVAL = 0.1


@click.group(invoke_without_command=True)
@click.version_option("0.0.5", prog_name="spotty")
@click.option("--plain", is_flag=True, help="Show plain (non-synced) lyrics and exit.")
@click.option(
    "--offset",
    default=0,
    show_default=True,
    metavar="MS",
    help="Shift lyrics by MS milliseconds. Positive = later, negative = earlier.",
)
@click.pass_context
def main(ctx: click.Context, plain: bool, offset: int) -> None:
    """Display synchronized lyrics for the currently playing Spotify track.

    \b
    Run `spotty init` first to configure credentials.

    \b
    Config:   ~/.config/spotty/config.json
    Tokens:   ~/.config/spotty/tokens.json
    """
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
    lyrics = fetch_lyrics(track.artist, track.title) if track else None
    clear_screen()
    print_lyrics(track, lyrics)


def _run_synced(offset: int = 0) -> None:
    last_id: str | None = None
    synced_lines: list[LyricLine] | None = None
    plain_fallback: str | None = None
    current_track: Track | None = None

    fetched_progress_ms: int = 0
    fetched_at: float = 0.0
    last_poll: float = 0.0

    with make_live() as live:
        while True:
            try:
                now = time.time()

                if now - last_poll >= POLL_INTERVAL:
                    last_poll = now
                    token = get_valid_token()
                    track = get_now_playing(token)

                    if track is None:
                        from rich.text import Text
                        live.update(Text("Nothing currently playing on Spotify.", style="dim", justify="center"))
                        time.sleep(2)
                        last_id = None
                        fetched_at = 0.0
                        continue

                    fetched_progress_ms = track.progress_ms
                    fetched_at = time.time()
                    current_track = track

                    if track.id != last_id:
                        last_id = track.id
                        synced_lines = fetch_synced_lyrics(track.artist, track.title)
                        plain_fallback = None if synced_lines else fetch_lyrics(track.artist, track.title)

                if current_track is None:
                    time.sleep(RENDER_INTERVAL)
                    continue

                elapsed_since_fetch = int((time.time() - fetched_at) * 1000) if (fetched_at and current_track.is_playing) else 0
                effective_progress = fetched_progress_ms + elapsed_since_fetch + offset

                if synced_lines:
                    live.update(render_synced(current_track, synced_lines, effective_progress))
                else:
                    from rich.text import Text
                    t = Text(justify="center")
                    t.append(f"{current_track.artist}", style="cyan")
                    t.append(" — ")
                    t.append(f"{current_track.title}\n\n", style="bold white")
                    t.append(plain_fallback if plain_fallback else "No lyrics found.", style="white" if plain_fallback else "yellow")
                    live.update(t)

            except KeyboardInterrupt:
                break
            except Exception as e:
                from rich.text import Text
                live.update(Text(f"Error: {e}", style="red"))

            time.sleep(RENDER_INTERVAL)


if __name__ == "__main__":
    main()
