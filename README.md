# macos-local-ocr

Extract text from screenshots and scans on your Mac. Apple Vision runs first and
Tesseract takes over if it fails or returns no text. Use the command line tool
directly or load it as an agent skill.

This uses Apple's Vision OCR framework, not Apple Intelligence or a language
model. It needs no API key, model server or separately downloaded model weights.

## Setup

You need macOS, the Xcode Command Line Tools, and Python 3.9 or later. The Python
runner uses only the standard library. English is the supported language in
this version.

Tested on Apple Silicon with macOS 26.5. Older macOS releases and Intel Macs
have not been tested.

Clone the repository:

```sh
git clone https://github.com/jimliddle/macos-local-ocr.git
cd macos-local-ocr
```

Then build the helper:

```sh
# Only if the developer tools are missing; finish the installer before continuing:
xcode-select --install

# Build the native helper:
bash scripts/build.sh

# Optional fallback, for users who already have Homebrew:
brew install tesseract
```

The build writes only to `.build/`. It does not change shell profiles, install a
service or register a skill. Rebuild after moving between Mac architectures.

## Read an image

```sh
python3 scripts/ocr.py "/path/to/screenshot.png"
```

The command returns JSON on stdout:

```json
{"ok": true, "engine": "apple-vision", "text": "Invoice 4725", "fallback_used": false, "fallback_reason": null}
```

For plain text, add `--format text`. Keep JSON when the caller needs to know
which engine ran. Errors go to stderr with a nonzero exit status; cancellation
returns 130. Failed runs do not emit a success result.

```sh
# Use a particular engine without fallback:
python3 scripts/ocr.py "/path/to/image.jpg" --engine vision
python3 scripts/ocr.py "/path/to/image.jpg" --engine tesseract

# Set the shared runtime budget (default 30 seconds, maximum 300):
python3 scripts/ocr.py "/path/to/image.png" --timeout 45
```

Auto mode gives Vision at most 15 seconds, then Tesseract gets the remaining
budget, build time is separate. There is no retry based on confidence or text
content and nonempty recognition can still be wrong.

## Use as a skill

The repository root is an [Agent Skills](https://agentskills.io/specification)
directory. Place the complete `macos-local-ocr` folder in your agent's supported
skills location, or point its skill loader at this directory. Keep `scripts/`
beside `SKILL.md`; copying just the Markdown file is not enough. Build the helper
in the installed folder. Back up any existing installation before replacing it.

Example request:

> Use the macos-local-ocr skill to transcribe /path/to/screenshot.png. Preserve
> the text as recognized and tell me if Tesseract was used.

Discovery and invocation syntax depend on the agent. This package does not
install an MCP server or modify agent settings. Client specific loading has not
yet been tested for this standalone package.

## Behaviour and limits

- PNG and JPEG input only, up to 24 MiB per file. PDFs must be rendered separately.
- Vision uses accurate English recognition with language correction disabled.
  This avoids that correction pass, it does not guarantee exact transcription.
- The Vision helper rejects multi image files and images over 32 million pixels.
  Those are helper checks, not shared Tesseract limits.
- Tesseract uses its installed English data and default segmentation. Its output
  can differ from Vision, including whitespace and reading order.
- No layout reconstruction, table extraction, handwriting guarantee or accuracy
  benchmark. Inspect important numbers, punctuation and code against the image.
- No screen capture, cloud OCR or automatic dependency downloads. Image files
  are read, not rewritten. The runner creates no transcript or output files.
- A calling agent may store or upload returned text. Local OCR does not make a
  hosted agent session private or offline. Shell redirection also creates a file
  under your shell's normal permissions.

The helper depends on macOS services. A restricted execution environment can
block Vision even when compilation succeeds. Try the standalone helper directly
to see its diagnostic output: `.build/vision-ocr /path/to/image.png`. Do not
disable security controls automatically to work around a failure.

## Tests

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash scripts/build.sh
python3 tests/smoke.py
```

Unit tests exercise engine selection, failures, cancellation and subprocess
cleanup. The smoke test generates a synthetic image, checks real Vision output,
then forces the automatic Tesseract fallback. It requires both engines. No
personal documents, screenshots or model calls are used. See [TESTING.md](TESTING.md)
for recorded results and gaps.

## License and credits

The helper and fallback runner started in the maintainer's local MiniSuite OCR
integration. This package runs independently of MiniSuite and its agent setup.

The source, skill and documentation are under the [MIT license](LICENSE).
[Dependency notices](NOTICE.md) credit Apple, Tesseract and Python and link to
their terms. Their software and model data are not bundled here. This project
is not affiliated with or endorsed by Apple.

Apple documents the underlying API in
[Recognizing Text in Images](https://developer.apple.com/documentation/vision/recognizing-text-in-images).
