import bisect

from rich.console import Console
from rich.live import Live
from rich.text import Text

from .types import LyricLine, Track

console = Console()

def clear_screen() -> None:
    console.clear()


def _context_window(idx: int, total: int, term_height: int) -> tuple[int, int]:
    available = max(term_height - 3, 10)
    before = int(available * 0.4)
    after = available - before - 1
    start = max(0, idx - before)
    end = min(total, idx + after + 1)
    return start, end


def _current_index(lines: list[LyricLine], progress_ms: int) -> int:
    """Return index of the active lyric line, or -1 if before first line."""
    times = [l.time_ms for l in lines]
    return bisect.bisect_right(times, progress_ms) - 1


def render_synced(track: Track, lines: list[LyricLine], progress_ms: int) -> Text:
    t = Text(justify="center")
    t.append(f"{track.artist}", style="cyan")
    t.append(" — ")
    t.append(f"{track.title}", style="bold white")
    if not track.is_playing:
        t.append("  [paused]", style="dim")
    t.append("\n")
    t.append(f"{track.album}\n\n", style="dim")

    if not lines:
        t.append("No synced lyrics found.", style="yellow")
        return t

    idx = _current_index(lines, progress_ms)
    height = console.height or 24
    start, end = _context_window(idx if idx >= 0 else 0, len(lines), height)

    if idx == -1:
        for line in lines[:end]:
            t.append(f"   {line.text}\n", style="white")
        return t

    for i in range(start, end):
        line = lines[i]
        if i == idx:
            if track.is_playing:
                t.append(f"▶  {line.text}\n", style="bold yellow")
            else:
                t.append(f"⏸  {line.text}\n", style="dim")
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
