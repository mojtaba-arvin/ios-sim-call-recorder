import XCTest
@testable import CallRecorderCore

final class RecordingSessionOrchestratorTests: XCTestCase {
    func testConsentGatesConnectionAndVerifiedArtifactCompletes() async throws {
        let artifact = RecordingArtifact(
            identifier: "verified",
            durationSeconds: 30,
            localAudioVerified: true,
            remoteAudioVerified: true
        )
        let orchestrator = RecordingSessionOrchestrator(
            adapter: StubAdapter(availability: .available, artifact: artifact)
        )
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        do {
            try await orchestrator.startRecording(
                sessionID: sessionID,
                consentEvidenceReference: "  "
            )
            XCTFail("Empty consent evidence must not start capture")
        } catch {
            XCTAssertEqual(
                error as? RecordingSessionOrchestratorError,
                .consentEvidenceRequired
            )
        }

        let waitingState = await orchestrator.state
        XCTAssertEqual(waitingState, .awaitingConsent)

        try await orchestrator.startRecording(
            sessionID: sessionID,
            consentEvidenceReference: "consent-event-123"
        )
        let recordingState = await orchestrator.state
        XCTAssertEqual(recordingState, .recording)

        let result = try await orchestrator.finish(sessionID: sessionID)
        let finalState = await orchestrator.state
        XCTAssertTrue(result.hasVerifiedTwoWayAudio)
        XCTAssertEqual(finalState, .completed)
    }

    func testOneSidedArtifactFinishesAsDegraded() async throws {
        let artifact = RecordingArtifact(
            identifier: "one-sided",
            durationSeconds: 30,
            localAudioVerified: true,
            remoteAudioVerified: false
        )
        let orchestrator = RecordingSessionOrchestrator(
            adapter: StubAdapter(availability: .available, artifact: artifact)
        )
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        try await orchestrator.startRecording(
            sessionID: sessionID,
            consentEvidenceReference: "consent-event-456"
        )
        _ = try await orchestrator.finish(sessionID: sessionID)

        let finalState = await orchestrator.state
        XCTAssertEqual(finalState, .degraded)
    }

    func testUnavailablePathwayFailsBeforePreparation() async throws {
        let orchestrator = RecordingSessionOrchestrator(
            adapter: StubAdapter(
                availability: .unavailable(reason: "carrier merge unsupported"),
                artifact: nil
            )
        )

        do {
            _ = try await orchestrator.prepare(sessionID: UUID(), context: makeContext())
            XCTFail("Unavailable pathway must fail closed")
        } catch {
            XCTAssertEqual(
                error as? RecordingSessionOrchestratorError,
                .pathwayUnavailable(.unavailable(reason: "carrier merge unsupported"))
            )
        }

        let state = await orchestrator.state
        XCTAssertEqual(state, .idle)
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
    let pathway: RecordingPathway = .conferenceBridge
    let availability: PathwayAvailability
    let artifact: RecordingArtifact?

    func capability(for context: DeviceCompatibilityContext) async -> PathwayCapability {
        PathwayCapability(pathway: pathway, availability: availability)
    }

    func prepare(sessionID: UUID) async throws {}
    func connect(sessionID: UUID) async throws {}
    func startCapture(sessionID: UUID) async throws {}

    func finishCapture(sessionID: UUID) async throws -> RecordingArtifact {
        guard let artifact else {
            throw StubError.missingArtifact
        }
        return artifact
    }
}

private enum StubError: Error {
    case missingArtifact
}
