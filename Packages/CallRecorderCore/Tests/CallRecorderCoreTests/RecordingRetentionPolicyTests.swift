import XCTest
@testable import CallRecorderCore

final class RecordingRetentionPolicyTests: XCTestCase {
    func testKeepForeverNeverExpires() {
        let now = Date(timeIntervalSince1970: 2_000_000_000)
        let oldImport = Date(timeIntervalSince1970: 1)
        XCTAssertNil(RecordingRetentionPolicy.keepForever.expirationDate(relativeTo: now))
        XCTAssertFalse(RecordingRetentionPolicy.keepForever.hasExpired(
            importedAt: oldImport,
            relativeTo: now
        ))
    }

    func testThirtyDayPolicyExpiresOnlyOlderItems() {
        let now = Date(timeIntervalSince1970: 2_000_000_000)
        let cutoff = now.addingTimeInterval(-30 * 24 * 60 * 60)
        XCTAssertFalse(RecordingRetentionPolicy.thirtyDays.hasExpired(
            importedAt: cutoff,
            relativeTo: now
        ))
        XCTAssertTrue(RecordingRetentionPolicy.thirtyDays.hasExpired(
            importedAt: cutoff.addingTimeInterval(-1),
            relativeTo: now
        ))
    }

    func testSupportedPoliciesHaveExpectedDurations() {
        XCTAssertEqual(
            RecordingRetentionPolicy.allCases.map(\.rawValue),
            [0, 30, 90, 365]
        )
    }
}
