import XCTest
@testable import CallRecorderCore

final class AccessoryCompatibilityEvidenceTests: XCTestCase {
    func testThreePositivePhysicalCallsConfirmExactTuple() {
        let evidence = makeEvidence(trials: [trial("a"), trial("b"), trial("c")])
        XCTAssertEqual(evidence.status, .confirmed(positiveTrials: 3))
        XCTAssertTrue(evidence.isConfirmed)
    }

    func testTwoPositiveCallsAreInsufficient() {
        let evidence = makeEvidence(trials: [trial("a"), trial("b")])
        XCTAssertEqual(
            evidence.status,
            .insufficient(reason: "At least three repeated physical-device calls are required.")
        )
    }

    func testFailedRemoteSpeechBlocksConfirmation() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"),
            trial("c", remote: false)
        ])
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("A failed remote speech check must block confirmation")
        }
        XCTAssertTrue(reason.contains("local and remote speech"))
    }

    func testMissingConsentBlocksConfirmation() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", consent: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testMissingRecordingNoticeBlocksConfirmation() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", notice: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testCorruptArtifactBlocksConfirmation() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", integrity: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testDuplicateAttemptIdentifiersBlockConfirmation() {
        let evidence = makeEvidence(trials: [trial("same"), trial("same"), trial("third")])
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("Duplicate attempt identifiers must not count as repeated evidence")
        }
        XCTAssertTrue(reason.contains("unique"))
    }

    func testMismatchedActiveRouteBlocksOtherwisePositiveTrials() {
        let context = makeContext(route: .receiver)
        let evidence = AccessoryCompatibilityEvidence(
            context: context,
            accessory: profile,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("Positive summaries cannot override a mismatched physical route")
        }
        XCTAssertTrue(reason.contains("active route"))
    }

    func testConnectorGenerationMismatchBlocksEvidencePromotion() {
        let context = makeContext(model: "iPhone14,5", route: .wired)
        let usbC = AccessoryCaptureProfile(
            modelIdentifier: "USB-C-Recorder",
            firmwareVersion: "1.0",
            transport: .usbC
        )
        let evidence = AccessoryCompatibilityEvidence(
            context: context,
            accessory: usbC,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testDuplicateObservationTimestampsBlockConfirmation() {
        let timestamp = Date(timeIntervalSince1970: 1_800_000_000)
        let repeated = (1...3).map { index in
            AccessoryCaptureTrial(
                attemptIdentifier: "attempt-\\(index)",
                observedAt: timestamp,
                consentConfirmed: true,
                recordingNoticeConfirmed: true,
                localSpeechIntelligible: true,
                remoteSpeechIntelligible: true,
                artifactIntegrityVerified: true
            )
        }
        let evidence = makeEvidence(trials: repeated)
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("One timestamp must not stand in for three distinct physical calls")
        }
        XCTAssertTrue(reason.contains("distinct observation timestamp"))
    }

    func testMissingOSBuildBlocksConfirmation() {
        let context = makeContext(build: nil)
        let evidence = AccessoryCompatibilityEvidence(
            context: context,
            accessory: profile,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("OS build is part of the compatibility tuple")
        }
        XCTAssertTrue(reason.contains("iOS build"))
    }

    func testMissingAccessoryFirmwareBlocksConfirmation() {
        let accessory = AccessoryCaptureProfile(
            modelIdentifier: "Recorder-X",
            firmwareVersion: " ",
            transport: .contactVibration
        )
        let evidence = AccessoryCompatibilityEvidence(
            context: makeContext(),
            accessory: accessory,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("Firmware version is required")
        }
        XCTAssertTrue(reason.contains("firmware"))
    }

    private var profile: AccessoryCaptureProfile {
        AccessoryCaptureProfile(
            modelIdentifier: "Recorder-X",
            firmwareVersion: "1.2.3",
            transport: .contactVibration
        )
    }

    private func trial(
        _ identifier: String,
        consent: Bool = true,
        notice: Bool = true,
        local: Bool = true,
        remote: Bool = true,
        integrity: Bool = true
    ) -> AccessoryCaptureTrial {
        AccessoryCaptureTrial(
            attemptIdentifier: identifier,
            observedAt: Date(
                timeIntervalSince1970: 1_800_000_000
                    + Double(identifier.unicodeScalars.reduce(0) { $0 + Int($1.value) })
            ),
            consentConfirmed: consent,
            recordingNoticeConfirmed: notice,
            localSpeechIntelligible: local,
            remoteSpeechIntelligible: remote,
            artifactIntegrityVerified: integrity
        )
    }

    private func makeEvidence(trials: [AccessoryCaptureTrial]) -> AccessoryCompatibilityEvidence {
        AccessoryCompatibilityEvidence(
            context: makeContext(),
            accessory: profile,
            trials: trials
        )
    }

    private func makeContext(
        build: String? = "22H",
        model: String = "iPhone16,1",
        route: CallAudioRoute = .speaker
    ) -> DeviceCompatibilityContext {
        DeviceCompatibilityContext(
            deviceModelIdentifier: model,
            operatingSystemVersion: "18.7.1",
            operatingSystemBuild: build,
            deviceRegionCode: "US",
            physicalTestCountryCode: "US",
            languageCode: "en-US",
            simConfiguration: .physicalAndESIM,
            isRoaming: false,
            networkType: .cellular5G,
            wifiCallingEnabled: false,
            volteEnabled: true,
            callDirection: .incoming,
            audioRoute: route
        )
    }
}
