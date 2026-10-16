# Verification

Checked on 16 October 2026 with macOS 26.5 (arm64), Python 3.9.6 and Tesseract
5.5.3. Tests use synthetic text only.

| Check | Result |
| --- | --- |
| Python unit tests | 17 passed |
| Native Swift helper build | Passed |
| Apple Vision on synthetic PNG and JPEG | Passed |
| Automatic Tesseract fallback on the same two images | Passed |
| Blank image | Error returned, no success output |
| Input file hashes before and after OCR | Unchanged |
| Skill frontmatter validation | Passed |
| Shell script syntax | Passed |

The real-engine test deliberately points to a nonexistent Vision helper for
its fallback checks. Its primary checks require `apple-vision` in the result;
silently succeeding through Tesseract does not pass that test.

Vision failed inside the restricted execution environment, while Tesseract
worked. Repeating the test with normal macOS access passed both engines. This
is a deployment limitation worth checking in sandboxed agent clients.

The smoke test is a functional check, not an OCR accuracy benchmark. It does not
establish performance on handwriting, poor scans, multiple columns or code.
Agent-client loading, Intel Macs and older macOS versions need separate checks.
