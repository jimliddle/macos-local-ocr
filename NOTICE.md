# Credits and dependency licenses

## This repository

Copyright (c) 2026 jimliddle and macos-local-ocr contributors.

The source, tests, skill and documentation are covered by [LICENSE](LICENSE)
(MIT). The OCR helper and fallback behaviour originated in the maintainer's
local MiniSuite integration. No third-party source files, compiled binaries,
SDKs or model weights are included in this repository.

## Apple frameworks and developer tools

The native helper calls Apple's Vision, Foundation and ImageIO frameworks.
The test-image generator also uses AppKit. These are supplied by Apple, not
licensed under this repository's MIT license. Building requires Apple's
developer tools and SDKs; use is subject to the applicable Apple agreements.

- [Apple developer agreements](https://developer.apple.com/support/terms/)
- [Apple software license agreements](https://www.apple.com/legal/sla/)
- [Vision text recognition documentation](https://developer.apple.com/documentation/vision/recognizing-text-in-images)

Apple names identify the APIs and platform used. They do not imply endorsement.

## Tesseract

Tesseract OCR is developed by the Tesseract contributors and distributed under
Apache License 2.0. The optional fallback invokes a separately installed
`tesseract` executable with its English language data. Neither the executable
nor its data or libraries are included here or relicensed as MIT.

- [Project and contributors](https://github.com/tesseract-ocr/tesseract)
- [Author credits](https://github.com/tesseract-ocr/tesseract/blob/main/AUTHORS)
- [Tesseract license](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE)
- [Language-data license](https://github.com/tesseract-ocr/tessdata/blob/main/LICENSE)

Any distribution that bundles Tesseract, language data or their dependencies
must retain the licenses and notices required by those components.

## Python

The runner and tests use a separately installed Python interpreter and its
standard library. Python is maintained by the Python Software Foundation and
contributors and is covered by the PSF license and the additional notices
listed in [Python's license documentation](https://docs.python.org/3/license.html).
No Python runtime or standard-library source is redistributed here.
