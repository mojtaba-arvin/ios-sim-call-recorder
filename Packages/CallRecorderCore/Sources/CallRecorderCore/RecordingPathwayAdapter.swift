import Foundation

/// Pathway-specific capture implementations live outside the core package.
/// This contract does not imply access to native Phone audio.
public protocol RecordingPathwayAdapter: Sendable {
    var pathway: RecordingPathway { get }

    func capability(for context: DeviceCompatibilityContext) async -> PathwayCapability
    func prepare(sessionID: UUID) async throws
    func connect(sessionID: UUID) async throws
    func startCapture(sessionID: UUID) async throws
    func finishCapture(sessionID: UUID) async throws -> RecordingArtifact

    /// Stops any partially or fully prepared provider/device resources.
    /// Implementations must be idempotent and coordinate with in-flight
    /// connect/start operations so a late completion cannot restart capture.
    func cancel(sessionID: UUID) async throws
}
