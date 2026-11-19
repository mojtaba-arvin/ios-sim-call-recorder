import XCTest
@testable import CallRecorderCore

final class RecordingImportValidatorTests: XCTestCase {
    func testAcceptsValidAppleNotesExportMetadata() {
        XCTAssertNoThrow(try validate(validMetadata(source: .appleNotesExport)).get())
    }

    func testAcceptsValidExternalRecorderMetadata() {
        XCTAssertNoThrow(try validate(validMetadata(
            fileName: "external.wav",
            container: .wav,
            source: .externalRecorder
        )).get())
    }

    func testRejectsWhitespaceOnlyFileName() {
        XCTAssertEqual(validate(validMetadata(fileName: "  ")).failure, .emptyFileName)
    }

    func testRejectsUnsupportedExtension() {
        XCTAssertEqual(validate(validMetadata(fileName: "recording.aac")).failure, .unsupportedFileExtension)
    }

    func testRejectsZeroByteFile() {
        XCTAssertEqual(validate(validMetadata(byteCount: 0)).failure, .emptyFile)
    }

    func testRejectsFileAboveMaximumSize() {
        XCTAssertEqual(
            validate(validMetadata(byteCount: RecordingImportValidator.maximumFileSizeBytes + 1)).failure,
            .fileTooLarge(maximumBytes: RecordingImportValidator.maximumFileSizeBytes)
        )
    }

    func testRejectsNonFiniteOrNonPositiveDuration() {
        XCTAssertEqual(validate(validMetadata(duration: .nan)).failure, .invalidDuration)
        XCTAssertEqual(validate(validMetadata(duration: 0)).failure, .invalidDuration)
        XCTAssertEqual(validate(validMetadata(duration: -.infinity)).failure, .invalidDuration)
    }

    func testRejectsDurationAboveMaximum() {
        XCTAssertEqual(
            validate(validMetadata(duration: RecordingImportValidator.maximumDurationSeconds + 1)).failure,
            .durationTooLong(maximumSeconds: RecordingImportValidator.maximumDurationSeconds)
        )
    }

    func testRejectsInvalidSampleRate() {
        XCTAssertEqual(validate(validMetadata(sampleRate: 7_999)).failure, .invalidSampleRate)
        XCTAssertEqual(validate(validMetadata(sampleRate: .infinity)).failure, .invalidSampleRate)
    }

    func testRejectsUnsupportedChannelCount() {
        XCTAssertEqual(validate(validMetadata(channels: 0)).failure, .unsupportedChannelCount)
        XCTAssertEqual(validate(validMetadata(channels: 3)).failure, .unsupportedChannelCount)
    }

    func testRejectsExtensionAndProbedContainerMismatch() {
        XCTAssertEqual(
            validate(validMetadata(fileName: "recording.m4a", container: .wav)).failure,
            .extensionContainerMismatch
        )
    }

    func testAcceptsBoundaryValues() {
        let metadata = validMetadata(
            byteCount: RecordingImportValidator.maximumFileSizeBytes,
            duration: RecordingImportValidator.maximumDurationSeconds,
            sampleRate: 192_000,
            channels: 2
        )
        XCTAssertNoThrow(try validate(metadata).get())
    }

    private func validate(
        _ metadata: RecordingImportMetadata
    ) -> Result<Void, RecordingImportValidationError> {
        RecordingImportValidator.validate(metadata)
    }

    private func validMetadata(
        fileName: String = "call-recording.m4a",
        byteCount: Int64 = 1_024,
        duration: TimeInterval = 60,
        sampleRate: Double = 44_100,
        channels: Int = 1,
        container: RecordingAudioContainer = .m4a,
        source: RecordingImportSource = .appleNotesExport
    ) -> RecordingImportMetadata {
        RecordingImportMetadata(
            fileName: fileName,
            byteCount: byteCount,
            durationSeconds: duration,
            sampleRateHz: sampleRate,
            channelCount: channels,
            container: container,
            source: source
        )
    }
}
