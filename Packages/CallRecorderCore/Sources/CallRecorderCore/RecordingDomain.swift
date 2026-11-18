import Foundation

/// A capture or companion route investigated by the product.
public enum RecordingPathway: String, CaseIterable, Sendable {
    case nativeCompanion
    case conferenceBridge
    case carrierService
    case appOwnedVoIP
    case bluetoothAccessory
    case wiredAccessory
    case acoustic
    case experimental
}

/// Capability decisions are scoped to this exact environment context.
public struct DeviceCompatibilityContext: Equatable, Sendable {
    public let deviceModelIdentifier: String
    public let operatingSystemVersion: String
    public let regionCode: String
    public let carrierIdentifier: String?
    public let usesPhysicalSIM: Bool
    public let isRoaming: Bool

    public init(
        deviceModelIdentifier: String,
        operatingSystemVersion: String,
        regionCode: String,
        carrierIdentifier: String? = nil,
        usesPhysicalSIM: Bool,
        isRoaming: Bool
    ) {
        self.deviceModelIdentifier = deviceModelIdentifier
        self.operatingSystemVersion = operatingSystemVersion
        self.regionCode = regionCode
        self.carrierIdentifier = carrierIdentifier
        self.usesPhysicalSIM = usesPhysicalSIM
        self.isRoaming = isRoaming
    }
}

public enum PathwayAvailability: Equatable, Sendable {
    case available
    case unavailable(reason: String)
    case requiresUserAction(reason: String)
    case requiresExternalHardware(reason: String)
    case experimental(reason: String)
}

public struct PathwayCapability: Equatable, Sendable {
    public let pathway: RecordingPathway
    public let availability: PathwayAvailability
    public let evidenceReference: String?

    public init(
        pathway: RecordingPathway,
        availability: PathwayAvailability,
        evidenceReference: String? = nil
    ) {
        self.pathway = pathway
        self.availability = availability
        self.evidenceReference = evidenceReference
    }
}

/// Two-way support is not inferred from the existence of an artifact.
public struct RecordingArtifact: Equatable, Sendable {
    public let identifier: String
    public let durationSeconds: TimeInterval
    public let localAudioVerified: Bool
    public let remoteAudioVerified: Bool

    public init(
        identifier: String,
        durationSeconds: TimeInterval,
        localAudioVerified: Bool,
        remoteAudioVerified: Bool
    ) {
        self.identifier = identifier
        self.durationSeconds = durationSeconds
        self.localAudioVerified = localAudioVerified
        self.remoteAudioVerified = remoteAudioVerified
    }

    public var hasVerifiedTwoWayAudio: Bool {
        localAudioVerified && remoteAudioVerified
    }
}
