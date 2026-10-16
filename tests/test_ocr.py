import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ocr", ROOT / "scripts" / "ocr.py")
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)


class OCRTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "image with spaces.png"
        # Routing tests stub the engines; image decoding is covered by the smoke test.
        self.image.write_bytes(b"\x89PNG\r\n\x1a\n")

    def test_primary_preserves_text_and_does_not_probe_fallback(self):
        text = "  odd_id = 001\n\tunchanged  "
        with patch.object(ocr, "run", return_value=json.dumps({"text": text})) as run, \
                patch.object(ocr.shutil, "which") as which:
            result = ocr.recognize(self.image)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["engine"], "apple-vision")
        self.assertFalse(result["fallback_used"])
        run.assert_called_once()
        which.assert_not_called()

    def test_failure_variants_fall_back_once(self):
        for raw in (ocr.OCRError("timeout"), "", "invalid", "[]", '{"text":1}',
                    '{"text":"  "}', "null"):
            with self.subTest(raw=raw), patch.object(ocr, "run", side_effect=[raw, "fallback\n"]) as run, \
                    patch.object(ocr.shutil, "which", return_value="/test/tesseract"):
                result = ocr.recognize(self.image)
                self.assertEqual(result["text"], "fallback\n")
                self.assertTrue(result["fallback_used"])
                self.assertTrue(result["fallback_reason"])
                self.assertEqual(run.call_count, 2)
                self.assertEqual(run.call_args.args[0],
                                 ["/test/tesseract", str(self.image.resolve()), "stdout", "-l", "eng"])

    def test_forced_vision_never_falls_back(self):
        with patch.object(ocr, "run", side_effect=ocr.OCRError("failed")), \
                patch.object(ocr.shutil, "which") as which:
            with self.assertRaises(ocr.OCRError):
                ocr.recognize(self.image, engine="vision")
            which.assert_not_called()

    def test_forced_tesseract_skips_vision(self):
        with patch.object(ocr, "run", return_value="text") as run, \
                patch.object(ocr.shutil, "which", return_value="/test/tesseract"):
            result = ocr.recognize(self.image, engine="tesseract")
        self.assertFalse(result["fallback_used"])
        self.assertIsNone(result["fallback_reason"])
        self.assertEqual(run.call_args.args[0][0], "/test/tesseract")

    def test_cancellation_never_falls_back(self):
        with patch.object(ocr, "run", side_effect=KeyboardInterrupt), \
                patch.object(ocr.shutil, "which") as which:
            with self.assertRaises(KeyboardInterrupt):
                ocr.recognize(self.image)
            which.assert_not_called()

    def test_remaining_time_shared(self):
        with patch.object(ocr.time, "monotonic", side_effect=[100, 115]), \
                patch.object(ocr, "run", side_effect=[ocr.OCRError("timeout"), "text"]) as run, \
                patch.object(ocr.shutil, "which", return_value="tesseract"):
            ocr.recognize(self.image)
        self.assertEqual(run.call_args.args[1], 15)

    def test_exhausted_budget_does_not_launch_fallback(self):
        with patch.object(ocr.time, "monotonic", side_effect=[100, 131]), \
                patch.object(ocr, "run", side_effect=ocr.OCRError("timeout")) as run:
            with self.assertRaisesRegex(ocr.OCRError, "budget exhausted"):
                ocr.recognize(self.image)
            run.assert_called_once()

    def test_missing_tesseract_reports_primary_failure(self):
        with patch.object(ocr, "run", side_effect=ocr.OCRError("primary failed")), \
                patch.object(ocr.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ocr.OCRError, "primary failed; Tesseract is not installed"):
                ocr.recognize(self.image)

    def test_empty_or_failed_fallback_is_error(self):
        for result in ("   ", ocr.OCRError("engine failed")):
            with self.subTest(result=result), \
                    patch.object(ocr, "run", side_effect=[ocr.OCRError("primary failed"), result]), \
                    patch.object(ocr.shutil, "which", return_value="tesseract"):
                with self.assertRaises(ocr.OCRError):
                    ocr.recognize(self.image)

    def test_invalid_input_does_not_launch_engine(self):
        for path in (self.image.parent, self.image.parent / "missing.png"):
            with patch.object(ocr, "run") as run:
                with self.assertRaises(ocr.OCRError):
                    ocr.recognize(path)
                run.assert_not_called()
        self.image.write_bytes(b"%PDF-1.7")
        with self.assertRaisesRegex(ocr.OCRError, "Only PNG and JPEG"):
            ocr.recognize(self.image)

    def test_size_limit(self):
        with patch.object(ocr, "MAX_BYTES", 4):
            with self.assertRaisesRegex(ocr.OCRError, "file limit"):
                ocr.recognize(self.image)

    def test_timeout_validation(self):
        for value in (0, -1, 301, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ocr.OCRError):
                ocr.recognize(self.image, timeout=value)

    def test_cli_error_and_cancellation_have_no_success_stdout(self):
        for error, status in ((ocr.OCRError("failed"), 1), (KeyboardInterrupt(), 130)):
            out, err = io.StringIO(), io.StringIO()
            with patch.object(ocr, "recognize", side_effect=error), \
                    patch.object(ocr.signal, "signal"), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(ocr.main([str(self.image)]), status)
            self.assertEqual(out.getvalue(), "")
            self.assertFalse(json.loads(err.getvalue())["ok"])

    def test_real_subprocess_errors(self):
        for code in ("import sys; sys.exit(2)", "import sys; sys.stdout.buffer.write(b'\\xff')"):
            with self.subTest(code=code), self.assertRaises(ocr.OCRError):
                ocr.run([sys.executable, "-c", code], 2)
        with self.assertRaises(ocr.OCRError):
            ocr.run([str(self.image.parent / "missing-executable")], 2)

    def test_real_subprocess_timeout_is_bounded(self):
        start = time.monotonic()
        with self.assertRaisesRegex(ocr.OCRError, "timed out"):
            ocr.run([sys.executable, "-c", "import time; time.sleep(10)"], .1)
        self.assertLess(time.monotonic() - start, 3)

    @unittest.skipUnless(os.name == "posix", "POSIX process groups required")
    def test_timeout_cleans_up_child_after_parent_exits(self):
        code = ("import subprocess,sys; "
                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])")
        start = time.monotonic()
        with self.assertRaisesRegex(ocr.OCRError, "timed out"):
            ocr.run([sys.executable, "-c", code], .2)
        self.assertLess(time.monotonic() - start, 3)

    @unittest.skipUnless(os.name == "posix", "POSIX signals required")
    def test_sigterm_stops_engine_without_fallback(self):
        helper = self.image.parent / "sleep-helper"
        marker = self.image.parent / "pid"
        helper.write_text(f'#!{sys.executable}\nimport os,time\n'
                          f'open({str(marker)!r}, "w").write(str(os.getpid()))\n'
                          'time.sleep(60)\n')
        helper.chmod(0o700)
        process = subprocess.Popen([sys.executable, str(ROOT / "scripts/ocr.py"),
                                    str(self.image), "--vision-helper", str(helper)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists())
            process.send_signal(signal.SIGTERM)
            out, err = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 130)
            self.assertEqual(out, b"")
            self.assertEqual(json.loads(err)["error"], "OCR cancelled")
            with self.assertRaises(ProcessLookupError):
                os.kill(int(marker.read_text()), 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == "__main__":
    unittest.main()
