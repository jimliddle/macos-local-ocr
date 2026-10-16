#!/usr/bin/env python3
"""Read a local image with Apple Vision, falling back to Tesseract."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".build" / "vision-ocr"
MAX_BYTES = 24 * 1024 * 1024


class OCRError(Exception):
    pass


def run(command, timeout):
    """Reap the engine and its children on timeout or interruption."""
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
    except OSError as exc:
        raise OCRError("OCR executable unavailable") from exc
    finished = False
    try:
        try:
            out, _ = process.communicate(timeout=timeout)
            finished = True
        except subprocess.TimeoutExpired as exc:
            raise OCRError("OCR engine timed out") from exc
        if process.returncode:
            raise OCRError(f"OCR engine exited with code {process.returncode}")
        try:
            return out.decode("utf-8")
        except UnicodeError as exc:
            raise OCRError("OCR engine returned invalid UTF-8") from exc
    finally:
        if not finished:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.communicate()


def validate_image(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise OCRError("Input must be an existing local image file")
    if path.stat().st_size > MAX_BYTES:
        raise OCRError("Input exceeds the 24 MiB file limit")
    with path.open("rb") as source:
        header = source.read(8)
    if not (header == b"\x89PNG\r\n\x1a\n" or header.startswith(b"\xff\xd8\xff")):
        raise OCRError("Only PNG and JPEG images are supported; render PDFs separately")
    return path


def recognize(image, engine="auto", timeout=30, vision_helper=HELPER):
    if engine not in ("auto", "vision", "tesseract"):
        raise OCRError("Unknown OCR engine")
    if not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise OCRError("Timeout must be greater than zero and at most 300 seconds")
    image = validate_image(image)
    deadline = time.monotonic() + timeout
    reason = None
    if engine != "tesseract":
        try:
            raw = run([str(vision_helper), str(image)], min(15, timeout))
            try:
                data = json.loads(raw)
            except ValueError as exc:
                raise OCRError("Apple Vision returned invalid JSON") from exc
            if not isinstance(data, dict) or not isinstance(data.get("text"), str):
                raise OCRError("Apple Vision returned an invalid text field")
            if not data["text"].strip():
                raise OCRError("Apple Vision returned no text")
            return {"ok": True, "engine": "apple-vision", "text": data["text"],
                    "fallback_used": False, "fallback_reason": None}
        except OCRError as exc:
            if engine == "vision":
                raise
            reason = str(exc)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise OCRError("OCR time budget exhausted")
    executable = shutil.which("tesseract")
    if not executable:
        raise OCRError((reason + "; " if reason else "") + "Tesseract is not installed")
    text = run([executable, str(image), "stdout", "-l", "eng"], remaining)
    if not text.strip():
        raise OCRError("Tesseract returned no text")
    return {"ok": True, "engine": "tesseract", "text": text,
            "fallback_used": engine == "auto", "fallback_reason": reason}


def interrupted(_signum, _frame):
    raise KeyboardInterrupt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--engine", choices=("auto", "vision", "tesseract"), default="auto")
    parser.add_argument("--timeout", type=float, default=30, help="Total engine budget in seconds (default: 30)")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--vision-helper", type=Path, default=HELPER,
                        help="Override the compiled helper, including for fallback tests")
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        result = recognize(args.image, args.engine, args.timeout, args.vision_helper)
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": "OCR cancelled"}), file=sys.stderr)
        return 130
    except (OCRError, OSError) as exc:
        message = str(exc) if isinstance(exc, OCRError) else "Cannot read the input file"
        print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
        return 1
    if args.format == "text":
        sys.stdout.write(result["text"])
        if not result["text"].endswith("\n"):
            sys.stdout.write("\n")
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
