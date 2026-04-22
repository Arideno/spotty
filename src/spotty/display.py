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


def _progress_bar(progress_ms: int, duration_ms: int, width: int) -> Text:
    cur_s = progress_ms // 1000
    dur_s = duration_ms // 1000 if duration_ms else 0
    cur_str = f"{cur_s // 60}:{cur_s % 60:02d}"
    dur_str = f"{dur_s // 60}:{dur_s % 60:02d}"
    time_str = f"  {cur_str} / {dur_str}"
    bar_width = max(width - len(time_str) - 4, 10)
    filled = int(bar_width * progress_ms / duration_ms) if duration_ms else 0
    filled = min(filled, bar_width)
    t = Text(justify="center")
    t.append("▓" * filled, style="green")
    t.append("░" * (bar_width - filled), style="dim")
    t.append(time_str, style="dim")
    t.append("\n")
    return t


def render_no_track() -> Text:
    return Text("Nothing currently playing on Spotify.", style="dim", justify="center")


def render_plain(track: Track, lyrics: str | None, source: str | None = None) -> Text:
    t = Text(justify="center")
    t.append(f"{track.artist}", style="cyan")
    t.append(" — ")
    t.append(f"{track.title}\n\n", style="bold white")
    if lyrics and source:
        max_lines = max((console.height or 24) - 5, 3)
        lyric_lines = lyrics.splitlines()
        if len(lyric_lines) > max_lines:
            lyrics = "\n".join(lyric_lines[:max_lines])
    t.append(lyrics if lyrics else "No lyrics found.", style="white" if lyrics else "yellow")
    if source:
        t.append(f"\n\n{source}", style="dim")
    return t


def render_error(e: Exception) -> Text:
    return Text(f"Error: {e}", style="red")


def render_loading(track: Track) -> Text:
    t = Text(justify="center")
    t.append(f"{track.artist}", style="cyan")
    t.append(" — ")
    t.append(f"{track.title}\n\n", style="bold white")
    t.append("Loading lyrics…", style="dim")
    return t


def render_synced(track: Track, lines: list[LyricLine], progress_ms: int, source: str | None = None) -> Text:
    t = Text(justify="center")
    t.append(f"{track.artist}", style="cyan")
    t.append(" — ")
    t.append(f"{track.title}", style="bold white")
    if not track.is_playing:
        t.append("  [paused]", style="dim")
    t.append("\n")
    t.append(f"{track.album}\n", style="dim")
    t.append_text(_progress_bar(progress_ms, track.duration_ms, console.width or 80))
    t.append("\n")

    if not lines:
        t.append("No synced lyrics found.", style="yellow")
        if source:
            t.append(f"\n\n{source}", style="dim")
        return t

    idx = _current_index(lines, progress_ms)
    height = (console.height or 24) - (4 if source else 0)
    start, end = _context_window(idx if idx >= 0 else 0, len(lines), height)

    if idx == -1:
        for line in lines[:end]:
            t.append(f"   {line.text}\n", style="white")
        if source:
            t.append(f"\n\n{source}", style="dim")
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

    if source:
        t.append(f"\n\n{source}", style="dim")

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
