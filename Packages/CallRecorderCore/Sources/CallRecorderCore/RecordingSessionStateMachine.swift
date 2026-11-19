public enum RecordingSessionState: Hashable, Sendable {
    case idle
    case preparing
    case awaitingConsent
    case connecting
    case recording
    case cancelling
    case finalizing
    case completed
    case failed
    case cancelled
    case interrupted
    case degraded
}

public struct RecordingSessionStateMachine: Sendable {
    public private(set) var state: RecordingSessionState = .idle

    public init() {}

    public mutating func transition(to next: RecordingSessionState) throws {
        guard Self.allowedTransitions(from: state).contains(next) else {
            throw RecordingSessionTransitionError.invalidTransition(from: state, to: next)
        }
        state = next
    }

    private static func allowedTransitions(
        from state: RecordingSessionState
    ) -> Set<RecordingSessionState> {
        switch state {
        case .idle:
            return [.preparing]
        case .preparing:
            return [.awaitingConsent, .failed]
        case .awaitingConsent:
            return [.connecting, .cancelling, .failed]
        case .connecting:
            return [.recording, .cancelling, .failed, .interrupted, .degraded]
        case .recording:
            return [.finalizing, .cancelling, .failed, .interrupted, .degraded]
        case .interrupted:
            return [.connecting, .cancelling, .finalizing, .failed]
        case .cancelling:
            return [.cancelled, .failed]
        case .degraded:
            return []
        case .finalizing:
            return [.completed, .degraded, .failed]
        case .completed, .failed, .cancelled:
            return []
        }
    }
}

public enum RecordingSessionTransitionError: Error, Equatable, Sendable {
    case invalidTransition(from: RecordingSessionState, to: RecordingSessionState)
}
