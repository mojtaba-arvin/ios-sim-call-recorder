import AVFoundation
import CallRecorderCore
import CryptoKit
import Foundation

enum RecordingImportServiceError: LocalizedError {
    case unsupportedContainer
    case unreadableAudio
    case missingFileSize
    case sourceChangedDuringImport
    case validation(RecordingImportValidationError)
    case storageUnavailable
    case insufficientStorage(requiredBytes: Int64, availableBytes: Int64)
    case recordingNotFound
    case recordingFileMissing
    case catalogCorrupted
    case duplicateRecording

    var errorDescription: String? {
        switch self {
        case .unsupportedContainer:
            return "This audio container is not supported."
        case .unreadableAudio:
            return "The selected file could not be decoded as audio."
        case .missingFileSize:
            return "The selected file size could not be determined."
        case .sourceChangedDuringImport:
            return "The selected file changed while it was being imported. Please try again."
        case .validation(let error):
            switch error {
            case .emptyFileName:
                return "The selected file has no valid filename."
            case .unsupportedFileExtension:
                return "Choose an M4A, MP3, WAV, CAF, or AIFF audio file."
            case .emptyFile:
                return "The selected audio file is empty."
            case .fileTooLarge(let maximumBytes):
                return "The selected file exceeds the maximum size of \(maximumBytes / 1_048_576) MiB."
            case .invalidDuration:
                return "The selected recording has an invalid audio duration."
            case .durationTooLong(let maximumSeconds):
                return "The selected recording exceeds the maximum duration of \(Int(maximumSeconds / 3_600)) hours."
            case .invalidSampleRate:
                return "The selected file has an unsupported sample rate."
            case .unsupportedChannelCount:
                return "The selected file must contain one or two audio channels."
            case .extensionContainerMismatch:
                return "The file extension does not match its actual audio container."
            }
        case .storageUnavailable:
            return "Private recording storage is unavailable."
        case .insufficientStorage(let requiredBytes, let availableBytes):
            return "Not enough free storage to safely import this recording. Required: \(requiredBytes / 1_048_576) MiB; available: \(availableBytes / 1_048_576) MiB. Free up space and try again."
        case .recordingNotFound:
            return "This recording is no longer in your library."
        case .recordingFileMissing:
            return "The audio file for this recording is missing."
        case .catalogCorrupted:
            return "The recording catalog is damaged and no valid backup is available. Audio files were left untouched."
        case .duplicateRecording:
            return "This audio file is already in your library."
        }
    }
}

struct ImportedRecording: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    let fileExtension: String
    let byteCount: Int64
    let durationSeconds: Double
    let importedAt: Date
    let contentSHA256: String? = nil
}

