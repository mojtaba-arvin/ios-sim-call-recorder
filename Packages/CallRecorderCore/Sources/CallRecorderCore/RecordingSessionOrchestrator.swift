import Foundation

public enum RecordingSessionOrchestratorError: Error, Equatable, Sendable {
    case sessionAlreadyActive
    case noActiveSession
    case sessionMismatch
    case consentEvidenceIncomplete
    case consentEvidenceRejected
    case pathwayUnavailable(PathwayAvailability)
    case adapterPathwayMismatch(expected: RecordingPathway, actual: RecordingPathway)
    case invalidState(RecordingSessionState)
}

/// Coordinates one adapter-backed session. Instantiate per recording session;
/// UI, provider-specific code and authoritative consent storage remain outside.
public actor RecordingSessionOrchestrator {
    private let adapter: any RecordingPathwayAdapter
    private let consentVerifier: any ConsentEvidenceVerifying
    private var machine = RecordingSessionStateMachine()
    private var activeSessionID: UUID?

    public init(
        adapter: any RecordingPathwayAdapter,
        consentVerifier: any ConsentEvidenceVerifying
    ) {
        self.adapter = adapter
        self.consentVerifier = consentVerifier
    }

    public var state: RecordingSessionState {
        machine.state
    }

    /// Reserves the actor's session before the first suspension point so
    /// concurrent prepare calls cannot race capability discovery.
    public func prepare(
        sessionID: UUID,
        context: DeviceCompatibilityContext
    ) async throws -> PathwayCapability {
        guard activeSessionID == nil, machine.state == .idle else {
            throw RecordingSessionOrchestratorError.sessionAlreadyActive
        }

        try machine.transition(to: .preparing)
        activeSessionID = sessionID

        let decision = await adapter.capability(for: context)
        guard decision.pathway == adapter.pathway else {
            try? machine.transition(to: .failed)
            activeSessionID = nil
            throw RecordingSessionOrchestratorError.adapterPathwayMismatch(
                expected: adapter.pathway,
                actual: decision.pathway
            )
        }

        switch decision.availability {
        case .available, .requiresUserAction:
            break
        case .unavailable, .requiresExternalHardware, .experimental:
            try? machine.transition(to: .failed)
            activeSessionID = nil
            throw RecordingSessionOrchestratorError.pathwayUnavailable(decision.availability)
        }

        do {
            try await adapter.prepare(sessionID: sessionID)
            try machine.transition(to: .awaitingConsent)
            return decision
        } catch {
            try? machine.transition(to: .failed)
            activeSessionID = nil
            throw error
        }
    }

    /// The trusted verifier must validate persisted evidence before the
    /// adapter is allowed to connect or start capture.
    public func startRecording(
        sessionID: UUID,
        consentEvidence: ConsentEvidence
    ) async throws {
        try validate(sessionID: sessionID)
        guard machine.state == .awaitingConsent else {
            throw RecordingSessionOrchestratorError.invalidState(machine.state)
        }

        // Reserve the transition before awaiting the verifier to prevent
        // concurrent start calls from both attempting to connect.
        try machine.transition(to: .connecting)
        do {
            guard consentEvidence.isStructurallyComplete else {
                throw RecordingSessionOrchestratorError.consentEvidenceIncomplete
            }
            guard try await consentVerifier.verify(consentEvidence, sessionID: sessionID) else {
                throw RecordingSessionOrchestratorError.consentEvidenceRejected
            }

            try await adapter.connect(sessionID: sessionID)
            try await adapter.startCapture(sessionID: sessionID)
            try machine.transition(to: .recording)
        } catch {
            try? machine.transition(to: .failed)
            activeSessionID = nil
            throw error
        }
    }

    public func markInterrupted(sessionID: UUID) throws {
        try validate(sessionID: sessionID)
        guard machine.state == .recording else {
            throw RecordingSessionOrchestratorError.invalidState(machine.state)
        }
        try machine.transition(to: .interrupted)
    }

    public func resume(sessionID: UUID) async throws {
        try validate(sessionID: sessionID)
        guard machine.state == .interrupted else {
            throw RecordingSessionOrchestratorError.invalidState(machine.state)
        }

        try machine.transition(to: .connecting)
        do {
            try await adapter.connect(sessionID: sessionID)
            try await adapter.startCapture(sessionID: sessionID)
            try machine.transition(to: .recording)
        } catch {
            try? machine.transition(to: .failed)
            activeSessionID = nil
            throw error
        }
    }

    /// A malformed or one-sided artifact is retained as degraded, never
    /// promoted to completed. Final outcomes are terminal for this session.
    public func finish(sessionID: UUID) async throws -> RecordingArtifact {
        try validate(sessionID: sessionID)
        guard [.recording, .interrupted].contains(machine.state) else {
            throw RecordingSessionOrchestratorError.invalidState(machine.state)
        }

        try machine.transition(to: .finalizing)
        do {
            let artifact = try await adapter.finishCapture(sessionID: sessionID)
            try machine.transition(to: artifact.hasVerifiedTwoWayAudio ? .completed : .degraded)
            activeSessionID = nil
            return artifact
        } catch {
            try? machine.transition(to: .failed)
            activeSessionID = nil
            throw error
        }
    }

    private func validate(sessionID: UUID) throws {
        guard let activeSessionID else {
            throw RecordingSessionOrchestratorError.noActiveSession
        }
        guard activeSessionID == sessionID else {
            throw RecordingSessionOrchestratorError.sessionMismatch
        }
    }
}
