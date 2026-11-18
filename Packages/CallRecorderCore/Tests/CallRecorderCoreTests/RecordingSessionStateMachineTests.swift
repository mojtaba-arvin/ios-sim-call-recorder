import XCTest
@testable import CallRecorderCore

final class RecordingSessionStateMachineTests: XCTestCase {
    func testHappyPathRequiresFinalizationBeforeCompletion() throws {
        var machine = RecordingSessionStateMachine()
        try machine.transition(to: .preparing)
        try machine.transition(to: .awaitingConsent)
        try machine.transition(to: .connecting)
        try machine.transition(to: .recording)
        try machine.transition(to: .finalizing)
        try machine.transition(to: .completed)
        XCTAssertEqual(machine.state, .completed)
    }

    func testCannotStartConnectingBeforeConsent() {
        var machine = RecordingSessionStateMachine()
        XCTAssertThrowsError(try machine.transition(to: .connecting)) { error in
            XCTAssertEqual(
                error as? RecordingSessionTransitionError,
                .invalidTransition(from: .idle, to: .connecting)
            )
        }
        XCTAssertEqual(machine.state, .idle)
    }

    func testInterruptedSessionCanReconnect() throws {
        var machine = RecordingSessionStateMachine()
        try machine.transition(to: .preparing)
        try machine.transition(to: .awaitingConsent)
        try machine.transition(to: .connecting)
        try machine.transition(to: .recording)
        try machine.transition(to: .interrupted)
        try machine.transition(to: .connecting)
        XCTAssertEqual(machine.state, .connecting)
    }

    func testTerminalStateCannotBeReopened() throws {
        var machine = RecordingSessionStateMachine()
        try machine.transition(to: .cancelled)
        XCTAssertThrowsError(try machine.transition(to: .preparing))
        XCTAssertEqual(machine.state, .cancelled)
    }

    func testArtifactRequiresBothAudioDirections() {
        let oneSided = RecordingArtifact(
            identifier: "one-sided",
            durationSeconds: 12,
            localAudioVerified: true,
            remoteAudioVerified: false
        )
        let twoSided = RecordingArtifact(
            identifier: "two-sided",
            durationSeconds: 12,
            localAudioVerified: true,
            remoteAudioVerified: true
        )
        XCTAssertFalse(oneSided.hasVerifiedTwoWayAudio)
        XCTAssertTrue(twoSided.hasVerifiedTwoWayAudio)
    }
}
