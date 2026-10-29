"""
youtube_transcript.py — Download and extract subtitles/transcript from a YouTube video.

Uses yt-dlp to fetch subtitles (manual or auto-generated), parses the VTT file
into clean plain text, and returns video metadata. Used by /lumi-youtube skill.

CLI:
    python youtube_transcript.py <url> [--lang LANG] [--output-dir DIR]

Options:
    --lang LANG          Subtitle language code (default: vi). Use comma-separated
                         list for fallback, e.g. "vi,en".
    --output-dir DIR     Directory for raw transcript text file (default: ./Documents/raw/download/youtube).
    --no-save            Skip saving raw text file; only print JSON to stdout.

Output (stdout, single JSON object on success):
    {
      "video_id": "dQw4w9WgXcQ",
      "title": "Video title",
      "channel": "Channel name",
      "upload_date": "2024-01-15",
      "duration_seconds": 1234,
      "language": "vi",
      "subtitle_type": "manual",
      "chapters": [{"title": "Intro", "start_seconds": 0}, ...],
      "raw_text": "full cleaned transcript text...",
      "raw_text_path": "Documents/raw/download/youtube/dQw4w9WgXcQ.txt"
    }

Exit codes:
    0  success
    2  user error (invalid URL, no subtitles available, yt-dlp not found)
    3  internal/transient error (network failure, yt-dlp crash, parse failure)

Requires: yt-dlp (must be on PATH or at /opt/homebrew/bin/yt-dlp).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Constants ──

YTDLP_PATHS = ("yt-dlp", "/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp")
REQUEST_TIMEOUT = 120  # seconds for yt-dlp network ops

# Regex patterns for VTT parsing
VTT_TIMESTAMP_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}"
)
VTT_HEADER_RE = re.compile(r"^(WEBVTT|Kind:|Language:)")
VTT_TAG_RE = re.compile(r"<[^>]+>")
VTT_CUE_NUMBER_RE = re.compile(r"^\d+$")

# YouTube URL patterns
YT_WATCH_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})"
)
YT_SHORTS_RE = re.compile(
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})"
)


# ── Helpers ──

def _err(msg: str) -> None:
    """Print error message to stderr."""
    print(msg, file=sys.stderr)


def _find_ytdlp() -> str:
    """Find yt-dlp binary on PATH. Raises ValueError if not found."""
    import shutil

    for candidate in YTDLP_PATHS:
        if shutil.which(candidate):
            return candidate
    raise ValueError(
        "yt-dlp not found. Install it with: brew install yt-dlp\n"
        "Or: pip install yt-dlp"
    )


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL. Raises ValueError on invalid input."""
    if not url or not url.strip():
        raise ValueError("URL is empty")

    url = url.strip()

    for pattern in (YT_WATCH_RE, YT_SHORTS_RE):
        m = pattern.search(url)
        if m:
            return m.group(1)

    # Also handle bare video IDs
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
        return url

    raise ValueError(
        f"Cannot extract video ID from URL: {url!r}\n"
        "Expected formats:\n"
        "  https://www.youtube.com/watch?v=VIDEO_ID\n"
        "  https://youtu.be/VIDEO_ID\n"
        "  https://www.youtube.com/shorts/VIDEO_ID"
    )


def _seconds_from_timestamp(ts: str) -> int:
    """Convert VTT timestamp 'HH:MM:SS.mmm' to integer seconds."""
    parts = ts.strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return int(hours * 3600 + minutes * 60 + seconds)


def _format_timestamp(total_seconds: int) -> str:
    """Format seconds as [HH:MM:SS] or [MM:SS]."""
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return f"[{h:02d}:{m:02d}:{s:02d}]"
    return f"[{m:02d}:{s:02d}]"


# ── Core Functions ──

