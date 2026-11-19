import Foundation

/// The physical signal path an accessory claims to use. A transport alone
/// never proves that both cellular-call directions reach the recorder.
public enum AccessoryCaptureTransport: String, Equatable, Sendable {
    case lightning
    case usbC
    case bluetoothHFP
    case contactVibration
    case standaloneAcoustic
}

/// A concrete accessory candidate. Model and firmware are required so results
/// can be tied to a reproducible hardware tuple instead of a generic category.
public struct AccessoryCaptureProfile: Equatable, Sendable {
    public let modelIdentifier: String
    public let firmwareVersion: String
    public let transport: AccessoryCaptureTransport
    public let evidenceReference: String?

    public init(
        modelIdentifier: String,
        firmwareVersion: String,
        transport: AccessoryCaptureTransport,
        evidenceReference: String? = nil
    ) {
        self.modelIdentifier = modelIdentifier
        self.firmwareVersion = firmwareVersion
        self.transport = transport
        self.evidenceReference = evidenceReference
    }
}

/// Conservative compatibility assessment for external call-recording
/// candidates. It checks only whether the observed route is consistent with
/// the accessory's declared mechanism; it does not certify two-way audio.
public enum AccessoryCaptureAssessment {
    public static func assess(
        context: DeviceCompatibilityContext,
        accessory: AccessoryCaptureProfile
    ) -> PathwayCapability {
        let pathway = pathway(for: accessory.transport)
        let model = accessory.modelIdentifier.trimmingCharacters(in: .whitespacesAndNewlines)
        let firmware = accessory.firmwareVersion.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !model.isEmpty, !firmware.isEmpty else {
            return PathwayCapability(
                pathway: pathway,
                availability: .experimental(
                    reason: "A concrete accessory model and firmware version are required before compatibility can be assessed."
                ),
                evidenceReference: accessory.evidenceReference
            )
        }

        guard routeMatches(accessory.transport, route: context.audioRoute) else {
            return PathwayCapability(
                pathway: pathway,
                availability: .unavailable(
                    reason: "The active call route does not match the accessory transport. Connect and select the accessory, or switch to speakerphone for an acoustic/contact recorder."
                ),
                evidenceReference: accessory.evidenceReference
            )
        }

        let device = context.deviceModelIdentifier.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !device.isEmpty,
              !context.operatingSystemVersion.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return PathwayCapability(
                pathway: pathway,
                availability: .experimental(
                    reason: "An exact iPhone model identifier and iOS version are required for a device-specific compatibility record."
                ),
                evidenceReference: accessory.evidenceReference
            )
        }

        if accessory.transport == .lightning || accessory.transport == .usbC {
            guard let connector = inferredConnector(for: device) else {
                return PathwayCapability(
                    pathway: pathway,
                    availability: .experimental(
                        reason: "The iPhone model identifier does not match a recognized iPhone generation; connector compatibility must be verified manually."
                    ),
                    evidenceReference: accessory.evidenceReference
                )
            }
            let expectedTransport: AccessoryCaptureTransport = connector == .lightning ? .lightning : .usbC
            guard accessory.transport == expectedTransport else {
                return PathwayCapability(
                    pathway: pathway,
                    availability: .unavailable(
                        reason: "The accessory connector does not match the iPhone model generation. Use a connector-compatible accessory and assess any adapter as a separate hardware configuration."
                    ),
                    evidenceReference: accessory.evidenceReference
                )
            }
        }

        return PathwayCapability(
            pathway: pathway,
            availability: .experimental(
                reason: "Accessory \(model) (firmware \(firmware)) is connected on the expected route for \(device) running iOS \(context.operatingSystemVersion). This is a candidate only: verify local and remote speech independently in three physical calls before marking this exact tuple supported."
            ),
            evidenceReference: accessory.evidenceReference
        )
    }

    private enum IPhoneConnector {
        case lightning
        case usbC
    }

    /// iPhone 15 introduced USB-C; earlier iPhone generations use Lightning.
    /// Unknown/non-iPhone identifiers fail closed instead of guessing.
    private static func inferredConnector(for modelIdentifier: String) -> IPhoneConnector? {
        guard modelIdentifier.hasPrefix("iPhone"),
              let comma = modelIdentifier.firstIndex(of: ",") else {
            return nil
        }
        let generationStart = modelIdentifier.index(modelIdentifier.startIndex, offsetBy: 6)
        guard generationStart < comma,
              let generation = Int(modelIdentifier[generationStart..<comma]),
              generation > 0 else {
            return nil
        }
        return generation >= 15 ? .usbC : .lightning
    }

    private static func pathway(for transport: AccessoryCaptureTransport) -> RecordingPathway {
        switch transport {
        case .lightning, .usbC:
            return .wiredAccessory
        case .bluetoothHFP:
            return .bluetoothAccessory
        case .contactVibration, .standaloneAcoustic:
            return .independentExternalRecorder
        }
    }

    private static func routeMatches(
        _ transport: AccessoryCaptureTransport,
        route: CallAudioRoute
    ) -> Bool {
        switch transport {
        case .lightning, .usbC:
            return route == .wired || route == .externalAccessory
        case .bluetoothHFP:
            return route == .bluetoothHFP
        case .contactVibration, .standaloneAcoustic:
            return route == .speaker
        }
    }
}
