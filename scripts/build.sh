#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(uname -s)" != Darwin ]]; then
    printf 'Apple Vision requires macOS.\n' >&2
    exit 1
fi
if ! xcrun --find swiftc >/dev/null 2>&1; then
    printf 'Install the Xcode Command Line Tools with: xcode-select --install\n' >&2
    exit 1
fi
mkdir -p "$ROOT/.build/module-cache"
TEMP="$(mktemp "$ROOT/.build/vision-ocr.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT
xcrun swiftc -O -module-cache-path "$ROOT/.build/module-cache" \
    "$ROOT/scripts/vision_ocr.swift" -o "$TEMP"
chmod 755 "$TEMP"
mv -f "$TEMP" "$ROOT/.build/vision-ocr"
printf 'Apple Vision OCR helper built.\n'
