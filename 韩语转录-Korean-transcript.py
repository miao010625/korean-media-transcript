#!/usr/bin/env python3
"""Download permitted media and prepare Korean transcripts. Author: miao010625."""

import argparse
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


OUTPUTS = ("全文-Transcript.txt", "时间戳-Timestamped.md", "字幕-Subtitles.srt")
TIMING = re.compile(
    r"^(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})(?:\s+.*)?$"
)


class TranscriptError(Exception):
    """An actionable input or tool failure, safe to show without process output."""


def milliseconds(parts):
    hours, minutes, seconds, fraction = map(int, parts)
    if minutes >= 60 or seconds >= 60:
        raise TranscriptError("Invalid timestamp: minutes and seconds must be below 60")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + fraction


def read_captions(path):
    """Read UTF-8 SRT without discarding intentional repetitions or overlaps."""
    contents = Path(path).read_text(encoding="utf-8-sig")
    cues = []
    for block in re.split(r"\n[ \t]*\n", contents.strip()):
        if not block.strip():
            continue
        lines = block.splitlines()
        if lines[0].strip().isdigit():
            lines = lines[1:]
        match = TIMING.fullmatch(lines[0].strip()) if lines else None
        if not match:
            raise TranscriptError("Invalid subtitle cue: expected an SRT timestamp")
        start = milliseconds(match.groups()[:4])
        end = milliseconds(match.groups()[4:])
        if end <= start:
            raise TranscriptError("Subtitle end must be after start")
        if cues and start < cues[-1][0]:
            raise TranscriptError("Subtitle cues must be in chronological order")
        text = html.unescape(re.sub(r"</?[^>]+>", "", " ".join(lines[1:])))
        text = " ".join(text.split())
        if text:
            cues.append((start, end, text))
    if not cues:
        raise TranscriptError(
            "No usable subtitle cues; recognition may contain no speech"
        )
    return cues


def timestamp(value, separator=","):
    seconds, fraction = divmod(value, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{fraction:03}"


def export_captions(cues, directory):
    """Create three UTF-8 outputs and refuse to overwrite existing results."""
    directory = Path(directory)
    if any((directory / name).exists() for name in OUTPUTS):
        raise TranscriptError("Output already exists; choose a new --out directory")
    directory.mkdir(parents=True, exist_ok=True)
    documents = (
        "\n\n".join(text for _, _, text in cues) + "\n",
        "\n\n".join(f"`{timestamp(start, '.')}` {text}" for start, _, text in cues)
        + "\n",
        "\n\n".join(
            f"{number}\n{timestamp(start)} --> {timestamp(end)}\n{text}"
            for number, (start, end, text) in enumerate(cues, 1)
        )
        + "\n",
    )
    created = []
    try:
        for name, contents in zip(OUTPUTS, documents):
            path = directory / name
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                created.append(path)
                stream.write(contents)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def tool_path(name, explicit=None):
    candidate = explicit or shutil.which(name)
    if not candidate or not Path(candidate).is_file():
        option = "whisper" if name == "whisper-cli" else name
        raise TranscriptError(f"Missing {name}; install it or supply --{option}")
    return str(Path(candidate).resolve())


def run_tool(command, label, cwd=None):
    """Capture external output: errors can contain signed URLs or private paths."""
    try:
        result = subprocess.run(
            list(map(str, command)),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            cwd=cwd,
        )
    except OSError:
        raise TranscriptError(
            f"Could not start {label}; check the executable"
        ) from None
    if result.returncode:
        raise TranscriptError(f"{label} failed (exit {result.returncode})")
    return result.stdout


def download_media(url, directory):
    """Download one item through yt-dlp; no cookie export or playlists."""
    run_tool(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "--ignore-config",
            "--no-playlist",
            "--no-progress",
            "--restrict-filenames",
            "--concurrent-fragments",
            "8",
            "--retries",
            "5",
            "--abort-on-unavailable-fragments",
            "-f",
            "bestaudio/best",
            "-o",
            directory / "下载-Source.%(ext)s",
            url,
        ],
        "Media download",
    )
    files = [
        path
        for path in directory.glob("下载-Source.*")
        if path.suffix not in (".part", ".ytdl")
    ]
    if len(files) != 1:
        raise TranscriptError("Download did not produce exactly one media file")
    return files[0]


