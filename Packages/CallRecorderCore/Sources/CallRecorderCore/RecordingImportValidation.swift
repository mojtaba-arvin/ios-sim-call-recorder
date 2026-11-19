import Foundation

/// Where the user obtained a recording before explicitly importing it.
public enum RecordingImportSource: String, Equatable, Sendable {
    case appleNotesExport
    case externalRecorder
    case filesApp
    case other
}

/// Container formats accepted by the import boundary. The app-shell adapter
/// must inspect the actual media container; a filename extension is not proof.
public enum RecordingAudioContainer: String, CaseIterable, Equatable, Sendable {
    case m4a
    case mp3
    case wav
    case caf
    case aiff
}

/// Media properties extracted by a platform adapter (for example AVFoundation).
/// No phone number, contact name, transcript or raw audio is retained here.
public struct RecordingImportMetadata: Equatable, Sendable {
    public let fileName: String
    public let byteCount: Int64
    public let durationSeconds: TimeInterval
    public let sampleRateHz: Double
    public let channelCount: Int
    public let container: RecordingAudioContainer
    public let source: RecordingImportSource

    public init(
        fileName: String,
        byteCount: Int64,
        durationSeconds: TimeInterval,
        sampleRateHz: Double,
        channelCount: Int,
        container: RecordingAudioContainer,
        source: RecordingImportSource
    ) {
        self.fileName = fileName
        self.byteCount = byteCount
        self.durationSeconds = durationSeconds
        self.sampleRateHz = sampleRateHz
        self.channelCount = channelCount
        self.container = container
        self.source = source
    }
}

public enum RecordingImportValidationError: Error, Equatable, Sendable {
    case emptyFileName
    case unsupportedFileExtension
    case emptyFile
    case fileTooLarge(maximumBytes: Int64)
    case invalidDuration
    case durationTooLong(maximumSeconds: TimeInterval)
    case invalidSampleRate
    case unsupportedChannelCount
    case extensionContainerMismatch
}

/// Pure validation for imported recordings. The caller remains responsible
/// for security-scoped URL access, actual media probing, copying into app
/// storage, and cleanup of temporary files.
public enum RecordingImportValidator {
    public static let maximumFileSizeBytes: Int64 = 500 * 1_024 * 1_024
    public static let maximumDurationSeconds: TimeInterval = 24 * 60 * 60
    public static let supportedSampleRateRange: ClosedRange<Double> = 8_000...192_000

    public static func validate(
        _ metadata: RecordingImportMetadata
    ) -> Result<Void, RecordingImportValidationError> {
        let normalizedName = metadata.fileName
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedName.isEmpty else {
            return .failure(.emptyFileName)
        }

        guard let extensionValue = normalizedName.split(separator: ".").last,
              normalizedName.contains("."),
              let declaredContainer = RecordingAudioContainer(
                rawValue: extensionValue.lowercased()
              ) else {
            return .failure(.unsupportedFileExtension)
        }

        guard metadata.byteCount > 0 else {
            return .failure(.emptyFile)
        }
        guard metadata.byteCount <= maximumFileSizeBytes else {
            return .failure(.fileTooLarge(maximumBytes: maximumFileSizeBytes))
        }
        guard metadata.durationSeconds.isFinite,
              metadata.durationSeconds > 0 else {
            return .failure(.invalidDuration)
        }
        guard metadata.durationSeconds <= maximumDurationSeconds else {
            return .failure(.durationTooLong(maximumSeconds: maximumDurationSeconds))
        }
        guard metadata.sampleRateHz.isFinite,
              supportedSampleRateRange.contains(metadata.sampleRateHz) else {
            return .failure(.invalidSampleRate)
        }
        guard (1...2).contains(metadata.channelCount) else {
            return .failure(.unsupportedChannelCount)
        }
        guard declaredContainer == metadata.container else {
            return .failure(.extensionContainerMismatch)
        }

        return .success(())
    }
}
