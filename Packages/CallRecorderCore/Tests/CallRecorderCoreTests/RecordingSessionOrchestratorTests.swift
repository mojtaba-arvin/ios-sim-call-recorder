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

        let evidence = ConsentEvidence(
            reference: "audit-event-123",
            policyVersion: "consent-v1",
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

    func testPrepareFailureCancelsPartiallyPreparedAdapter() async throws {
        let probe = CancellationProbe()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: nil,
                cancellationProbe: probe,
                prepareFails: true
            ),
            consentVerifier: StubConsentVerifier(verified: true)
        )

        do {
            _ = try await orchestrator.prepare(sessionID: UUID(), context: makeContext())
            XCTFail("A failed adapter preparation must fail the session")
        } catch {
            XCTAssertTrue(error is StubError)
        }

        let wasCancelled = await probe.wasCancelled
        let state = await orchestrator.state
        XCTAssertTrue(wasCancelled)
        XCTAssertEqual(state, .failed)
    }

    func testConsentRejectionCancelsPreparedAdapterResources() async throws {
        let probe = CancellationProbe()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: nil,
                cancellationProbe: probe
            ),
            consentVerifier: StubConsentVerifier(verified: false)
        )
        let sessionID = UUID()
        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())

        do {
            try await orchestrator.startRecording(
                sessionID: sessionID,
                consentEvidence: makeConsentEvidence()
            )
            XCTFail("Rejected consent must fail closed")
        } catch {
            XCTAssertEqual(error as? RecordingSessionOrchestratorError, .consentEvidenceRejected)
        }

        let wasCancelled = await probe.wasCancelled
        let state = await orchestrator.state
        XCTAssertTrue(wasCancelled)
        XCTAssertEqual(state, .failed)
    }

    func testAdapterConnectFailureCancelsPartiallyAllocatedResources() async throws {
        let probe = CancellationProbe()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: nil,
                cancellationProbe: probe,
                connectFails: true
            ),
            consentVerifier: StubConsentVerifier(verified: true)
        )
        let sessionID = UUID()
        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())

        do {
            try await orchestrator.startRecording(
                sessionID: sessionID,
                consentEvidence: makeConsentEvidence()
            )
            XCTFail("Adapter connect failure must fail the session")
        } catch {
            XCTAssertTrue(error is StubError)
        }

        let wasCancelled = await probe.wasCancelled
        let state = await orchestrator.state
        XCTAssertTrue(wasCancelled)
        XCTAssertEqual(state, .failed)
    }

    func testAdapterStartFailureCancelsPartiallyConnectedResources() async throws {
        let probe = CancellationProbe()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: nil,
                cancellationProbe: probe,
                startFails: true
            ),
            consentVerifier: StubConsentVerifier(verified: true)
        )
        let sessionID = UUID()
        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())

        do {
            try await orchestrator.startRecording(
                sessionID: sessionID,
                consentEvidence: makeConsentEvidence()
            )
            XCTFail("Adapter start failure must fail the session")
        } catch {
            XCTAssertTrue(error is StubError)
        }

        let wasCancelled = await probe.wasCancelled
        let state = await orchestrator.state
        XCTAssertTrue(wasCancelled)
        XCTAssertEqual(state, .failed)
    }

    func testFinalizationFailureCancelsRemainingAdapterResources() async throws {
        let probe = CancellationProbe()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: nil,
                cancellationProbe: probe,
                finishFails: true
            ),
            consentVerifier: StubConsentVerifier(verified: true)
        )
        let sessionID = UUID()
        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        try await orchestrator.startRecording(
            sessionID: sessionID,
            consentEvidence: makeConsentEvidence()
        )

        do {
            _ = try await orchestrator.finish(sessionID: sessionID)
            XCTFail("A failed finalization must not be reported as completed")
        } catch {
            XCTAssertTrue(error is StubError)
        }

        let wasCancelled = await probe.wasCancelled
        let state = await orchestrator.state
        XCTAssertTrue(wasCancelled)
        XCTAssertEqual(state, .failed)
    }

    func testAdapterCannotAdvertiseAnotherPathway() async throws {
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
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

    func testCancelFromRecordingStopsAdapterAndIsTerminal() async throws {
        let probe = CancellationProbe()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: verifiedArtifact(),
                cancellationProbe: probe
            ),
            consentVerifier: StubConsentVerifier(verified: true)
        )
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        try await orchestrator.startRecording(
            sessionID: sessionID,
            consentEvidence: makeConsentEvidence()
        )
        try await orchestrator.cancel(sessionID: sessionID)

        let wasCancelled = await probe.wasCancelled
        let finalState = await orchestrator.state
        XCTAssertTrue(wasCancelled)
        XCTAssertEqual(finalState, .cancelled)

        do {
            _ = try await orchestrator.finish(sessionID: sessionID)
            XCTFail("A cancelled session must not be finalized")
        } catch {
            XCTAssertEqual(error as? RecordingSessionOrchestratorError, .noActiveSession)
        }
    }

    func testCancelBeforeConsentPreventsRecordingFromStarting() async throws {
        let probe = CancellationProbe()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: verifiedArtifact(),
                cancellationProbe: probe
            ),
            consentVerifier: StubConsentVerifier(verified: true)
        )
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        try await orchestrator.cancel(sessionID: sessionID)

        do {
            try await orchestrator.startRecording(
                sessionID: sessionID,
                consentEvidence: makeConsentEvidence()
            )
            XCTFail("A cancelled session must not start recording")
        } catch {
            XCTAssertEqual(error as? RecordingSessionOrchestratorError, .noActiveSession)
        }

        let finalState = await orchestrator.state
        XCTAssertEqual(finalState, .cancelled)
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
            adapter: makeAdapter(
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

    func testCancellationDuringAdapterStartPreventsLateRecordingTransition() async throws {
        let adapter = GatedCancellationAdapter()
        let orchestrator = RecordingSessionOrchestrator(
            adapter: adapter,
            consentVerifier: StubConsentVerifier(verified: true)
        )
        let sessionID = UUID()

        _ = try await orchestrator.prepare(sessionID: sessionID, context: makeContext())
        let startTask = Task {
            try await orchestrator.startRecording(
                sessionID: sessionID,
                consentEvidence: makeConsentEvidence()
            )
        }
        await adapter.waitUntilStartCaptureIsSuspended()

        try await orchestrator.cancel(sessionID: sessionID)

        do {
            try await startTask.value
            XCTFail("A cancelled adapter start must not transition to recording")
        } catch {
            XCTAssertEqual(error as? RecordingSessionOrchestratorError, .sessionCancelled)
        }

        let state = await orchestrator.state
        let captureStarted = await adapter.captureStarted
        XCTAssertEqual(state, .cancelled)
        XCTAssertFalse(captureStarted)
    }

    private func makeOrchestrator(
        artifact: RecordingArtifact?,
        consentVerified: Bool
    ) -> RecordingSessionOrchestrator {
        RecordingSessionOrchestrator(
            adapter: makeAdapter(
                advertisedPathway: .conferenceBridge,
                availability: .available,
                artifact: artifact
            ),
            consentVerifier: StubConsentVerifier(verified: consentVerified)
        )
    }

    private func makeAdapter(
        advertisedPathway: RecordingPathway,
        availability: PathwayAvailability,
        artifact: RecordingArtifact?,
        cancellationProbe: CancellationProbe? = nil,
        prepareFails: Bool = false,
        connectFails: Bool = false,
        startFails: Bool = false,
        finishFails: Bool = false
    ) -> StubAdapter {
        StubAdapter(
            pathway: .conferenceBridge,
            advertisedPathway: advertisedPathway,
            availability: availability,
            artifact: artifact,
            cancellationProbe: cancellationProbe,
            prepareFails: prepareFails,
            connectFails: connectFails,
            startFails: startFails,
            finishFails: finishFails
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
    let cancellationProbe: CancellationProbe?
    let prepareFails: Bool
    let connectFails: Bool
    let startFails: Bool
    let finishFails: Bool

    func capability(for context: DeviceCompatibilityContext) async -> PathwayCapability {
        PathwayCapability(pathway: advertisedPathway, availability: availability)
    }

    func prepare(sessionID: UUID) async throws {
        if prepareFails { throw StubError.prepareFailed }
    }
    func connect(sessionID: UUID) async throws {
        if connectFails { throw StubError.connectFailed }
    }
    func startCapture(sessionID: UUID) async throws {
        if startFails { throw StubError.startFailed }
    }

    func finishCapture(sessionID: UUID) async throws -> RecordingArtifact {
        if finishFails { throw StubError.finishFailed }
        guard let artifact else { throw StubError.missingArtifact }
        return artifact
    }

    func cancel(sessionID: UUID) async throws {
        await cancellationProbe?.markCancelled()
    }
}

private actor CancellationProbe {
    private(set) var wasCancelled = false

    func markCancelled() {
        wasCancelled = true
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
    case prepareFailed
    case connectFailed
    case startFailed
    case finishFailed
}

private actor GatedCancellationAdapter: RecordingPathwayAdapter {
    let pathway: RecordingPathway = .conferenceBridge
    private var startContinuation: CheckedContinuation<Void, Error>?
    private var enteredContinuation: CheckedContinuation<Void, Never>?
    private(set) var captureStarted = false

    func capability(for context: DeviceCompatibilityContext) async -> PathwayCapability {
        PathwayCapability(pathway: pathway, availability: .available)
    }

    func prepare(sessionID: UUID) async throws {}
    func connect(sessionID: UUID) async throws {}

    func startCapture(sessionID: UUID) async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            startContinuation = continuation
            enteredContinuation?.resume()
            enteredContinuation = nil
        }
        captureStarted = true
    }

    func finishCapture(sessionID: UUID) async throws -> RecordingArtifact {
        RecordingArtifact(
            identifier: "gated",
            durationSeconds: 1,
            localAudioVerified: true,
            remoteAudioVerified: true
        )
    }

    func cancel(sessionID: UUID) async throws {
        startContinuation?.resume(throwing: GatedAdapterError.cancelled)
        startContinuation = nil
    }

    func waitUntilStartCaptureIsSuspended() async {
        if startContinuation != nil { return }
        await withCheckedContinuation { continuation in
            enteredContinuation = continuation
        }
    }
}

private enum GatedAdapterError: Error {
    case cancelled
}
