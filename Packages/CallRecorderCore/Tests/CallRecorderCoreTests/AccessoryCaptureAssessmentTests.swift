import XCTest
@testable import CallRecorderCore

final class AccessoryCaptureAssessmentTests: XCTestCase {
    func testWiredAccessoryRequiresAnActiveWiredOrExternalRoute() {
        let result = assess(.usbC, route: .speaker)
        guard case .unavailable = result.availability else {
            return XCTFail("A connected-looking USB accessory must not be assumed active on speaker route")
        }
        XCTAssertEqual(result.pathway, .wiredAccessory)
    }

    func testWiredAccessoryOnExternalRouteRemainsExperimental() {
        let result = assess(.lightning, route: .externalAccessory)
        assertExperimental(result, containing: "three physical calls")
    }

    func testBluetoothAccessoryRequiresHFPRoute() {
        let result = assess(.bluetoothHFP, route: .wired)
        guard case .unavailable = result.availability else {
            return XCTFail("Bluetooth accessory must not pass when HFP is not the active route")
        }
    }

    func testBluetoothHFPDoesNotBecomeSupportedFromPairingAlone() {
        let result = assess(.bluetoothHFP, route: .bluetoothHFP)
        assertExperimental(result, containing: "candidate only")
        XCTAssertEqual(result.pathway, .bluetoothAccessory)
    }

    func testContactVibrationRecorderRequiresSpeakerRoute() {
        let result = assess(.contactVibration, route: .receiver)
        guard case .unavailable = result.availability else {
            return XCTFail("Contact/vibration recorder requires the documented speakerphone setup")
        }
    }

    func testContactVibrationRecorderOnSpeakerRemainsExperimental() {
        let result = assess(.contactVibration, route: .speaker)
        assertExperimental(result, containing: "local and remote speech independently")
        XCTAssertEqual(result.pathway, .independentExternalRecorder)
    }

    func testStandaloneAcousticRecorderRequiresSpeakerRoute() {
        let result = assess(.standaloneAcoustic, route: .bluetoothHFP)
        guard case .unavailable = result.availability else {
            return XCTFail("Acoustic recorder must not be accepted while call audio is routed to Bluetooth")
        }
    }

    func testMissingAccessoryModelOrFirmwareFailsClosed() {
        let profile = AccessoryCaptureProfile(
            modelIdentifier: " ",
            firmwareVersion: "",
            transport: .usbC
        )
        let result = AccessoryCaptureAssessment.assess(
            context: makeContext(route: .wired),
            accessory: profile
        )
        assertExperimental(result, containing: "model and firmware")
    }

    func testMissingDeviceTupleFailsClosed() {
        let context = DeviceCompatibilityContext(
            deviceModelIdentifier: "",
            operatingSystemVersion: "",
            deviceRegionCode: "US",
            physicalTestCountryCode: "US",
            languageCode: "en-US",
            simConfiguration: .physicalSingle,
            isRoaming: false,
            networkType: .cellularLTE,
            wifiCallingEnabled: false,
            volteEnabled: true,
            callDirection: .outgoing,
            audioRoute: .wired
        )
        let result = AccessoryCaptureAssessment.assess(
            context: context,
            accessory: profile(.usbC)
        )
        assertExperimental(result, containing: "exact iPhone model identifier")
    }

    func testUSBCAccessoryIsRejectedForLightningGeneration() {
        let context = makeContext(route: .wired, model: "iPhone14,5")
        let result = AccessoryCaptureAssessment.assess(
            context: context,
            accessory: profile(.usbC)
        )
        guard case .unavailable(let reason) = result.availability else {
            return XCTFail("USB-C accessory must not be assumed directly compatible with a Lightning iPhone")
        }
        XCTAssertTrue(reason.contains("connector does not match"))
    }

    func testLightningAccessoryIsRejectedForUSBCGeneration() {
        let context = makeContext(route: .wired, model: "iPhone16,1")
        let result = AccessoryCaptureAssessment.assess(
            context: context,
            accessory: profile(.lightning)
        )
        guard case .unavailable = result.availability else {
            return XCTFail("Lightning accessory must not be assumed directly compatible with a USB-C iPhone")
        }
    }

    func testUnknownIPhoneGenerationDoesNotGuessConnector() {
        let context = makeContext(route: .wired, model: "iPhone-unknown")
        let result = AccessoryCaptureAssessment.assess(
            context: context,
            accessory: profile(.usbC)
        )
        assertExperimental(result, containing: "does not match a recognized iPhone generation")
    }

    func testAssessmentRetainsEvidenceReference() {
        let result = AccessoryCaptureAssessment.assess(
            context: makeContext(route: .bluetoothHFP),
            accessory: AccessoryCaptureProfile(
                modelIdentifier: "Recorder-X",
                firmwareVersion: "1.2.3",
                transport: .bluetoothHFP,
                evidenceReference: "https://example.com/device-spec"
            )
        )
        XCTAssertEqual(result.evidenceReference, "https://example.com/device-spec")
    }

    private func profile(_ transport: AccessoryCaptureTransport) -> AccessoryCaptureProfile {
        AccessoryCaptureProfile(
            modelIdentifier: "Recorder-X",
            firmwareVersion: "1.2.3",
            transport: transport
        )
    }

    private func assess(
        _ transport: AccessoryCaptureTransport,
        route: CallAudioRoute
    ) -> PathwayCapability {
        AccessoryCaptureAssessment.assess(
            context: makeContext(route: route),
            accessory: profile(transport)
        )
    }

    private func makeContext(
        route: CallAudioRoute,
        model: String = "iPhone16,1"
    ) -> DeviceCompatibilityContext {
        DeviceCompatibilityContext(
            deviceModelIdentifier: model,
            operatingSystemVersion: "18.7.1",
            operatingSystemBuild: "22H",
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

    private func assertExperimental(
        _ capability: PathwayCapability,
        containing phrase: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard case .experimental(let reason) = capability.availability else {
            return XCTFail("Accessory candidates must remain experimental until physical proof", file: file, line: line)
        }
        XCTAssertTrue(reason.contains(phrase), file: file, line: line)
    }
}
