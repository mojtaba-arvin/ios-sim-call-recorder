import XCTest
@testable import CallRecorderCore

final class RecordingPathwayRegistryTests: XCTestCase {
    func testEvaluatesAdaptersAndPreservesRegistrationOrder() async throws {
        let registry = try RecordingPathwayRegistry(adapters: [
            StubAdapter(pathway: .conferenceBridge),
            StubAdapter(pathway: .bluetoothAccessory)
        ])

        let results = await registry.capabilities(for: makeContext())

        XCTAssertEqual(results.map(\.pathway), [.conferenceBridge, .bluetoothAccessory])
        XCTAssertEqual(results.count, 2)
    }

    func testRejectsDuplicatePathwayAdapters() {
        XCTAssertThrowsError(
            try RecordingPathwayRegistry(adapters: [
                StubAdapter(pathway: .conferenceBridge),
                StubAdapter(pathway: .conferenceBridge)
            ])
        ) { error in
            XCTAssertEqual(
                error as? RecordingPathwayRegistryError,
                .duplicatePathway(.conferenceBridge)
            )
        }
    }

    private func makeContext() -> DeviceCompatibilityContext {
        DeviceCompatibilityContext(
            deviceModelIdentifier: "iPhone-test",
            operatingSystemVersion: "27.0",
            deviceRegionCode: "US",
            physicalTestCountryCode: "US",
            languageCode: "en",
            simConfiguration: .eSIMSingle,
            isRoaming: false,
            networkType: .cellular5G,
            wifiCallingEnabled: false,
            volteEnabled: true,
            callDirection: .outgoing,
            audioRoute: .receiver
        )
    }
}

private struct StubAdapter: RecordingPathwayAdapter {
    let pathway: RecordingPathway

    func capability(for context: DeviceCompatibilityContext) async -> PathwayCapability {
        PathwayCapability(pathway: pathway, availability: .available)
    }

    func prepare(sessionID: UUID) async throws {}
    func connect(sessionID: UUID) async throws {}
    func startCapture(sessionID: UUID) async throws {}

    func finishCapture(sessionID: UUID) async throws -> RecordingArtifact {
        RecordingArtifact(
            identifier: sessionID.uuidString,
            durationSeconds: 1,
            localAudioVerified: true,
            remoteAudioVerified: true
        )
    }
}
