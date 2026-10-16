import AppKit

let image = NSImage(size: NSSize(width: 1200, height: 360))
image.lockFocus()
NSColor.white.setFill()
NSRect(x: 0, y: 0, width: 1200, height: 360).fill()
if !CommandLine.arguments.contains("--blank") {
    let text = "Invoice 4725\nTotal 123.45\nReference ABC-2048" as NSString
    text.draw(at: NSPoint(x: 60, y: 100), withAttributes: [
        .font: NSFont.monospacedSystemFont(ofSize: 42, weight: .regular),
        .foregroundColor: NSColor.black
    ])
}
image.unlockFocus()
let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
let target = URL(fileURLWithPath: CommandLine.arguments[1])
let format: NSBitmapImageRep.FileType = target.pathExtension == "jpg" ? .jpeg : .png
try bitmap.representation(using: format, properties: [:])!.write(to: target)