def parse_vtt(vtt_path: Path) -> str:
    """Parse a VTT subtitle file into clean plain text.

    Strips timestamps, cue numbers, HTML tags, and WEBVTT headers.
    Deduplicates consecutive identical lines.
    Returns a single string with paragraphs separated by blank lines.
    """
    lines: list[str] = []
    prev_line = ""
    skip_next = False

    with open(vtt_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            # Skip empty lines
            if not line:
                if lines and lines[-1] != "":
                    lines.append("")
                continue

            # Skip VTT header metadata
            if VTT_HEADER_RE.match(line):
                continue

            # Skip cue numbers (pure digits)
            if VTT_CUE_NUMBER_RE.match(line):
                continue

            # Skip timestamp lines
            if VTT_TIMESTAMP_RE.match(line):
                continue

            # Strip HTML/XML tags (e.g., <c>, </c>, <00:00:01.000>)
            clean = VTT_TAG_RE.sub("", line).strip()

            if not clean:
                continue

            # Deduplicate consecutive identical lines (common in VTT)
            if clean == prev_line:
                continue
            prev_line = clean

            lines.append(clean)

    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def fetch_transcript(
    url: str,
    lang: str = "vi",
    output_dir: Path | None = None,
    save_raw: bool = True,
) -> dict:
    """Download YouTube subtitles and return metadata + clean text.

    Args:
        url: YouTube URL or video ID.
        lang: Subtitle language code(s), comma-separated for fallback.
        output_dir: Directory for saving raw text. Defaults to ./Documents/raw/download/youtube.
        save_raw: If True, write raw text to output_dir/<video_id>.txt.

    Returns:
        dict with keys: video_id, title, channel, upload_date, duration_seconds,
        language, subtitle_type, chapters, raw_text, raw_text_path.

    Raises:
        ValueError: Invalid URL, no subtitles, yt-dlp not found.
        RuntimeError: yt-dlp crashes, VTT parse failure.
        OSError: Network failure, timeout.
    """
    ytdlp = _find_ytdlp()
    video_id = _extract_video_id(url)

    if output_dir is None:
        output_dir = Path("Documents/raw/download/youtube")

    # ── Phase 1: Fetch video metadata ──
    try:
        meta_result = subprocess.run(
            [ytdlp, "--dump-json", "--no-playlist", f"https://youtu.be/{video_id}"],
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"yt-dlp timed out after {REQUEST_TIMEOUT}s while fetching metadata.\n"
            "Retry hint: check your internet connection and try again."
        )

    if meta_result.returncode != 0:
        stderr = meta_result.stderr.strip()
        # Detect common errors
        if "Video unavailable" in stderr or "Private video" in stderr:
            raise ValueError(f"Video unavailable or private: {video_id}")
        if "unable to download" in stderr.lower():
            raise OSError(f"Network error fetching video metadata: {stderr}")
        raise RuntimeError(f"yt-dlp metadata fetch failed: {stderr}")

    try:
        meta = json.loads(meta_result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse yt-dlp JSON output: {exc}")

    title = meta.get("title", "")
    channel = meta.get("uploader", meta.get("channel", ""))
    upload_date_raw = meta.get("upload_date", "")
    duration = int(meta.get("duration", 0) or 0)

    # Format upload date from YYYYMMDD to YYYY-MM-DD
    upload_date = ""
    if upload_date_raw and len(upload_date_raw) == 8:
        upload_date = f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:8]}"

    # ── Phase 2: Extract chapters (if available) ──
    chapters: list[dict] = []
    raw_chapters = meta.get("chapters", [])
    if raw_chapters:
        for ch in raw_chapters:
            chapters.append({
                "title": ch.get("title", ""),
                "start_seconds": int(ch.get("start_time", 0)),
                "end_seconds": int(ch.get("end_time", 0)),
            })

    # ── Phase 3: List available subtitles ──
    try:
        list_result = subprocess.run(
            [
                ytdlp,
                "--list-subs",
                "--no-playlist",
                f"https://youtu.be/{video_id}",
            ],
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"yt-dlp timed out while listing subtitles.\n"
            "Retry hint: check your internet connection."
        )

    if list_result.returncode != 0:
        raise RuntimeError(f"yt-dlp list-subs failed: {list_result.stderr.strip()}")

    # Parse available languages from --list-subs output
    output_text = list_result.stdout
    available_manual: list[str] = []
    available_auto: list[str] = []

    # Parse the subtitle listing to find available languages
    in_manual_section = False
    in_auto_section = False
    lang_re = re.compile(r"^\s*(\w+)(?:\s|$)")

    for line in output_text.splitlines():
        if "Available subtitles" in line:
            continue
        if "Language" in line and "formats" in line:
            continue
        if "Has manual" in line or "has_manual" in line:
            continue
        if "auto" in line.lower() and "automatic" in line.lower():
            in_manual_section = False
            in_auto_section = True
            continue
        m = lang_re.match(line)
        if m:
            lang_code = m.group(1)
            if lang_code in ("Available", "Language", "Has", "has"):
                continue
            if in_auto_section:
                available_auto.append(lang_code)
            else:
                available_manual.append(lang_code)

    # ── Phase 4: Determine best subtitle language ──
    requested_langs = [l.strip() for l in lang.split(",")]

    subtitle_type = "none"
    chosen_lang = ""
    subtitle_lang_arg = ""

    # Try manual first, then auto
    for rl in requested_langs:
        if rl in available_manual:
            subtitle_type = "manual"
            chosen_lang = rl
            break
        # Also try prefix match (e.g., "vi" matches "vi-VN")
        for al in available_manual:
            if al.startswith(rl):
                subtitle_type = "manual"
                chosen_lang = al
                break
        if subtitle_type == "manual":
            break

    if subtitle_type == "none":
        for rl in requested_langs:
            if rl in available_auto:
                subtitle_type = "auto"
                chosen_lang = rl
                break
            for al in available_auto:
                if al.startswith(rl):
                    subtitle_type = "auto"
                    chosen_lang = al
                    break
            if subtitle_type == "auto":
                break

    if subtitle_type == "none":
        raise ValueError(
            f"No subtitles found for language(s): {lang}\n"
            f"Available manual subtitles: {', '.join(available_manual) if available_manual else '(none)'}\n"
            f"Available auto-generated subtitles: {', '.join(available_auto) if available_auto else '(none)'}\n"
            f"Try a different --lang value."
        )

    subtitle_lang_arg = chosen_lang

    # ── Phase 5: Download subtitles ──
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        output_template = tmpdir_path / "%(id)s.%(ext)s"

        download_args = [
            ytdlp,
            "--skip-download",
            "--no-playlist",
            "--write-auto-subs" if subtitle_type == "auto" else "--write-subs",
            "--sub-format", "vtt",
            "--sub-langs", subtitle_lang_arg,
            "--convert-subs", "vtt",
            "-o", str(output_template),
            f"https://youtu.be/{video_id}",
        ]

        try:
            dl_result = subprocess.run(
                download_args,
                capture_output=True,
                text=True,
                timeout=REQUEST_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"yt-dlp timed out while downloading subtitles.\n"
                "Retry hint: check your internet connection."
            )

        if dl_result.returncode != 0:
            stderr = dl_result.stderr.strip()
            if "no subtitles" in stderr.lower() or "could not find" in stderr.lower():
                raise ValueError(
                    f"No subtitles available for language '{subtitle_lang_arg}'.\n"
                    f"Try --lang with one of: manual={available_manual}, auto={available_auto}"
                )
            raise RuntimeError(f"yt-dlp subtitle download failed: {stderr}")

        # Find the downloaded VTT file
        vtt_files = list(tmpdir_path.glob(f"{video_id}*.vtt"))
        if not vtt_files:
            # Also try recursive search
            vtt_files = list(tmpdir_path.rglob("*.vtt"))

        if not vtt_files:
            raise RuntimeError(
                "yt-dlp succeeded but no VTT file was produced.\n"
                f"Available manual: {available_manual}, auto: {available_auto}"
            )

        vtt_path = vtt_files[0]

        # ── Phase 6: Parse VTT to clean text ──
        try:
            raw_text = parse_vtt(vtt_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to parse VTT file: {exc}")

    if not raw_text.strip():
        raise RuntimeError("Parsed transcript is empty — VTT file may be malformed.")

    # ── Phase 7: Save raw text ──
    raw_text_path = ""
    if save_raw:
        output_dir.mkdir(parents=True, exist_ok=True)
        txt_path = output_dir / f"{video_id}.txt"
        # Atomic write
        fd, tmp_path = tempfile.mkstemp(dir=output_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(raw_text)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        os.replace(tmp_path, txt_path)
        raw_text_path = str(txt_path)

    return {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "upload_date": upload_date,
        "duration_seconds": duration,
        "language": subtitle_lang_arg,
        "subtitle_type": subtitle_type,
        "chapters": chapters,
        "raw_text": raw_text,
        "raw_text_path": raw_text_path,
    }


# ── CLI ──

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Download YouTube subtitles and extract clean transcript text.",
    )
    parser.add_argument(
        "url",
        help="YouTube URL or video ID",
    )
    parser.add_argument(
        "--lang",
        default="vi",
        help="Subtitle language code(s), comma-separated (default: vi). Example: 'vi,en'",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for raw transcript text file (default: ./Documents/raw/download/youtube)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip saving raw text file; only print JSON to stdout",
    )

    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        result = fetch_transcript(
            url=args.url,
            lang=args.lang,
            output_dir=output_dir,
            save_raw=not args.no_save,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    except ValueError as exc:
        _err(f"Error: {exc}")
        sys.exit(2)
    except (OSError, RuntimeError) as exc:
        _err(f"Error: {exc}")
        sys.exit(3)


if __name__ == "__main__":
    main()
