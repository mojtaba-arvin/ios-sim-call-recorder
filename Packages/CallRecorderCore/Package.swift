// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "CallRecorderCore",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [.library(name: "CallRecorderCore", targets: ["CallRecorderCore"])],
    targets: [
        .target(name: "CallRecorderCore"),
        .testTarget(name: "CallRecorderCoreTests", dependencies: ["CallRecorderCore"])
    ]
)
