import XCTest
@testable import CallRecorderCore

final class RecordingSessionOrchestratorTests: XCTestCase {
    func testVerifiedConsentGatesConnectionAndVerifiedArtifactCompletes() async throws {
        let orchestrator = makeOrchestrator(
            artifact: verifiedArtifact(),
            consentVerified: true
        )
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        try await orchestrator.startRecording(
            sessionID: sessionID,
            consentEvidence: makeConsentEvidence()
        )

        let recordingState = await orchestrator.state
        XCTAssertEqual(recordingState, .recording)

        let result = try await orchestrator.finish(sessionID: sessionID)
        let finalState = await orchestrator.state
        XCTAssertTrue(result.hasVerifiedTwoWayAudio)
        XCTAssertEqual(finalState, .completed)
    }

    func testIncompleteConsentEvidenceFailsClosed() async throws {
        let orchestrator = makeOrchestrator(artifact: verifiedArtifact(), consentVerified: true)
        let sessionID = UUID()
        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())

        var evidence = makeConsentEvidence()
        evidence = ConsentEvidence(
            reference: evidence.reference,
            policyVersion: evidence.policyVersion,
            participantIdentifiers: ["caller", "callee"],
            consentTimestamps: ["caller": Date(timeIntervalSince1970: 100)],
            disclosureTimestamp: Date(timeIntervalSince1970: 90)
        )

        do {
            try await orchestrator.startRecording(sessionID: sessionID, consentEvidence: evidence)
            XCTFail("Missing participant consent must fail closed")
        } catch {
            XCTAssertEqual(error as? RecordingSessionOrchestratorError, .consentEvidenceIncomplete)
        }

        let state = await orchestrator.state
        XCTAssertEqual(state, .failed)
    }

    func testTrustedVerifierCanRejectStructurallyValidEvidence() async throws {
        let orchestrator = makeOrchestrator(artifact: verifiedArtifact(), consentVerified: false)
        let sessionID = UUID()
        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())

        do {
            try await orchestrator.startRecording(
                sessionID: sessionID,
                consentEvidence: makeConsentEvidence()
            )
            XCTFail("Unverified consent evidence must not start capture")
        } catch {
            XCTAssertEqual(error as? RecordingSessionOrchestratorError, .consentEvidenceRejected)
        }

        let state = await orchestrator.state
        XCTAssertEqual(state, .failed)
    }

    func testAdapterCannotAdvertiseAnotherPathway() async throws {
        let orchestrator = RecordingSessionOrchestrator(
            adapter: StubAdapter(
                pathway: .conferenceBridge,
                advertisedPathway: .bluetoothAccessory,
                availability: .available,
                artifact: verifiedArtifact()
            ),
            consentVerifier: StubConsentVerifier(verified: true)
        )

        do {
            _ = try await orchestrator.prepare(sessionID: UUID(), context: makeContext())
            XCTFail("Mismatched adapter capability must fail closed")
        } catch {
            XCTAssertEqual(
                error as? RecordingSessionOrchestratorError,
                .adapterPathwayMismatch(
                    expected: .conferenceBridge,
                    actual: .bluetoothAccessory
                )
            )
        }

        let state = await orchestrator.state
        XCTAssertEqual(state, .failed)
    }

    func testInterruptionCanResumeBeforeFinalization() async throws {
        let orchestrator = makeOrchestrator(artifact: verifiedArtifact(), consentVerified: true)
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        try await orchestrator.startRecording(
            sessionID: sessionID,
            consentEvidence: makeConsentEvidence()
        )
        try await orchestrator.markInterrupted(sessionID: sessionID)

        let interruptedState = await orchestrator.state
        XCTAssertEqual(interruptedState, .interrupted)

        try await orchestrator.resume(sessionID: sessionID)
        let resumedState = await orchestrator.state
        XCTAssertEqual(resumedState, .recording)

        _ = try await orchestrator.finish(sessionID: sessionID)
        let finalState = await orchestrator.state
        XCTAssertEqual(finalState, .completed)
    }

    func testOneSidedOrMalformedArtifactFinishesAsDegraded() async throws {
        let malformedArtifact = RecordingArtifact(
            identifier: "one-sided",
            durationSeconds: .infinity,
            localAudioVerified: true,
            remoteAudioVerified: true
        )
        let orchestrator = makeOrchestrator(artifact: malformedArtifact, consentVerified: true)
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        try await orchestrator.startRecording(
            sessionID: sessionID,
            consentEvidence: makeConsentEvidence()
        )
        _ = try await orchestrator.finish(sessionID: sessionID)

        let finalState = await orchestrator.state
        XCTAssertEqual(finalState, .degraded)
    }

    func testUnavailablePathwayFailsBeforeAdapterPreparation() async throws {
        let orchestrator = RecordingSessionOrchestrator(
            adapter: StubAdapter(
                pathway: .conferenceBridge,
                advertisedPathway: .conferenceBridge,
                availability: .unavailable(reason: "carrier merge unsupported"),
                artifact: nil
            ),
            consentVerifier: StubConsentVerifier(verified: true)
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
        XCTAssertEqual(state, .failed)
    }

    private func makeOrchestrator(
        artifact: RecordingArtifact?,
        consentVerified: Bool
    ) -> RecordingSessionOrchestrator {
        RecordingSessionOrchestrator(
            adapter: StubAdapter(
                pathway: .conferenceBridge,
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: artifact
            ),
            consentVerifier: StubConsentVerifier(verified: consentVerified)
        )
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

    private func makeConsentEvidence() -> ConsentEvidence {
        let disclosure = Date(timeIntervalSince1970: 100)
        let consent = Date(timeIntervalSince1970: 110)
        return ConsentEvidence(
            reference: "audit-event-123",
            policyVersion: "consent-v1",
            participantIdentifiers: ["caller", "callee"],
            consentTimestamps: ["caller": consent, "callee": consent],
            disclosureTimestamp: disclosure
        )
    }

    private func verifiedArtifact() -> RecordingArtifact {
        RecordingArtifact(
            identifier: "verified",
            durationSeconds: 30,
            localAudioVerified: true,
            remoteAudioVerified: true
        )
    }
}

private struct StubAdapter: RecordingPathwayAdapter {
    let pathway: RecordingPathway
    let advertisedPathway: RecordingPathway
    let availability: PathwayAvailability
    let artifact: RecordingArtifact?

    func capability(for context: DeviceCompatibilityContext) async -> PathwayCapability {
        PathwayCapability(pathway: advertisedPathway, availability: availability)
    }

    func prepare(sessionID: UUID) async throws {}
    func connect(sessionID: UUID) async throws {}
    func startCapture(sessionID: UUID) async throws {}

    func finishCapture(sessionID: UUID) async throws -> RecordingArtifact {
        guard let artifact else { throw StubError.missingArtifact }
        return artifact
    }
}

private struct StubConsentVerifier: ConsentEvidenceVerifying {
    let verified: Bool

    func verify(_ evidence: ConsentEvidence, sessionID: UUID) async throws -> Bool {
        verified
    }
}

private enum StubError: Error {
    case missingArtifact
}
