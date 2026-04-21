import bisect

from rich.console import Console
from rich.live import Live
from rich.text import Text

from .types import LyricLine, Track

console = Console()

CONTEXT_BEFORE = 4
CONTEXT_AFTER = 12


def clear_screen() -> None:
    console.clear()


def _current_index(lines: list[LyricLine], progress_ms: int) -> int:
    """Return index of the active lyric line, or -1 if before first line."""
    times = [l.time_ms for l in lines]
    return bisect.bisect_right(times, progress_ms) - 1


def render_synced(track: Track, lines: list[LyricLine], progress_ms: int) -> Text:
    t = Text()
    t.append(f"{track.artist}", style="cyan")
    t.append(" — ")
    t.append(f"{track.title}\n", style="bold white")
    t.append(f"{track.album}\n\n", style="dim")

    if not lines:
        t.append("No synced lyrics found.", style="yellow")
        return t

    idx = _current_index(lines, progress_ms)
    start = max(0, idx - CONTEXT_BEFORE)
    end = min(len(lines), idx + CONTEXT_AFTER + 1)

    if idx == -1:
        end = min(len(lines), CONTEXT_AFTER + 1)
        for line in lines[:end]:
            t.append(f"   {line.text}\n", style="white")
        return t

    for i in range(start, end):
        line = lines[i]
        if i == idx:
            t.append(f"▶  {line.text}\n", style="bold yellow")
        elif i < idx:
            t.append(f"   {line.text}\n", style="dim")
        else:
            t.append(f"   {line.text}\n", style="white")

    return t


def print_lyrics(track: Track | None, lyrics: str | None) -> None:
    if not track:
        console.print("[dim]Nothing currently playing on Spotify.[/dim]")
        return

    console.print(Text.assemble(
        (track.artist, "cyan"),
        " — ",
        (track.title, "bold white"),
    ))
    console.print(f"[dim]{track.album}[/dim]")
    console.print()

    if not lyrics:
        console.print("[yellow]No lyrics found.[/yellow]")
        return

    lines = lyrics.splitlines()
    term_height = console.height or 40
    page_size = max(term_height - 6, 20)

    if len(lines) <= page_size:
        console.print(lyrics)
        return

    offset = 0
    while offset < len(lines):
        page = "\n".join(lines[offset:offset + page_size])
        console.print(page)
        offset += page_size
        if offset < len(lines):
            try:
                input("[dim]-- Press Enter for more --[/dim]")
            except (EOFError, KeyboardInterrupt):
                break


def make_live() -> Live:
    return Live(console=console, refresh_per_second=4, screen=True)
