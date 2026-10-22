# External dependencies

No third-party source code, binaries, or model weights are included in this repository.

| Component | Purpose | Upstream |
| --- | --- | --- |
| Python | Standard-library runtime | https://www.python.org/ |
| yt-dlp | Optional single-item media download | https://github.com/yt-dlp/yt-dlp |
| FFmpeg / FFprobe | Media verification and audio conversion | https://ffmpeg.org/ |
| whisper.cpp | Local speech recognition executable | https://github.com/ggml-org/whisper.cpp |
| Whisper models | Model weights loaded by whisper.cpp | Follow the model source's license |

These components are installed separately and retain their own authorship and
license terms. The project's MIT license applies to this repository's implementation,
not to independently distributed executables or models.
