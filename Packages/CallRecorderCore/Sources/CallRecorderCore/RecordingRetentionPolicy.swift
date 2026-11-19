import Foundation

/// User-selected retention duration for locally imported recordings.
/// The default is indefinite retention; expiration is opt-in.
public enum RecordingRetentionPolicy: Int, CaseIterable, Sendable {
    case keepForever = 0
    case thirtyDays = 30
    case ninetyDays = 90
    case oneYear = 365

    public func expirationDate(relativeTo now: Date) -> Date? {
        guard self != .keepForever else { return nil }
        return now.addingTimeInterval(-TimeInterval(rawValue) * 24 * 60 * 60)
    }

    public func hasExpired(
        importedAt: Date,
        relativeTo now: Date
    ) -> Bool {
        guard let cutoff = expirationDate(relativeTo: now) else {
            return false
        }
        return importedAt < cutoff
    }
}
