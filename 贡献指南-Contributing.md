# Contributing

Maintainer: **miao010625**.

Report an issue with the command used, Python/tool versions, expected behavior,
and a minimal reproduction. Replace URLs and paths that identify private material.
Prefer synthetic subtitles or a short recording you own and have permission to share.

For code changes, create a branch, add a regression test, and run:

```sh
python -X utf8 tests/转录测试-Transcript-tests.py -v
```

Keep changes focused. Explain the user-visible result and which validation you ran.
Changes to downloading or speech recognition should also be checked locally with
real tools; the default CI suite covers subtitle processing without downloads.
Never commit generated transcripts, recordings, model weights, or authentication data.
