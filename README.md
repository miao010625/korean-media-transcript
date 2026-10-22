# Korean Media Transcript · 韩语影音转录

**Author / 作者：[miao010625](https://github.com/miao010625)**

A small command-line tool for downloading permitted media, transcribing speech locally, and exporting Korean text and subtitles. Korean is the default language; other whisper.cpp language codes are supported.

面向韩语学习和资料整理的命令行工具：输入可下载的视频链接、本地音视频或已有 SRT，输出全文、毫秒级时间戳文本和标准 SRT。识别在本机完成，不需要云端转录 API。

## Features

- Download one media item with yt-dlp; playlists and user-level downloader configuration are disabled.
- Check media duration and decoding before converting to 16 kHz mono audio.
- Run whisper.cpp with an explicit model and optional vocabulary hint.
- Convert UTF-8 SRT directly without installing media tools.
- Preserve Korean characters, millisecond timestamps, and intentional repetitions.
- Refuse to overwrite existing deliverables. Temporary downloads are removed after processing, including on failure; original local files are preserved.
- No bundled third-party source, models, binaries, browser cookies, or recordings.

## Requirements

Python **3.10+**. SRT conversion uses only Python's standard library.

For URL input, install the download dependency:

```sh
python -m pip install -r 运行依赖-Requirements.txt
```

For speech recognition, separately install:

- [FFmpeg and FFprobe](https://ffmpeg.org/download.html)
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp), including `whisper-cli`
- A multilingual whisper.cpp GGML model supporting Korean, such as `ggml-small.bin` or a compatible quantized model. Obtain models from the whisper.cpp project's documented sources.

Executables can be on `PATH` or supplied using `--ffmpeg`, `--ffprobe`, and `--whisper`. Supply the model with `--model` or the `WHISPER_MODEL` environment variable. Hardware, model choice, and audio quality affect speed and accuracy.

## Quick start

Clone this repository, then run commands from its directory:

```sh
git clone https://github.com/miao010625/korean-media-transcript.git
cd korean-media-transcript
```

Existing subtitles — no media dependencies:

```sh
python 韩语转录-Korean-transcript.py examples/示例字幕-Example-subtitles.srt --out results/example
```

Local audio or video:

```sh
python 韩语转录-Korean-transcript.py recording.mp4 --out results/lesson --model /path/to/ggml-small.bin
```

Download and transcribe a permitted URL (replace the example):

```sh
python 韩语转录-Korean-transcript.py "https://example.org/your-video.mp4" --out results/video --model /path/to/model.bin
```

Windows PowerShell example, with explicit executable paths:

```powershell
python .\韩语转录-Korean-transcript.py .\recording.mp4 `
  --out .\results\lesson `
  --model "C:\Models\ggml-small.bin" `
  --ffmpeg "C:\Tools\ffmpeg.exe" `
  --ffprobe "C:\Tools\ffprobe.exe" `
  --whisper "C:\Tools\whisper-cli.exe" `
  --hint "한국어 건축 환경"
```

Use `--lang en` for English, `--lang auto` for automatic language detection, or another whisper.cpp language code. `--keep-media` retains the downloaded file and recognition intermediates in a clearly named subdirectory of the output directory; it does not duplicate local originals. `--help` lists all options.

## Outputs

| File | Contents |
| --- | --- |
| `全文-Transcript.txt` | Cue text in chronological order, separated by blank lines |
| `时间戳-Timestamped.md` | Text with `HH:MM:SS.mmm` start times |
| `字幕-Subtitles.srt` | Numbered subtitle cues with original millisecond timing |

All outputs are UTF-8. Text is not translated or automatically rewritten. Repeated speech is retained. Existing SRT tags are removed and HTML entities are decoded. Overlapping cues are accepted when their start times are ordered. Choose a new output directory to process a source again.

## Limits and privacy

Process only media you have permission to download and transcribe. This tool does not log into course platforms, export browser cookies, or bypass DRM/access restrictions. A supported URL must be directly usable by yt-dlp without additional authentication. For authenticated material, obtain an authorized local copy separately.

Speech recognition can mishear names and technical vocabulary or hallucinate speech in music/silence. Review transcripts before using them as quotations. `--hint` provides context, not a correctness guarantee. Error messages show the failed processing stage and exit code while suppressing external process output, which can contain private URLs. No full private URLs or downloader metadata are written into deliverables.

## Tests

Offline regression tests use synthetic Korean captions:

```sh
python -X utf8 tests/转录测试-Transcript-tests.py -v
```

GitHub Actions runs the same tests on Windows and Linux with Python 3.10 and 3.12. Media tools, network access, and model downloads are unnecessary for these tests.

## Contributing

See [contribution guidance](贡献指南-Contributing.md) and [security reporting](安全说明-Security.md). Please submit small changes with a reproducible case and tests. Do not upload private recordings, transcripts, credentials, or model files.

## License and dependencies

Project code and documentation: **MIT**, copyright © 2026 **miao010625**. See [LICENSE](LICENSE).

External programs are installed separately and retain their own authorship and licenses. See [dependency notes](依赖说明-Dependencies.md).
