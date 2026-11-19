import XCTest
@testable import CallRecorderCore

final class RecordingPathwayAssessmentTests: XCTestCase {
    func testAppleCallRecordingDoesNotAssumeGroupCallSupport() {
        let capability = RecordingPathwayAssessment.appleSystemCallRecording(
            for: makeContext(participants: 3)
        )

        guard case .unavailable(let reason) = capability.availability else {
            return XCTFail("Group-call recording must not be assumed supported")
        }
        XCTAssertTrue(reason.contains("one other person"))
    }

    func testAppleCallRecordingRequiresIOS181OrLater() {
        let capability = RecordingPathwayAssessment.appleSystemCallRecording(
            for: makeContext(os: "18.0")
        )

        XCTAssertEqual(capability.pathway, .appleSystemCallRecording)
        XCTAssertEqual(
            capability.availability,
            .unavailable(reason: "Requires iOS 18.1 or later; detected 18.0.")
        )
    }

    func testAppleCallRecordingIsUnavailableInEuropeanUnion() {
        let capability = RecordingPathwayAssessment.appleSystemCallRecording(
            for: makeContext(region: "DE", country: "DE")
        )

        guard case .unavailable = capability.availability else {
            return XCTFail("Expected EU region to be unavailable")
        }
    }

    func testAppleCallRecordingIsUnavailableInOman() {
        let capability = RecordingPathwayAssessment.appleSystemCallRecording(
            for: makeContext(region: "OM", country: "OM")
        )

        guard case .unavailable = capability.availability else {
            return XCTFail("Expected Oman to be unavailable")
        }
    }

    func testSupportedMarketReturnsUserMediatedPathwayNotAutomaticCapture() {
        let capability = RecordingPathwayAssessment.appleSystemCallRecording(
            for: makeContext(region: "US", country: "US", language: "en-US")
        )

        guard case .requiresUserAction(let reason) = capability.availability else {
            return XCTFail("Expected a user-mediated Phone.app workflow")
        }
        XCTAssertTrue(reason.contains("Phone.app"))
        XCTAssertTrue(reason.contains("Notes"))
    }

    func testUnknownRegionFailsClosedAsExperimental() {
        let capability = RecordingPathwayAssessment.appleSystemCallRecording(
            for: makeContext(region: "ZZ", country: "US")
        )

        guard case .experimental = capability.availability else {
            return XCTFail("Unknown region must not be assumed supported")
        }
    }

    func testReplayKitIsNotPresentedAsNativeCellularCapture() {
        let capability = RecordingPathwayAssessment.replayKitForNativeCellularCall()

        guard case .unavailable(let reason) = capability.availability else {
            return XCTFail("ReplayKit must not be advertised for Phone.app audio")
        }
        XCTAssertTrue(reason.contains("Phone.app"))
    }

    func testExternalRecorderRequiresIndependentHardware() {
        let capability = RecordingPathwayAssessment.independentExternalRecorder()

        guard case .requiresExternalHardware = capability.availability else {
            return XCTFail("Expected an independent recorder requirement")
        }
    }

    private func makeContext(
        os: String = "18.1",
        region: String = "US",
        country: String = "US",
        language: String = "en-US",
        participants: Int = 2
    ) -> DeviceCompatibilityContext {
        DeviceCompatibilityContext(
            deviceModelIdentifier: "iPhone-test",
            operatingSystemVersion: os,
            deviceRegionCode: region,
            physicalTestCountryCode: country,
            languageCode: language,
            simConfiguration: .physicalSingle,
            isRoaming: false,
            networkType: .cellularLTE,
            wifiCallingEnabled: false,
            volteEnabled: true,
            callDirection: .outgoing,
            audioRoute: .speaker,
            callParticipantCount: participants
        )
    }
}
