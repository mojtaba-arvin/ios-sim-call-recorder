import Foundation

public enum RecordingSessionOrchestratorError: Error, Equatable, Sendable {
    case sessionAlreadyActive
    case noActiveSession
    case sessionMismatch
    case consentEvidenceRequired
    case pathwayUnavailable(PathwayAvailability)
    case invalidState(RecordingSessionState)
}

/// Coordinates one adapter-backed session. Instantiate per recording session;
/// UI and provider-specific code remain outside this actor.
public actor RecordingSessionOrchestrator {
    private let adapter: any RecordingPathwayAdapter
    private var machine = RecordingSessionStateMachine()
    private var activeSessionID: UUID?

    public init(adapter: any RecordingPathwayAdapter) {
        self.adapter = adapter
    }

    public var state: RecordingSessionState {
        machine.state
    }

    /// Prepares a route and returns its capability decision for user-facing UX.
    /// User-action pathways are allowed; unavailable or hardware-missing paths fail closed.
    public func prepare(
        sessionID: UUID,
        context: DeviceCompatibilityContext
    ) async throws -> PathwayCapability {
        guard activeSessionID == nil, machine.state == .idle else {
            throw RecordingSessionOrchestratorError.sessionAlreadyActive
        }

        let decision = await adapter.capability(for: context)
        switch decision.availability {
        case .available, .requiresUserAction:
            break
        case .unavailable, .requiresExternalHardware, .experimental:
            throw RecordingSessionOrchestratorError.pathwayUnavailable(decision.availability)
        }

        try machine.transition(to: .preparing)
        activeSessionID = sessionID
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

    /// A non-empty evidence reference is required before the adapter is connected.
    public func startRecording(
        sessionID: UUID,
        consentEvidenceReference: String
    ) async throws {
        try validate(sessionID: sessionID)
        guard !consentEvidenceReference.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw RecordingSessionOrchestratorError.consentEvidenceRequired
        }
        guard machine.state == .awaitingConsent else {
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

    /// Finalization is not marked successful unless both audio directions
    /// were independently verified by the pathway adapter.
    public func finish(sessionID: UUID) async throws -> RecordingArtifact {
        try validate(sessionID: sessionID)
        guard [.recording, .interrupted, .degraded].contains(machine.state) else {
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
