"""Offline command-line regression tests using synthetic Korean subtitles."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "韩语转录-Korean-transcript.py"
CAPTIONS = "1\n00:00:00,125 --> 00:00:01,250\n안녕하세요.\n\n2\n00:00:02,000 --> 00:00:03,500\n한국어 자막 테스트입니다.\n"


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.source = self.root / "입력.srt"
        self.output = self.root / "결과"

    def invoke(self, text=CAPTIONS, *flags):
        self.source.write_text(text, encoding="utf-8", newline="")
        return subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPT),
                str(self.source),
                "--out",
                str(self.output),
                *flags,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_korean_text_and_millisecond_timestamps_are_preserved(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.output / "全文-Transcript.txt").read_text(encoding="utf-8"),
            "안녕하세요.\n\n한국어 자막 테스트입니다.\n",
        )
        self.assertIn(
            "00:00:00.125",
            (self.output / "时间戳-Timestamped.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "00:00:03,500",
            (self.output / "字幕-Subtitles.srt").read_text(encoding="utf-8"),
        )
        self.assertEqual(self.source.read_text(encoding="utf-8"), CAPTIONS)
        self.assertEqual(len(list(self.output.iterdir())), 3)

    def test_bom_crlf_and_dot_timestamps(self):
        result = self.invoke(
            "\ufeff1\r\n00:00:00.000 --> 00:00:01.000\r\n<b>반갑습니다.</b>\r\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.output / "全文-Transcript.txt").read_text(encoding="utf-8"), "반갑습니다.\n"
        )

    def test_intentional_repeated_speech_is_retained(self):
        result = self.invoke(CAPTIONS.replace("한국어 자막 테스트입니다.", "안녕하세요."))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.output / "全文-Transcript.txt")
            .read_text(encoding="utf-8")
            .count("안녕하세요."),
            2,
        )

    def test_multiline_cue_and_html_entities(self):
        result = self.invoke("1\n00:00:00,000 --> 00:00:01,000\n하나 &amp; 둘\n셋\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.output / "全文-Transcript.txt").read_text(encoding="utf-8"),
            "하나 & 둘 셋\n",
        )

    def test_empty_subtitles_fail_without_deliverables(self):
        result = self.invoke("")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No usable subtitle cues", result.stderr)
        self.assertFalse(self.output.exists())

    def test_reversed_timestamps_fail(self):
        result = self.invoke("1\n00:00:03,000 --> 00:00:01,000\n잘못된 시간\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("end must be after start", result.stderr)

    def test_out_of_order_cues_fail(self):
        result = self.invoke(CAPTIONS + "\n3\n00:00:00,000 --> 00:00:01,000\n역순\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chronological", result.stderr)

    def test_invalid_minutes_fail(self):
        result = self.invoke("1\n00:99:00,000 --> 01:40:00,000\n시간\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid timestamp", result.stderr)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        target = self.output / "全文-Transcript.txt"
        target.write_text("keep me", encoding="utf-8")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_missing_source_fails_without_a_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPT),
                str(self.source),
                "--out",
                str(self.output),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Source file does not exist", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_url_fails_without_a_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPT),
                "https://[broken",
                "--out",
                str(self.output),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

    def test_url_credentials_are_never_echoed(self):
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPT),
                "https://private-user:sample-password@example.org/a.mp4",
                "--out",
                str(self.output),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("sample-password", result.stderr + result.stdout)

    def test_missing_whisper_error_names_the_supported_option(self):
        media = self.root / "sample.wav"
        media.write_bytes(b"fixture")
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(SCRIPT),
                str(media),
                "--out",
                str(self.output),
                "--ffmpeg",
                sys.executable,
                "--ffprobe",
                sys.executable,
                "--whisper",
                str(self.root / "missing"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("supply --whisper", result.stderr)
        self.assertNotIn("--whisper-cli", result.stderr)


if __name__ == "__main__":
    unittest.main()