/// Owns user-mediated imports, app-private storage, catalog recovery and retention.
actor RecordingImportService {
    private let fileManager = FileManager.default
    private let storageRootURL: URL?
    private let availableStorageProvider: (() throws -> Int64)?
    private let minimumFreeStorageBytes: Int64

    init(
        storageRootURL: URL? = nil,
        minimumFreeStorageBytes: Int64 = 64 * 1_048_576,
        availableStorageProvider: (() throws -> Int64)? = nil
    ) {
        self.storageRootURL = storageRootURL
        self.minimumFreeStorageBytes = max(0, minimumFreeStorageBytes)
        self.availableStorageProvider = availableStorageProvider
    }

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
        let stagedURL = stagingDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(sourceURL.pathExtension)

        var stagedFileExists = false
        defer {
            // copyItem can fail after creating a partial destination when the
            // volume fills mid-copy. Check the path as well as the success flag.
            if stagedFileExists || fileManager.fileExists(atPath: stagedURL.path) {
                try? fileManager.removeItem(at: stagedURL)
            }
        }

        var coordinationError: NSError?
        var copyError: Error?
        var sourceByteCount: Int64?
        let coordinator = NSFileCoordinator()
        coordinator.coordinate(
            readingItemAt: sourceURL,
            options: [],
            error: &coordinationError
        ) { coordinatedURL in
            do {
                let sourceAttributes = try fileManager.attributesOfItem(
                    atPath: coordinatedURL.path
                )
                guard let byteCount = (sourceAttributes[.size] as? NSNumber)?.int64Value else {
                    throw RecordingImportServiceError.missingFileSize
                }
                guard byteCount > 0 else {
                    throw RecordingImportServiceError.validation(.emptyFile)
                }
                guard byteCount <= RecordingImportValidator.maximumFileSizeBytes else {
                    throw RecordingImportServiceError.validation(
                        .fileTooLarge(maximumBytes: RecordingImportValidator.maximumFileSizeBytes)
                    )
                }
                sourceByteCount = byteCount
                try ensureAvailableStorage(for: byteCount)
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
        try AudioContainerProbe.validateDeclaredPayloadLength(at: stagedURL, container: container)
        let attributes = try fileManager.attributesOfItem(atPath: stagedURL.path)
        guard let size = (attributes[.size] as? NSNumber)?.int64Value,
              let sourceByteCount else {
            throw RecordingImportServiceError.missingFileSize
        }
        guard size == sourceByteCount else {
            throw RecordingImportServiceError.sourceChangedDuringImport
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
            throw RecordingImportServiceError.validation(error)
        }

        // AVAudioFile construction validates the container/header, not every
        // compressed or PCM frame. Decode the payload in bounded chunks so a
        // truncated tail cannot be committed as a playable library item.
        try validateAudioPayload(audioFile)

        // Resolve/recover the catalog before moving staged media into the
        // managed directory. Otherwise a first import would look like an
        // unexplained orphan to the missing-catalog fail-closed guard.
        let contentDigest = try sha256(of: stagedURL)
        var entries = try loadCatalog()
        var catalogNeedsSave = false
        // Backfill older catalog entries lazily so upgrades gain duplicate
        // detection without a destructive catalog migration or filename storage.
        for index in entries.indices where entries[index].contentSHA256 == nil {
            let existingURL = try recordingURL(for: entries[index])
            guard fileManager.fileExists(atPath: existingURL.path) else { continue }
            let existingDigest = try sha256(of: existingURL)
            entries[index] = ImportedRecording(
                id: entries[index].id,
                fileExtension: entries[index].fileExtension,
                byteCount: entries[index].byteCount,
                durationSeconds: entries[index].durationSeconds,
                importedAt: entries[index].importedAt,
                contentSHA256: existingDigest
            )
            catalogNeedsSave = true
        }
        if catalogNeedsSave { try saveCatalog(entries) }
        guard !entries.contains(where: { $0.contentSHA256 == contentDigest }) else {
            throw RecordingImportServiceError.duplicateRecording
        }
        let entry = ImportedRecording(
            id: UUID(),
            fileExtension: container.rawValue,
            byteCount: size,
            durationSeconds: duration,
            importedAt: Date(),
            contentSHA256: contentDigest
        )
        let finalURL = try recordingURL(for: entry)

        try fileManager.moveItem(at: stagedURL, to: finalURL)
        stagedFileExists = false

        do {
            try applyCompleteFileProtection(to: finalURL)
            entries.append(entry)
            try saveCatalog(entries)
        } catch {
            try? fileManager.removeItem(at: finalURL)
            throw error
        }

        return entry
    }

    /// Performs recovery and optional retention before returning the library.
    /// A value of zero means keep recordings indefinitely.
    func recordings(retentionDays: Int = 0) throws -> [ImportedRecording] {
        guard let retentionPolicy = RecordingRetentionPolicy(rawValue: retentionDays) else {
            throw RecordingImportServiceError.storageUnavailable
        }
        try performMaintenance(retentionPolicy: retentionPolicy)
        return try loadCatalog().sorted { $0.importedAt > $1.importedAt }
    }

    /// Returns only a URL belonging to a validated catalog entry in app-private storage.
    func playbackURL(for id: UUID) throws -> URL {
        let entries = try loadCatalog()
        guard let entry = entries.first(where: { $0.id == id }) else {
            throw RecordingImportServiceError.recordingNotFound
        }
        let url = try recordingURL(for: entry)
        guard fileManager.fileExists(atPath: url.path) else {
            throw RecordingImportServiceError.recordingFileMissing
        }
        return url
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

    private func validateAudioPayload(_ audioFile: AVAudioFile) throws {
        let expectedFrameCount = audioFile.length
        let format = audioFile.processingFormat
        guard expectedFrameCount > 0,
              format.sampleRate.isFinite,
              format.sampleRate > 0,
              (1...2).contains(Int(format.channelCount)),
              let buffer = AVAudioPCMBuffer(
                pcmFormat: format,
                frameCapacity: 65_536
              ) else {
            throw RecordingImportServiceError.unreadableAudio
        }

        var decodedFrameCount: AVAudioFramePosition = 0
        while decodedFrameCount < expectedFrameCount {
            let remainingFrames = expectedFrameCount - decodedFrameCount
            let requestedFrames = AVAudioFrameCount(
                min(Int64(buffer.frameCapacity), remainingFrames)
            )
            let previousFramePosition = audioFile.framePosition
            do {
                try audioFile.read(into: buffer, frameCount: requestedFrames)
            } catch {
                throw RecordingImportServiceError.unreadableAudio
            }

            let nextFramePosition = audioFile.framePosition
            guard buffer.frameLength > 0,
                  nextFramePosition > previousFramePosition,
                  nextFramePosition <= expectedFrameCount else {
                throw RecordingImportServiceError.unreadableAudio
            }
            decodedFrameCount = nextFramePosition
        }

        guard decodedFrameCount == expectedFrameCount else {
            throw RecordingImportServiceError.unreadableAudio
        }
    }

    /// Fail before copying when the source plus a safety reserve cannot fit.
    /// The provider is injectable so low-storage behavior is deterministic in tests.
    private func ensureAvailableStorage(for sourceBytes: Int64) throws {
        let available: Int64
        if let availableStorageProvider {
            available = try availableStorageProvider()
        } else {
            let path: String
            if let storageRootURL {
                path = storageRootURL.path
            } else if let applicationSupport = fileManager.urls(
                for: .applicationSupportDirectory,
                in: .userDomainMask
            ).first {
                path = applicationSupport.path
            } else {
                throw RecordingImportServiceError.storageUnavailable
            }
            let attributes = try fileManager.attributesOfFileSystem(forPath: path)
            guard let value = attributes[.systemFreeSize] as? NSNumber else {
                throw RecordingImportServiceError.storageUnavailable
            }
            available = value.int64Value
        }

        let (required, overflow) = sourceBytes.addingReportingOverflow(minimumFreeStorageBytes)
        guard !overflow, available >= required else {
            throw RecordingImportServiceError.insufficientStorage(
                requiredBytes: overflow ? Int64.max : required,
                availableBytes: max(0, available)
            )
        }
    }

    private func applyCompleteFileProtection(to url: URL) throws {
        guard storageRootURL == nil else { return }
        try fileManager.setAttributes(
            [.protectionKey: FileProtectionType.complete],
            ofItemAtPath: url.path
        )
    }

    private func protectCatalogFile(_ url: URL) throws {
        try applyCompleteFileProtection(to: url)
    }

    private func performMaintenance(retentionPolicy: RecordingRetentionPolicy) throws {
        var entries = try loadCatalog()
        let now = Date()

        var retainedEntries: [ImportedRecording] = []
        for entry in entries {
            let url = try recordingURL(for: entry)
            let isExpired = retentionPolicy.hasExpired(importedAt: entry.importedAt, relativeTo: now)
            if isExpired {
                if fileManager.fileExists(atPath: url.path) {
                    try fileManager.removeItem(at: url)
                }
            } else if fileManager.fileExists(atPath: url.path) {
                retainedEntries.append(entry)
            }
        }

        if retainedEntries != entries {
            try saveCatalog(retainedEntries)
            entries = retainedEntries
        }

        // Imports are serialized by this actor. Anything left in staging after
        // process termination is an abandoned, incomplete copy and is safe to remove.
        try removeContents(of: privateDirectory(named: "Staging"))

        // Remove only UUID-named files with known audio extensions that are not
        // referenced by the validated catalog. Unknown files are left untouched.
        let knownPaths = Set(try entries.map { try recordingURL(for: $0).standardizedFileURL.path })
        let recordingsDirectory = try privateDirectory(named: "Recordings")
        let files = try fileManager.contentsOfDirectory(
            at: recordingsDirectory,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        )
        for file in files {
            let values = try file.resourceValues(forKeys: [.isRegularFileKey])
            guard values.isRegularFile == true,
                  UUID(uuidString: file.deletingPathExtension().lastPathComponent) != nil,
                  RecordingAudioContainer(rawValue: file.pathExtension.lowercased()) != nil,
                  !knownPaths.contains(file.standardizedFileURL.path) else {
                continue
            }
            try fileManager.removeItem(at: file)
        }
    }

    private func removeContents(of directory: URL) throws {
        let contents = try fileManager.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        )
        for item in contents {
            try fileManager.removeItem(at: item)
        }
    }

    private func privateDirectory(named name: String) throws -> URL {
        if let storageRootURL {
            let directory = storageRootURL.appendingPathComponent(name, isDirectory: true)
            try fileManager.createDirectory(
                at: directory,
                withIntermediateDirectories: true
            )
            return directory
        }

        guard let applicationSupport = fileManager.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first else {
            throw RecordingImportServiceError.storageUnavailable
        }

        var directory = applicationSupport.appendingPathComponent(
            "CallRecorder/\(name)",
            isDirectory: true
        )
        try fileManager.createDirectory(
            at: directory,
            withIntermediateDirectories: true
        )
        try fileManager.setAttributes(
            [.protectionKey: FileProtectionType.complete],
            ofItemAtPath: directory.path
        )
        var resourceValues = URLResourceValues()
        resourceValues.isExcludedFromBackup = true
        try directory.setResourceValues(resourceValues)
        return directory
    }

    private func catalogURL() throws -> URL {
        try privateDirectory(named: "Catalog")
            .appendingPathComponent("recordings.json")
    }

    private func catalogBackupURL() throws -> URL {
        try privateDirectory(named: "Catalog")
            .appendingPathComponent("recordings.json.backup")
    }

    private func decodeAndValidateCatalog(at url: URL) throws -> [ImportedRecording] {
        let data = try Data(contentsOf: url)
        let entries = try JSONDecoder().decode([ImportedRecording].self, from: data)
        try validateCatalog(entries)
        return entries
    }

    private func validateCatalog(_ entries: [ImportedRecording]) throws {
        var identifiers = Set<UUID>()
        for entry in entries {
            guard identifiers.insert(entry.id).inserted,
                  RecordingAudioContainer(rawValue: entry.fileExtension.lowercased()) != nil,
                  entry.fileExtension == entry.fileExtension.lowercased(),
                  entry.byteCount > 0,
                  entry.byteCount <= RecordingImportValidator.maximumFileSizeBytes,
                  entry.durationSeconds.isFinite,
                  entry.durationSeconds > 0,
                  entry.durationSeconds <= RecordingImportValidator.maximumDurationSeconds,
                  entry.importedAt.timeIntervalSince1970.isFinite,
                  entry.contentSHA256 == nil || (entry.contentSHA256?.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil) else {
                throw RecordingImportServiceError.catalogCorrupted
            }
        }
    }

    private func loadCatalog() throws -> [ImportedRecording] {
        let primary = try catalogURL()
        let backup = try catalogBackupURL()
        guard fileManager.fileExists(atPath: primary.path) else {
            if fileManager.fileExists(atPath: backup.path) {
                let recovered = try decodeAndValidateCatalog(at: backup)
                try JSONEncoder().encode(recovered).write(to: primary, options: .atomic)
                try protectCatalogFile(primary)
                return recovered
            }

            // A genuinely new install has no catalog and no managed media.
            // If media exists without either catalog copy, do not treat data loss
            // as an empty library: fail closed and preserve every file for recovery.
            let recordingsDirectory = try privateDirectory(named: "Recordings")
            let existingMedia = try fileManager.contentsOfDirectory(
                at: recordingsDirectory,
                includingPropertiesForKeys: nil,
                options: [.skipsHiddenFiles]
            )
            guard existingMedia.isEmpty else {
                throw RecordingImportServiceError.catalogCorrupted
            }
            return []
        }

        do {
            return try decodeAndValidateCatalog(at: primary)
        } catch {
            guard fileManager.fileExists(atPath: backup.path) else {
                throw RecordingImportServiceError.catalogCorrupted
            }
            let recovered = try decodeAndValidateCatalog(at: backup)
            try JSONEncoder().encode(recovered).write(to: primary, options: .atomic)
            try protectCatalogFile(primary)
            return recovered
        }
    }

    private func sha256(of url: URL) throws -> String {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var hasher = SHA256()
        while let chunk = try handle.read(upToCount: 1_048_576), !chunk.isEmpty {
            hasher.update(data: chunk)
        }
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }

    private func saveCatalog(_ entries: [ImportedRecording]) throws {
        try validateCatalog(entries)
        let data = try JSONEncoder().encode(entries)
        let primary = try catalogURL()
        let backup = try catalogBackupURL()

        if fileManager.fileExists(atPath: primary.path) {
            // Preserve the last known-good snapshot before atomically replacing it.
            let current = try decodeAndValidateCatalog(at: primary)
            let backupData = try JSONEncoder().encode(current)
            try backupData.write(to: backup, options: .atomic)
            try protectCatalogFile(backup)
        } else {
            // Seed recovery from the first committed catalog, not only later updates.
            try data.write(to: backup, options: .atomic)
            try protectCatalogFile(backup)
        }
        try data.write(to: primary, options: .atomic)
        try protectCatalogFile(primary)
    }

    private func recordingURL(for entry: ImportedRecording) throws -> URL {
        guard let container = RecordingAudioContainer(rawValue: entry.fileExtension),
              entry.fileExtension == entry.fileExtension.lowercased() else {
            throw RecordingImportServiceError.catalogCorrupted
        }
        return try privateDirectory(named: "Recordings")
            .appendingPathComponent(entry.id.uuidString)
            .appendingPathExtension(container.rawValue)
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

    /// AVAudioFile may synthesize silence for missing PCM frames in a truncated
    /// WAV. Validate RIFF's declared chunk boundaries against the physical file
    /// length before asking AVFoundation to decode it.
    static func validateDeclaredPayloadLength(
        at url: URL,
        container: RecordingAudioContainer
    ) throws {
        guard container == .wav else { return }

        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        guard let fileSize = (attributes[.size] as? NSNumber)?.uint64Value,
              fileSize >= 12 else {
            throw RecordingImportServiceError.unreadableAudio
        }

        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }

        func read(_ count: Int, at offset: UInt64) throws -> Data {
            try handle.seek(toOffset: offset)
            let data = try handle.read(upToCount: count) ?? Data()
            guard data.count == count else {
                throw RecordingImportServiceError.unreadableAudio
            }
            return data
        }

        func uint32LE(_ data: Data) -> UInt64 {
            UInt64(data[data.startIndex])
                | (UInt64(data[data.startIndex + 1]) << 8)
                | (UInt64(data[data.startIndex + 2]) << 16)
                | (UInt64(data[data.startIndex + 3]) << 24)
        }

        let header = try read(12, at: 0)
        guard String(decoding: header[0..<4], as: UTF8.self) == "RIFF",
              String(decoding: header[8..<12], as: UTF8.self) == "WAVE" else {
            throw RecordingImportServiceError.unreadableAudio
        }

        let riffEnd = 8 + uint32LE(header.subdata(in: 4..<8))
        guard riffEnd <= fileSize, riffEnd >= 12 else {
            throw RecordingImportServiceError.unreadableAudio
        }

        var offset: UInt64 = 12
        while offset + 8 <= riffEnd {
            let chunkHeader = try read(8, at: offset)
            let chunkID = String(decoding: chunkHeader[0..<4], as: UTF8.self)
            let chunkLength = uint32LE(chunkHeader.subdata(in: 4..<8))
            let chunkEnd = offset + 8 + chunkLength + (chunkLength & 1)

            guard chunkEnd >= offset, chunkEnd <= riffEnd, chunkEnd <= fileSize else {
                throw RecordingImportServiceError.unreadableAudio
            }

            if chunkID == "data" {
                guard chunkLength > 0 else {
                    throw RecordingImportServiceError.unreadableAudio
                }
                return
            }
            offset = chunkEnd
        }

        throw RecordingImportServiceError.unreadableAudio
    }
}
