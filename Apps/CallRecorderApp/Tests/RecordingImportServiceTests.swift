import AVFoundation
import XCTest
@testable import CallRecorder

final class RecordingImportServiceTests: XCTestCase {
    private var temporaryRoot: URL!
    private var catalogDirectory: URL!
    private var recordingsDirectory: URL!
    private var stagingDirectory: URL!

    override func setUpWithError() throws {
        try super.setUpWithError()
        temporaryRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent("CallRecorderTests-\(UUID().uuidString)", isDirectory: true)
        catalogDirectory = temporaryRoot.appendingPathComponent("Catalog", isDirectory: true)
        recordingsDirectory = temporaryRoot.appendingPathComponent("Recordings", isDirectory: true)
        stagingDirectory = temporaryRoot.appendingPathComponent("Staging", isDirectory: true)
        try FileManager.default.createDirectory(at: catalogDirectory, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: recordingsDirectory, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: stagingDirectory, withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws {
        if let temporaryRoot {
            try? FileManager.default.removeItem(at: temporaryRoot)
        }
        try super.tearDownWithError()
    }

    func testFirstImportSeedsKnownGoodBackup() async throws {
        let sourceURL = temporaryRoot.appendingPathComponent("sample.wav")
        try writeValidWAV(to: sourceURL)

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        let imported = try await service.importRecording(from: sourceURL, source: .filesApp)
        XCTAssertGreaterThanOrEqual(imported.durationSeconds, 1.0)

        let primary = try Data(contentsOf: catalogDirectory.appendingPathComponent("recordings.json"))
        let backup = try Data(contentsOf: catalogDirectory.appendingPathComponent("recordings.json.backup"))
        XCTAssertEqual(
            try JSONDecoder().decode([ImportedRecording].self, from: primary),
            try JSONDecoder().decode([ImportedRecording].self, from: backup)
        )
        XCTAssertFalse(String(decoding: primary, as: UTF8.self).contains("sample.wav"))
        let storedFiles = try FileManager.default.contentsOfDirectory(
            at: recordingsDirectory,
            includingPropertiesForKeys: nil
        )
        XCTAssertEqual(storedFiles.count, 1)
        XCTAssertEqual(storedFiles[0].deletingPathExtension().lastPathComponent, imported.id.uuidString)
    }

    func testTruncatedAudioPayloadIsRejectedAndStagingIsCleaned() async throws {
        let validURL = temporaryRoot.appendingPathComponent("valid.wav")
        try writeValidWAV(to: validURL)
        var truncatedData = try Data(contentsOf: validURL)
        truncatedData.removeLast(1_024)
        let truncatedURL = temporaryRoot.appendingPathComponent("truncated.wav")
        try truncatedData.write(to: truncatedURL)

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        do {
            _ = try await service.importRecording(from: truncatedURL, source: .filesApp)
            XCTFail("A truncated WAV payload must not be imported")
        } catch let error as RecordingImportServiceError {
            guard case .unreadableAudio = error else {
                return XCTFail("Expected unreadableAudio, got \(error)")
            }
        }

        let stagedFiles = try FileManager.default.contentsOfDirectory(
            at: stagingDirectory,
            includingPropertiesForKeys: nil
        )
        let importedFiles = try FileManager.default.contentsOfDirectory(
            at: recordingsDirectory,
            includingPropertiesForKeys: nil
        )
        XCTAssertTrue(stagedFiles.isEmpty)
        XCTAssertTrue(importedFiles.isEmpty)
    }

    func testFilenameContainerMismatchIsRejectedBeforeCommit() async throws {
        let sourceURL = temporaryRoot.appendingPathComponent("misleading.m4a")
        try writeValidWAV(to: sourceURL)

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        do {
            _ = try await service.importRecording(from: sourceURL, source: .filesApp)
            XCTFail("A WAV payload named as M4A must be rejected")
        } catch let error as RecordingImportServiceError {
            guard case .validation(.extensionContainerMismatch) = error else {
                return XCTFail("Expected extensionContainerMismatch, got \(error)")
            }
        }

        let stagedFiles = try FileManager.default.contentsOfDirectory(
            at: stagingDirectory,
            includingPropertiesForKeys: nil
        )
        let importedFiles = try FileManager.default.contentsOfDirectory(
            at: recordingsDirectory,
            includingPropertiesForKeys: nil
        )
        XCTAssertTrue(stagedFiles.isEmpty)
        XCTAssertTrue(importedFiles.isEmpty)
    }

    func testWAVDeclaredDataChunkBeyondPhysicalFileIsRejected() async throws {
        let validURL = temporaryRoot.appendingPathComponent("valid-header.wav")
        try writeValidWAV(to: validURL)
        var data = try Data(contentsOf: validURL)
        let dataChunk = try XCTUnwrap(data.range(of: Data("data".utf8)))
        let lengthOffset = dataChunk.upperBound
        data.replaceSubrange(lengthOffset..<(lengthOffset + 4), with: [0xFF, 0xFF, 0xFF, 0x7F])
        let malformedURL = temporaryRoot.appendingPathComponent("invalid-chunk-length.wav")
        try data.write(to: malformedURL)

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        do {
            _ = try await service.importRecording(from: malformedURL, source: .filesApp)
            XCTFail("A WAV data chunk extending beyond the physical file must be rejected")
        } catch let error as RecordingImportServiceError {
            guard case .unreadableAudio = error else {
                return XCTFail("Expected unreadableAudio, got \(error)")
            }
        }

        let stagedFiles = try FileManager.default.contentsOfDirectory(
            at: stagingDirectory,
            includingPropertiesForKeys: nil
        )
        let importedFiles = try FileManager.default.contentsOfDirectory(
            at: recordingsDirectory,
            includingPropertiesForKeys: nil
        )
        XCTAssertTrue(stagedFiles.isEmpty)
        XCTAssertTrue(importedFiles.isEmpty)
    }

    func testLongAudioIsDecodedInBoundedChunks() async throws {
        let sourceURL = temporaryRoot.appendingPathComponent("long.wav")
        try writeValidWAV(to: sourceURL, durationSeconds: 60)

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        let imported = try await service.importRecording(from: sourceURL, source: .filesApp)

        XCTAssertEqual(imported.durationSeconds, 60, accuracy: 0.01)
        let playbackURL = try await service.playbackURL(for: imported.id)
        XCTAssertTrue(FileManager.default.fileExists(atPath: playbackURL.path))
    }

    func testCorruptPrimaryRestoresValidatedBackup() async throws {
        let entry = makeEntry()
        try writeCatalog([entry], named: "recordings.json.backup")
        try Data("{broken".utf8).write(to: catalogDirectory.appendingPathComponent("recordings.json"))
        try Data("audio".utf8).write(to: mediaURL(for: entry))

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        let result = try await service.recordings()

        XCTAssertEqual(result, [entry])
        let restored = try JSONDecoder().decode(
            [ImportedRecording].self,
            from: Data(contentsOf: catalogDirectory.appendingPathComponent("recordings.json"))
        )
        XCTAssertEqual(restored, [entry])
    }

    func testInvalidPrimaryAndBackupFailClosedWithoutDeletingMedia() async throws {
        let entry = makeEntry()
        let media = mediaURL(for: entry)
        try Data("audio".utf8).write(to: media)
        try Data("{bad-primary".utf8).write(to: catalogDirectory.appendingPathComponent("recordings.json"))
        try Data("{bad-backup".utf8).write(to: catalogDirectory.appendingPathComponent("recordings.json.backup"))

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        do {
            _ = try await service.recordings()
            XCTFail("Expected corrupt catalog to fail closed")
        } catch {
            XCTAssertTrue(FileManager.default.fileExists(atPath: media.path))
        }
    }

    func testInvalidCatalogExtensionFailsClosedBeforePathConstruction() async throws {
        let entry = ImportedRecording(
            id: UUID(),
            fileExtension: "../../outside",
            byteCount: 5,
            durationSeconds: 1,
            importedAt: Date()
        )
        try writeCatalog([entry], named: "recordings.json")
        let service = RecordingImportService(storageRootURL: temporaryRoot)

        do {
            _ = try await service.recordings()
            XCTFail("Expected invalid catalog entry to be rejected")
        } catch {
            XCTAssertTrue(FileManager.default.fileExists(atPath: catalogDirectory.appendingPathComponent("recordings.json").path))
        }
    }

    func testRetentionRemovesExpiredMediaAndCatalogEntry() async throws {
        let entry = makeEntry(importedAt: Date(timeIntervalSince1970: 1))
        let media = mediaURL(for: entry)
        try Data("audio".utf8).write(to: media)
        try writeCatalog([entry], named: "recordings.json")

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        let result = try await service.recordings(retentionDays: 30)

        XCTAssertTrue(result.isEmpty)
        XCTAssertFalse(FileManager.default.fileExists(atPath: media.path))
    }

    func testMaintenanceRemovesOnlyKnownOrphansAndAbandonedStaging() async throws {
        let entry = makeEntry()
        try Data("referenced".utf8).write(to: mediaURL(for: entry))
        try writeCatalog([entry], named: "recordings.json")

        let orphan = recordingsDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("m4a")
        let unknown = recordingsDirectory.appendingPathComponent("keep-me.txt")
        let directoryNamedLikeAudio = recordingsDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("m4a")
        let staged = stagingDirectory.appendingPathComponent("partial-import")
        try Data("orphan".utf8).write(to: orphan)
        try Data("unknown".utf8).write(to: unknown)
        try FileManager.default.createDirectory(at: directoryNamedLikeAudio, withIntermediateDirectories: false)
        try Data("partial".utf8).write(to: staged)

        let service = RecordingImportService(storageRootURL: temporaryRoot)
        _ = try await service.recordings()

        XCTAssertFalse(FileManager.default.fileExists(atPath: orphan.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: unknown.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directoryNamedLikeAudio.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: staged.path))
    }

    private func writeValidWAV(to url: URL, durationSeconds: Int = 1) throws {
        let format = try XCTUnwrap(AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: 44_100,
            channels: 1,
            interleaved: false
        ))

        // Keep the writer's lifetime inside this helper so AVAudioFile is
        // deallocated and its WAV header is finalized before the importer reads it.
        do {
            let audioFile = try AVAudioFile(
                forWriting: url,
                settings: format.settings,
                commonFormat: .pcmFormatFloat32,
                interleaved: false
            )
            let buffer = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 44_100))
            for _ in 0..<durationSeconds {
                buffer.frameLength = 44_100
                try audioFile.write(from: buffer)
            }
        }

        let decodedFile = try AVAudioFile(forReading: url)
        let decodedDuration = Double(decodedFile.length) / decodedFile.processingFormat.sampleRate
        XCTAssertGreaterThanOrEqual(
            decodedDuration,
            Double(durationSeconds),
            "The generated fixture must contain the requested decodable duration"
        )
    }

    private func makeEntry(importedAt: Date = Date()) -> ImportedRecording {
        ImportedRecording(
            id: UUID(),
            fileExtension: "m4a",
            byteCount: 5,
            durationSeconds: 1,
            importedAt: importedAt
        )
    }

    private func mediaURL(for entry: ImportedRecording) -> URL {
        recordingsDirectory
            .appendingPathComponent(entry.id.uuidString)
            .appendingPathExtension(entry.fileExtension)
    }

    private func writeCatalog(_ entries: [ImportedRecording], named name: String) throws {
        let data = try JSONEncoder().encode(entries)
        try data.write(to: catalogDirectory.appendingPathComponent(name))
    }
}
