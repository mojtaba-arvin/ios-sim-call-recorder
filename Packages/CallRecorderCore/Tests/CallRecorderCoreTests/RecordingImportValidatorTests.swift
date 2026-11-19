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
        XCTAssertEqual(validationError(validMetadata(fileName: "  ")), .emptyFileName)
    }

    func testRejectsUnsupportedExtension() {
        XCTAssertEqual(validationError(validMetadata(fileName: "recording.aac")), .unsupportedFileExtension)
    }

    func testRejectsDotfileAndTrailingDotExtension() {
        XCTAssertEqual(validationError(validMetadata(fileName: ".m4a")), .unsupportedFileExtension)
        XCTAssertEqual(validationError(validMetadata(fileName: "recording.m4a.")), .unsupportedFileExtension)
    }

    func testRejectsZeroByteFile() {
        XCTAssertEqual(validationError(validMetadata(byteCount: 0)), .emptyFile)
    }

    func testRejectsFileAboveMaximumSize() {
        XCTAssertEqual(
            validationError(validMetadata(byteCount: RecordingImportValidator.maximumFileSizeBytes + 1)),
            .fileTooLarge(maximumBytes: RecordingImportValidator.maximumFileSizeBytes)
        )
    }

    func testRejectsNonFiniteOrNonPositiveDuration() {
        XCTAssertEqual(validationError(validMetadata(duration: .nan)), .invalidDuration)
        XCTAssertEqual(validationError(validMetadata(duration: 0)), .invalidDuration)
        XCTAssertEqual(validationError(validMetadata(duration: -.infinity)), .invalidDuration)
    }

    func testRejectsDurationAboveMaximum() {
        XCTAssertEqual(
            validationError(validMetadata(duration: RecordingImportValidator.maximumDurationSeconds + 1)),
            .durationTooLong(maximumSeconds: RecordingImportValidator.maximumDurationSeconds)
        )
    }

    func testRejectsInvalidSampleRate() {
        XCTAssertEqual(validationError(validMetadata(sampleRate: 7_999)), .invalidSampleRate)
        XCTAssertEqual(validationError(validMetadata(sampleRate: .infinity)), .invalidSampleRate)
    }

    func testRejectsUnsupportedChannelCount() {
        XCTAssertEqual(validationError(validMetadata(channels: 0)), .unsupportedChannelCount)
        XCTAssertEqual(validationError(validMetadata(channels: 3)), .unsupportedChannelCount)
    }

    func testRejectsExtensionAndProbedContainerMismatch() {
        XCTAssertEqual(
            validationError(validMetadata(fileName: "recording.m4a", container: .wav)),
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

    private func validationError(
        _ metadata: RecordingImportMetadata
    ) -> RecordingImportValidationError? {
        guard case .failure(let error) = validate(metadata) else {
            return nil
        }
        return error
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