def recognize(media, directory, args):
    ffmpeg = tool_path("ffmpeg", args.ffmpeg)
    ffprobe = tool_path("ffprobe", args.ffprobe)
    whisper = tool_path("whisper-cli", args.whisper)
    if not args.model or not Path(args.model).is_file():
        raise TranscriptError("Supply an existing whisper.cpp model using --model")
    data = run_tool(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            media,
        ],
        "Media probe",
    )
    try:
        duration = float(json.loads(data)["format"]["duration"])
    except (ValueError, KeyError, TypeError):
        raise TranscriptError("Media duration could not be determined") from None
    if not math.isfinite(duration) or duration <= 0:
        raise TranscriptError("Media must have a positive finite duration")
    run_tool(
        [ffmpeg, "-nostdin", "-v", "error", "-i", media, "-f", "null", "-"],
        "Media integrity check",
    )
    # Relative ASCII names also work with older Windows whisper.cpp builds.
    audio = directory / "audio.wav"
    run_tool(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-v",
            "error",
            "-i",
            media,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            audio,
        ],
        "Audio conversion",
    )
    prefix = directory / "recognition"
    command = [
        whisper,
        "-m",
        Path(args.model).resolve(),
        "-f",
        audio.name,
        "-l",
        args.lang,
        "-osrt",
        "-of",
        prefix.name,
    ]
    if args.hint:
        command.extend(["--prompt", args.hint])
    run_tool(command, "Speech recognition", cwd=directory)
    captions = prefix.with_suffix(".srt")
    if not captions.is_file():
        raise TranscriptError("Speech recognition did not produce subtitles")
    return read_captions(captions)


def process(args):
    try:
        source = urlsplit(args.source)
    except ValueError:
        raise TranscriptError("Invalid source URL") from None
    remote = source.scheme.lower() in ("http", "https")
    if remote and (not source.hostname or source.username or source.password):
        raise TranscriptError("Use an HTTP(S) URL without embedded credentials")
    media = None if remote else Path(args.source).expanduser().resolve()
    if media is not None and not media.is_file():
        raise TranscriptError("Source file does not exist")
    if any((args.out / name).exists() for name in OUTPUTS):
        raise TranscriptError("Output already exists; choose a new --out directory")
    if media is not None and media.suffix.lower() == ".srt":
        cues = read_captions(media)
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        if args.keep_media:
            work = Path(tempfile.mkdtemp(prefix="保留媒体-Kept-media-", dir=args.out))
            if remote:
                media = download_media(args.source, work)
            cues = recognize(media, work, args)
        else:
            with tempfile.TemporaryDirectory(prefix="临时-Work-", dir=args.out) as folder:
                work = Path(folder)
                if remote:
                    media = download_media(args.source, work)
                cues = recognize(media, work, args)
    export_captions(cues, args.out)
    return len(cues)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Korean Media Transcript — download, transcribe, and export. Author: miao010625"
    )
    parser.add_argument(
        "source", help="Authorized HTTP(S) media URL, local media, or UTF-8 SRT"
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="Directory for three text outputs"
    )
    parser.add_argument(
        "--lang", default="ko", help="Whisper language code (default: ko)"
    )
    parser.add_argument("--hint", default="", help="Short optional vocabulary prompt")
    parser.add_argument("--model", default=os.environ.get("WHISPER_MODEL"))
    parser.add_argument("--ffmpeg", help="Explicit FFmpeg executable path")
    parser.add_argument("--ffprobe", help="Explicit FFprobe executable path")
    parser.add_argument("--whisper", help="Explicit whisper-cli executable path")
    parser.add_argument(
        "--keep-media",
        action="store_true",
        help="Keep downloaded and intermediate media",
    )
    args = parser.parse_args(argv)
    try:
        count = process(args)
    except TranscriptError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except UnicodeError:
        print("Error: subtitles must be valid UTF-8", file=sys.stderr)
        return 2
    except OSError:
        print(
            "Error: could not read or write a file; check paths and permissions",
            file=sys.stderr,
        )
        return 2
    print(f"Completed: {count} subtitle cues; saved TXT, timestamped Markdown, and SRT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
