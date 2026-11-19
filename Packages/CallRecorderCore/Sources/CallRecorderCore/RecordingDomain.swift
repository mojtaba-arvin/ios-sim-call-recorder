import Foundation

/// A capture or companion route investigated by the product.
public enum RecordingPathway: String, CaseIterable, Hashable, Sendable {
    case nativeCompanion
    case appleSystemCallRecording
    case independentExternalRecorder
    case replayKitAppCapture
    case conferenceBridge
    case carrierService
    case appOwnedVoIP
    case bluetoothAccessory
    case wiredAccessory
    case acoustic
    case experimental
}

public enum SIMConfiguration: String, Hashable, Sendable {
    case physicalSingle
    case eSIMSingle
    case dualPhysical
    case dualESIM
    case physicalAndESIM
    case unknown
}

public enum NetworkType: String, Hashable, Sendable {
    case cellularLTE
    case cellular5G
    case wifiCalling
    case unknown
}

public enum CallDirection: String, Hashable, Sendable {
    case incoming
    case outgoing
}

public enum CallAudioRoute: String, Hashable, Sendable {
    case receiver
    case speaker
    case wired
    case bluetoothHFP
    case externalAccessory
    case unknown
}

/// Capability decisions are scoped to this exact environment context.
public struct DeviceCompatibilityContext: Equatable, Sendable {
    public let deviceModelIdentifier: String
    public let operatingSystemVersion: String
    public let operatingSystemBuild: String?
    public let deviceRegionCode: String
    public let physicalTestCountryCode: String
    public let languageCode: String
    public let carrierIdentifier: String?
    public let carrierBundleVersion: String?
    public let simConfiguration: SIMConfiguration
    public let isRoaming: Bool
    public let networkType: NetworkType
    public let wifiCallingEnabled: Bool
    public let volteEnabled: Bool
    public let callDirection: CallDirection
    public let audioRoute: CallAudioRoute
    public let callParticipantCount: Int

    public init(
        deviceModelIdentifier: String,
        operatingSystemVersion: String,
        operatingSystemBuild: String? = nil,
        deviceRegionCode: String,
        physicalTestCountryCode: String,
        languageCode: String,
        carrierIdentifier: String? = nil,
        carrierBundleVersion: String? = nil,
        simConfiguration: SIMConfiguration,
        isRoaming: Bool,
        networkType: NetworkType,
        wifiCallingEnabled: Bool,
        volteEnabled: Bool,
        callDirection: CallDirection,
        audioRoute: CallAudioRoute,
        callParticipantCount: Int = 2
    ) {
        self.deviceModelIdentifier = deviceModelIdentifier
        self.operatingSystemVersion = operatingSystemVersion
        self.operatingSystemBuild = operatingSystemBuild
        self.deviceRegionCode = deviceRegionCode
        self.physicalTestCountryCode = physicalTestCountryCode
        self.languageCode = languageCode
        self.carrierIdentifier = carrierIdentifier
        self.carrierBundleVersion = carrierBundleVersion
        self.simConfiguration = simConfiguration
        self.isRoaming = isRoaming
        self.networkType = networkType
        self.wifiCallingEnabled = wifiCallingEnabled
        self.volteEnabled = volteEnabled
        self.callDirection = callDirection
        self.audioRoute = audioRoute
        self.callParticipantCount = callParticipantCount
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

/// A returned file is not successful until its metadata and both audio
/// directions have been independently verified.
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

    public var isStructurallyValid: Bool {
        !identifier.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && durationSeconds.isFinite
            && durationSeconds > 0
    }

    public var hasVerifiedTwoWayAudio: Bool {
        isStructurallyValid && localAudioVerified && remoteAudioVerified
    }
}
