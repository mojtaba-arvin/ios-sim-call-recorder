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

extension RecordingImportValidationError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case .emptyFileName:
            return "The selected file has no valid filename."
        case .unsupportedFileExtension:
            return "Choose an M4A, MP3, WAV, CAF, or AIFF audio file."
        case .emptyFile:
            return "The selected audio file is empty."
        case .fileTooLarge(let maximumBytes):
            return "The selected file exceeds the maximum size of \(maximumBytes / 1_048_576) MiB."
        case .invalidDuration:
            return "The selected file has an invalid audio duration."
        case .durationTooLong(let maximumSeconds):
            return "The selected recording exceeds the maximum duration of \(Int(maximumSeconds / 3_600)) hours."
        case .invalidSampleRate:
            return "The selected file has an unsupported sample rate."
        case .unsupportedChannelCount:
            return "The selected file must contain one or two audio channels."
        case .extensionContainerMismatch:
            return "The file extension does not match its actual audio container."
        }
    }
}

struct ImportedRecording: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    let fileExtension: String
    let byteCount: Int64
    let durationSeconds: Double
    let importedAt: Date
}

/// Owns the user-initiated import boundary. Imported files are copied to
/// app-private storage under opaque names; source filenames are not persisted.
actor RecordingImportService {
    private let fileManager = FileManager.default

    func importRecording(
        from sourceURL: URL,
        source: RecordingImportSource
    ) async throws -> ImportedRecording {
        let didStartAccess = sourceURL.startAccessingSecurityScopedResource()
        defer {
            if didStartAccess {
                sourceURL.stopAccessingSecurityScopedResource()
            }
        }

        let stagingDirectory = try privateDirectory(named: "Staging")
        let recordingsDirectory = try privateDirectory(named: "Recordings")
        let stagedURL = stagingDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(sourceURL.pathExtension)

        var stagedFileExists = false
        defer {
            if stagedFileExists {
                try? fileManager.removeItem(at: stagedURL)
            }
        }

        // Coordinate reads from File Provider / external document locations.
        // All later probing happens against our app-private staged copy.
        var coordinationError: NSError?
        var copyError: Error?
        let coordinator = NSFileCoordinator()
        coordinator.coordinate(
            readingItemAt: sourceURL,
            options: [],
            error: &coordinationError
        ) { coordinatedURL in
            do {
                try fileManager.copyItem(at: coordinatedURL, to: stagedURL)
                stagedFileExists = true
            } catch {
                copyError = error
            }
        }

        if let coordinationError { throw coordinationError }
        if let copyError { throw copyError }
        guard stagedFileExists else {
            throw RecordingImportServiceError.storageUnavailable
        }

        let container = try AudioContainerProbe.detect(at: stagedURL)
        let attributes = try fileManager.attributesOfItem(atPath: stagedURL.path)
        guard let size = (attributes[.size] as? NSNumber)?.int64Value else {
            throw RecordingImportServiceError.missingFileSize
        }

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

        let entry = ImportedRecording(
            id: UUID(),
            fileExtension: container.rawValue,
            byteCount: size,
            durationSeconds: duration,
            importedAt: Date()
        )
        let finalURL = recordingsDirectory
            .appendingPathComponent(entry.id.uuidString)
            .appendingPathExtension(container.rawValue)

        try fileManager.moveItem(at: stagedURL, to: finalURL)
        stagedFileExists = false

        do {
            var entries = try loadCatalog()
            entries.append(entry)
            try saveCatalog(entries)
        } catch {
            try? fileManager.removeItem(at: finalURL)
            throw error
        }

        return entry
    }

    func recordings() throws -> [ImportedRecording] {
        let entries = try loadCatalog()
        var validEntries: [ImportedRecording] = []
        for entry in entries {
            if fileManager.fileExists(atPath: try recordingURL(for: entry).path) {
                validEntries.append(entry)
            }
        }
        if validEntries != entries {
            try saveCatalog(validEntries)
        }
        return validEntries.sorted { $0.importedAt > $1.importedAt }
    }

    func deleteRecording(id: UUID) throws {
        var entries = try loadCatalog()
        guard let entry = entries.first(where: { $0.id == id }) else { return }

        let url = try recordingURL(for: entry)
        if fileManager.fileExists(atPath: url.path) {
            try fileManager.removeItem(at: url)
        }
        entries.removeAll { $0.id == id }
        try saveCatalog(entries)
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

    private func catalogURL() throws -> URL {
        try privateDirectory(named: "Catalog")
            .appendingPathComponent("recordings.json")
    }

    private func loadCatalog() throws -> [ImportedRecording] {
        let url = try catalogURL()
        guard fileManager.fileExists(atPath: url.path) else { return [] }
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode([ImportedRecording].self, from: data)
    }

    private func saveCatalog(_ entries: [ImportedRecording]) throws {
        let data = try JSONEncoder().encode(entries)
        try data.write(to: catalogURL(), options: .atomic)
    }

    private func recordingURL(for entry: ImportedRecording) throws -> URL {
        try privateDirectory(named: "Recordings")
            .appendingPathComponent(entry.id.uuidString)
            .appendingPathExtension(entry.fileExtension)
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
