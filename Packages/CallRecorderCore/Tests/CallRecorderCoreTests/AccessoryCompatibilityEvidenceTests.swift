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
        XCTAssertTrue(reason.contains("audio quality"))
    }

    func testLocalClippingBlocksEvidencePromotion() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", localClipping: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testRemoteAudioGapBlocksEvidencePromotion() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", remoteGaps: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testRemoteEchoOutsideAcceptableRangeBlocksEvidencePromotion() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", remoteEcho: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testExcessiveBackgroundNoiseBlocksEvidencePromotion() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", remoteNoise: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testSpeechMustBeIntelligibleAtBeginningMiddleAndEnd() {
        let evidence = makeEvidence(trials: [
            trial("a"), trial("b"), trial("c", remoteMiddle: false)
        ])
        XCTAssertFalse(evidence.isConfirmed)
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

    func testNumericOnlyAttemptIdentifiersAreRejectedAsPotentialPII() {
        let evidence = makeEvidence(trials: [trial("111"), trial("222"), trial("333")])
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("Numeric-only identifiers can be confused with personal identifiers")
        }
        XCTAssertTrue(reason.contains("numeric-only"))
    }

    func testOutOfOrderPhysicalAttemptsCannotBeConfirmed() {
        let evidence = makeEvidence(trials: [trial("c"), trial("b"), trial("a")])
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("Evidence must preserve chronological attempt order")
        }
        XCTAssertTrue(reason.contains("increasing observation-time order"))
    }

    func testOverlongAttemptIdentifierIsRejected() {
        let evidence = makeEvidence(trials: [
            trial(String(repeating: "a", count: 65)),
            trial("second"),
            trial("third")
        ])
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testDuplicateObservationTimestampsBlockConfirmation() {
        let timestamp = Date(timeIntervalSince1970: 1_800_000_000)
        let repeated = (1...3).map { index in
            AccessoryCaptureTrial(
                attemptIdentifier: "attempt-\(index)",
                observedAt: timestamp,
                consentConfirmed: true,
                recordingNoticeConfirmed: true,
                localAudioQuality: passingAudioQuality(),
                remoteAudioQuality: passingAudioQuality(),
                artifactIntegrityVerified: true
            )
        }
        let evidence = makeEvidence(trials: repeated)
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("One timestamp must not stand in for three distinct physical calls")
        }
        XCTAssertTrue(reason.contains("distinct observation timestamp"))
    }

    func testUserReportedRouteCannotPromotePhysicalEvidence() {
        let context = makeContext(routeEvidence: .userReported)
        let evidence = AccessoryCompatibilityEvidence(
            context: context,
            accessory: profile,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("A user-reported route is not physical route evidence")
        }
        XCTAssertTrue(reason.contains("physical-device test"))
    }

    func testAppOwnedAudioSessionRouteCannotPromotePhoneCallEvidence() {
        let context = makeContext(routeEvidence: .appOwnedSessionObserved)
        let evidence = AccessoryCompatibilityEvidence(
            context: context,
            accessory: profile,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testMissingCarrierIdentityBlocksEvidencePromotion() {
        let context = makeContext(carrier: nil)
        let evidence = AccessoryCompatibilityEvidence(
            context: context,
            accessory: profile,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        guard case .insufficient(let reason) = evidence.status else {
            return XCTFail("Carrier identity is part of the hardware/network compatibility tuple")
        }
        XCTAssertTrue(reason.contains("carrier"))
    }

    func testMissingCarrierBundleVersionBlocksEvidencePromotion() {
        let context = makeContext(carrierBundle: nil)
        let evidence = AccessoryCompatibilityEvidence(
            context: context,
            accessory: profile,
            trials: [trial("a"), trial("b"), trial("c")]
        )
        XCTAssertFalse(evidence.isConfirmed)
    }

    func testUSBCAccessoryMatchesIPhone15GenerationBoundary() {
        let context = makeContext(model: "iPhone15,2", route: .wired)
        let usbC = AccessoryCaptureProfile(
            modelIdentifier: "USB-C-Recorder",
            firmwareVersion: "1.0",
            transport: .usbC
        )
        XCTAssertTrue(AccessoryCaptureAssessment.isCandidateTuple(context: context, accessory: usbC))
    }

    func testLightningAccessoryMatchesIPhone14GenerationBoundary() {
        let context = makeContext(model: "iPhone14,7", route: .wired)
        let lightning = AccessoryCaptureProfile(
            modelIdentifier: "Lightning-Recorder",
            firmwareVersion: "1.0",
            transport: .lightning
        )
        XCTAssertTrue(AccessoryCaptureAssessment.isCandidateTuple(context: context, accessory: lightning))
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

    private func passingAudioQuality() -> AccessoryAudioDirectionEvidence {
        AccessoryAudioDirectionEvidence(
            intelligibleAtBeginning: true,
            intelligibleAtMiddle: true,
            intelligibleAtEnd: true,
            clippingAcceptable: true,
            gapsAcceptable: true,
            echoAcceptable: true,
            noiseAcceptable: true
        )
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
        integrity: Bool = true,
        remoteMiddle: Bool = true,
        localClipping: Bool = true,
        remoteGaps: Bool = true,
        remoteEcho: Bool = true,
        remoteNoise: Bool = true
    ) -> AccessoryCaptureTrial {
        func quality(
            speech: Bool,
            middle: Bool = true,
            clipping: Bool = true,
            gaps: Bool = true,
            echo: Bool = true,
            noise: Bool = true
        ) -> AccessoryAudioDirectionEvidence {
            AccessoryAudioDirectionEvidence(
                intelligibleAtBeginning: speech,
                intelligibleAtMiddle: speech && middle,
                intelligibleAtEnd: speech,
                clippingAcceptable: clipping,
                gapsAcceptable: gaps,
                echoAcceptable: echo,
                noiseAcceptable: noise
            )
        }

        return AccessoryCaptureTrial(
            attemptIdentifier: identifier,
            observedAt: Date(
                timeIntervalSince1970: 1_800_000_000
                    + Double(identifier.unicodeScalars.reduce(0) { $0 + Int($1.value) })
            ),
            consentConfirmed: consent,
            recordingNoticeConfirmed: notice,
            localAudioQuality: quality(speech: local, clipping: localClipping),
            remoteAudioQuality: quality(
                speech: remote,
                middle: remoteMiddle,
                gaps: remoteGaps,
                echo: remoteEcho,
                noise: remoteNoise
            ),
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
        route: CallAudioRoute = .speaker,
        routeEvidence: CallAudioRouteEvidence = .physicalTestObserved,
        carrier: String? = "carrier.example",
        carrierBundle: String? = "bundle-1.0"
    ) -> DeviceCompatibilityContext {
        DeviceCompatibilityContext(
            deviceModelIdentifier: model,
            operatingSystemVersion: "18.7.1",
            operatingSystemBuild: build,
            deviceRegionCode: "US",
            physicalTestCountryCode: "US",
            languageCode: "en-US",
            carrierIdentifier: carrier,
            carrierBundleVersion: carrierBundle,
            simConfiguration: .physicalAndESIM,
            isRoaming: false,
            networkType: .cellular5G,
            wifiCallingEnabled: false,
            volteEnabled: true,
            callDirection: .incoming,
            audioRoute: route,
            audioRouteEvidence: routeEvidence
        )
    }
}
