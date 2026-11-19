import AVFoundation
import CallRecorderCore
import Foundation

enum RecordingImportServiceError: LocalizedError {
    case unsupportedContainer
    case unreadableAudio
    case missingFileSize
    case storageUnavailable

    var errorDescription: String? {
        switch self {
        case .unsupportedContainer:
            return "This audio container is not supported."
        case .unreadableAudio:
            return "The selected file could not be decoded as audio."
        case .missingFileSize:
            return "The selected file size could not be determined."
        case .storageUnavailable:
            return "Private recording storage is unavailable."
        }
    }
}

/// Owns the user-initiated import boundary. Imported files are copied to
/// app-private storage under opaque names; source filenames are not persisted.
actor RecordingImportService {
    private let fileManager = FileManager.default

    func importRecording(
        from sourceURL: URL,
        source: RecordingImportSource
    ) async throws {
        let didStartAccess = sourceURL.startAccessingSecurityScopedResource()
        defer {
            if didStartAccess {
                sourceURL.stopAccessingSecurityScopedResource()
            }
        }

        let container = try AudioContainerProbe.detect(at: sourceURL)
        let attributes = try fileManager.attributesOfItem(atPath: sourceURL.path)
        guard let size = (attributes[.size] as? NSNumber)?.int64Value else {
            throw RecordingImportServiceError.missingFileSize
        }

        let stagingDirectory = try privateDirectory(named: "Staging")
        let recordingsDirectory = try privateDirectory(named: "Recordings")
        let stagedURL = stagingDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(container.rawValue)
        let finalURL = recordingsDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(container.rawValue)

        var stagedFileExists = false
        defer {
            if stagedFileExists {
                try? fileManager.removeItem(at: stagedURL)
            }
        }

        try fileManager.copyItem(at: sourceURL, to: stagedURL)
        stagedFileExists = true

        let audioFile: AVAudioFile
        do {
            audioFile = try AVAudioFile(forReading: stagedURL)
        } catch {
            throw RecordingImportServiceError.unreadableAudio
        }

        let sampleRate = audioFile.processingFormat.sampleRate
        let channelCount = Int(audioFile.processingFormat.channelCount)
        let duration = Double(audioFile.length) / sampleRate

        let metadata = RecordingImportMetadata(
            fileName: sourceURL.lastPathComponent,
            byteCount: size,
            durationSeconds: duration,
            sampleRateHz: sampleRate,
            channelCount: channelCount,
            container: container,
            source: source
        )

        switch RecordingImportValidator.validate(metadata) {
        case .success:
            break
        case .failure(let error):
            throw error
        }

        try fileManager.moveItem(at: stagedURL, to: finalURL)
        stagedFileExists = false
    }

    private func privateDirectory(named name: String) throws -> URL {
        guard let applicationSupport = fileManager.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first else {
            throw RecordingImportServiceError.storageUnavailable
        }

        let directory = applicationSupport.appendingPathComponent(
            "CallRecorder/\(name)",
            isDirectory: true
        )
        try fileManager.createDirectory(
            at: directory,
            withIntermediateDirectories: true
        )
        return directory
    }
}

private enum AudioContainerProbe {
    static func detect(at url: URL) throws -> RecordingAudioContainer {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let header = try handle.read(upToCount: 12) ?? Data()

        if header.count >= 12 {
            let riff = String(decoding: header[0..<4], as: UTF8.self)
            let wave = String(decoding: header[8..<12], as: UTF8.self)
            if riff == "RIFF", wave == "WAVE" { return .wav }

            let form = String(decoding: header[0..<4], as: UTF8.self)
            let formType = String(decoding: header[8..<12], as: UTF8.self)
            if form == "FORM", formType == "AIFF" || formType == "AIFC" {
                return .aiff
            }

            let atom = String(decoding: header[4..<8], as: UTF8.self)
            if atom == "ftyp" { return .m4a }
        }

        if header.count >= 4, String(decoding: header[0..<4], as: UTF8.self) == "caff" {
            return .caf
        }

        if header.count >= 3,
           String(decoding: header[0..<3], as: UTF8.self) == "ID3" {
            return .mp3
        }

        if header.count >= 2,
           header[0] == 0xFF,
           header[1] & 0xE0 == 0xE0 {
            return .mp3
        }

        throw RecordingImportServiceError.unsupportedContainer
    }
}
