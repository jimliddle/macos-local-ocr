import Foundation
import ImageIO
import Vision

do {
    guard CommandLine.arguments.count == 2 else {
        throw NSError(domain: "Usage: vision-ocr IMAGE", code: 1)
    }
    let url = URL(fileURLWithPath: CommandLine.arguments[1])
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          CGImageSourceGetCount(source) == 1 else {
        throw NSError(domain: "Expected one readable image", code: 2)
    }
    let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
    guard let width = properties?[kCGImagePropertyPixelWidth] as? Int,
          let height = properties?[kCGImagePropertyPixelHeight] as? Int,
          width > 0, height > 0, Double(width) * Double(height) <= 32_000_000 else {
        throw NSError(domain: "Image exceeds 32 million pixels or has invalid dimensions", code: 3)
    }
    // Keep recognition uncorrected so code identifiers are not rewritten.
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["en-US"]
    request.usesLanguageCorrection = false
    try VNImageRequestHandler(url: url, options: [:]).perform([request])
    let text = (request.results ?? []).compactMap {
        $0.topCandidates(1).first?.string
    }.joined(separator: "\n")
    let data = try JSONSerialization.data(withJSONObject: ["text": text])
    FileHandle.standardOutput.write(data)
} catch {
    FileHandle.standardError.write(Data("Apple Vision OCR failed: \(error)\n".utf8))
    exit(1)
}
