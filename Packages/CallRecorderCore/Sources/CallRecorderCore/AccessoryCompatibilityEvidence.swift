import Foundation

/// Human-reviewed quality evidence for one audio direction. A direction
/// passes only when speech is intelligible at the beginning, middle and end,
/// with acceptable clipping, gaps, echo and background noise.
public struct AccessoryAudioDirectionEvidence: Equatable, Sendable {
    public let intelligibleAtBeginning: Bool
    public let intelligibleAtMiddle: Bool
    public let intelligibleAtEnd: Bool
    public let clippingAcceptable: Bool
    public let gapsAcceptable: Bool
    public let echoAcceptable: Bool
    public let noiseAcceptable: Bool

    public init(
        intelligibleAtBeginning: Bool,
        intelligibleAtMiddle: Bool,
        intelligibleAtEnd: Bool,
        clippingAcceptable: Bool,
        gapsAcceptable: Bool,
        echoAcceptable: Bool,
        noiseAcceptable: Bool
    ) {
        self.intelligibleAtBeginning = intelligibleAtBeginning
        self.intelligibleAtMiddle = intelligibleAtMiddle
        self.intelligibleAtEnd = intelligibleAtEnd
        self.clippingAcceptable = clippingAcceptable
        self.gapsAcceptable = gapsAcceptable
        self.echoAcceptable = echoAcceptable
        self.noiseAcceptable = noiseAcceptable
    }

    public var isAcceptable: Bool {
        intelligibleAtBeginning
            && intelligibleAtMiddle
            && intelligibleAtEnd
            && clippingAcceptable
            && gapsAcceptable
            && echoAcceptable
            && noiseAcceptable
    }
}

/// A privacy-safe summary of one consented physical validation attempt.
/// It deliberately stores no audio, phone number, contact or media URL.
public struct AccessoryCaptureTrial: Equatable, Sendable {
    public let attemptIdentifier: String
    public let observedAt: Date
    public let consentConfirmed: Bool
    public let recordingNoticeConfirmed: Bool
    public let localAudioQuality: AccessoryAudioDirectionEvidence
    public let remoteAudioQuality: AccessoryAudioDirectionEvidence
    public let artifactIntegrityVerified: Bool

    public init(
        attemptIdentifier: String,
        observedAt: Date,
        consentConfirmed: Bool,
        recordingNoticeConfirmed: Bool,
        localAudioQuality: AccessoryAudioDirectionEvidence,
        remoteAudioQuality: AccessoryAudioDirectionEvidence,
        artifactIntegrityVerified: Bool
    ) {
        self.attemptIdentifier = attemptIdentifier
        self.observedAt = observedAt
        self.consentConfirmed = consentConfirmed
        self.recordingNoticeConfirmed = recordingNoticeConfirmed
        self.localAudioQuality = localAudioQuality
        self.remoteAudioQuality = remoteAudioQuality
        self.artifactIntegrityVerified = artifactIntegrityVerified
    }

    public var isPositive: Bool {
        consentConfirmed
            && recordingNoticeConfirmed
            && localAudioQuality.isAcceptable
            && remoteAudioQuality.isAcceptable
            && artifactIntegrityVerified
    }
}

public enum AccessoryEvidenceStatus: Equatable, Sendable {
    case confirmed(positiveTrials: Int)
    case insufficient(reason: String)
}

/// Evidence is scoped to one immutable device + OS + SIM + network + route
/// context and one accessory model/firmware. Three successful calls are
/// required; a single failed or incomplete attempt blocks promotion.
public struct AccessoryCompatibilityEvidence: Equatable, Sendable {
    public static let requiredPositiveTrials = 3

    public let context: DeviceCompatibilityContext
    public let accessory: AccessoryCaptureProfile
    public let trials: [AccessoryCaptureTrial]

    public init(
        context: DeviceCompatibilityContext,
        accessory: AccessoryCaptureProfile,
        trials: [AccessoryCaptureTrial]
    ) {
        self.context = context
        self.accessory = accessory
        self.trials = trials
    }

    public var status: AccessoryEvidenceStatus {
        let model = accessory.modelIdentifier.trimmingCharacters(in: .whitespacesAndNewlines)
        let firmware = accessory.firmwareVersion.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !model.isEmpty, !firmware.isEmpty else {
            return .insufficient(reason: "Exact accessory model and firmware are required.")
        }

        let device = context.deviceModelIdentifier.trimmingCharacters(in: .whitespacesAndNewlines)
        let os = context.operatingSystemVersion.trimmingCharacters(in: .whitespacesAndNewlines)
        let build = context.operatingSystemBuild?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !device.isEmpty, !os.isEmpty, !build.isEmpty else {
            return .insufficient(reason: "Exact iPhone model, iOS version and iOS build are required.")
        }

        let region = context.deviceRegionCode.trimmingCharacters(in: .whitespacesAndNewlines)
        let country = context.physicalTestCountryCode.trimmingCharacters(in: .whitespacesAndNewlines)
        let language = context.languageCode.trimmingCharacters(in: .whitespacesAndNewlines)
        let carrier = context.carrierIdentifier?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let carrierBundle = context.carrierBundleVersion?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !region.isEmpty, !country.isEmpty, !language.isEmpty,
              !carrier.isEmpty, !carrierBundle.isEmpty,
              context.simConfiguration != .unknown,
              context.networkType != .unknown else {
            return .insufficient(reason: "Exact device region, test country, language, carrier, carrier bundle, SIM configuration and network type are required.")
        }

        guard context.audioRouteEvidence == .physicalTestObserved else {
            return .insufficient(reason: "The active Phone call route must be observed during a physical-device test; a user report or app-owned audio-session route is not sufficient.")
        }

        guard AccessoryCaptureAssessment.isCandidateTuple(
            context: context,
            accessory: accessory
        ) else {
            return .insufficient(reason: "The active route, iPhone connector generation or accessory identity does not match this evidence tuple.")
        }

        guard trials.count >= Self.requiredPositiveTrials else {
            return .insufficient(reason: "At least three repeated physical-device calls are required.")
        }

        let identifiers = trials.map {
            $0.attemptIdentifier.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        guard identifiers.allSatisfy({ !$0.isEmpty }),
              Set(identifiers).count == identifiers.count else {
            return .insufficient(reason: "Every physical attempt must have a unique, non-empty opaque identifier.")
        }

        let timestamps = trials.map(\.observedAt)
        guard Set(timestamps).count == timestamps.count else {
            return .insufficient(reason: "Each physical attempt must have a distinct observation timestamp.")
        }

        guard trials.allSatisfy(\.isPositive) else {
            return .insufficient(reason: "Every recorded attempt must confirm consent, notice, acceptable local and remote audio quality, and artifact integrity.")
        }

        return .confirmed(positiveTrials: trials.count)
    }

    public var isConfirmed: Bool {
        if case .confirmed = status { return true }
        return false
    }
}
