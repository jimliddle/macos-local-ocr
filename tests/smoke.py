"""Real OCR against generated fixtures. Requires macOS, built Vision, and Tesseract."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def execute(args, timeout=60):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout)


def main():
    if not (ROOT / ".build/vision-ocr").is_file():
        raise SystemExit("Build the helper first: bash scripts/build.sh")
    with tempfile.TemporaryDirectory(prefix="local-ocr-smoke-") as temp:
        temp = Path(temp)
        renderer = temp / "make-fixture"
        execute(["xcrun", "swiftc", "-module-cache-path", str(ROOT / ".build/module-cache"),
                 str(ROOT / "tests/make_fixture.swift"), "-o", str(renderer)], timeout=120)
        results = []
        for suffix in ("png", "jpg"):
            image = temp / ("synthetic image." + suffix)
            execute([str(renderer), str(image)])
            before = hashlib.sha256(image.read_bytes()).hexdigest()
            for fallback in (False, True):
                command = [sys.executable, str(ROOT / "scripts/ocr.py"), str(image)]
                if fallback:
                    command += ["--vision-helper", str(temp / "missing-helper")]
                result = json.loads(execute(command).stdout)
                expected = "tesseract" if fallback else "apple-vision"
                assert result["engine"] == expected, result
                assert result["fallback_used"] == fallback, result
                for phrase in ("Invoice 4725", "Total 123.45", "Reference ABC-2048"):
                    assert phrase in result["text"], result
                results.append({"format": suffix, "engine": expected, "passed": True})
            assert hashlib.sha256(image.read_bytes()).hexdigest() == before
        blank = temp / "blank.png"
        execute([str(renderer), str(blank), "--blank"])
        result = subprocess.run([sys.executable, str(ROOT / "scripts/ocr.py"), str(blank)],
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 1 and not result.stdout, result
        assert "no text" in json.loads(result.stderr)["error"], result.stderr
        print(json.dumps({"checks": results, "blank_rejected": True,
                          "input_files_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
