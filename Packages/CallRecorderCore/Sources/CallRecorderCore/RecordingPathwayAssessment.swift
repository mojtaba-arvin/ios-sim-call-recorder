import Foundation

/// Evidence-based capability discovery for system and accessory routes.
///
/// This deliberately does not start Phone.app recording: Apple exposes that
/// action through the Phone UI, and the user must export/share the resulting
/// audio file from Notes into this app.
public enum RecordingPathwayAssessment {
    public static let appleCallRecordingEvidence =
        "https://support.apple.com/guide/iphone/record-and-transcribe-a-call-iph57c6590e9/27/ios"
    public static let replayKitEvidence =
        "https://developer.apple.com/documentation/ReplayKit"

    private static let minimumAppleCallRecordingVersion = (major: 18, minor: 1)

    /// Apple currently excludes these markets from built-in Phone call recording.
    /// EU member states are expanded explicitly so callers can pass ISO country
    /// codes instead of relying on a non-standard "EU" pseudo-country code.
    private static let unavailableCountryCodes: Set<String> = [
        "AZ", "BH", "EG", "IR", "IQ", "JO", "KW", "MA", "NG", "OM",
        "PK", "QA", "RU", "SA", "ZA", "TR", "AE", "YE",
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI",
        "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
        "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"
    ]

    private static let supportedLanguagePrefixes: Set<String> = [
        "ar", "zh", "ca", "cs", "da", "nl", "en", "fi", "fr",
        "de", "el", "he", "hi", "hu", "id", "it", "ja", "ko",
        "ms", "no", "pl", "pt", "ro", "ru", "sk", "es", "sv",
        "th", "tr", "uk", "vi"
    ]

    /// Returns a user-mediated native Phone recording option when Apple’s
    /// documented OS, region and language requirements appear satisfied.
    /// Region checks are conservative: both the device region and physical
    /// test country must be outside Apple's published unavailable markets.
    public static func appleSystemCallRecording(
        for context: DeviceCompatibilityContext
    ) -> PathwayCapability {
        let version = parseVersion(context.operatingSystemVersion)
        guard version >= minimumAppleCallRecordingVersion else {
            return PathwayCapability(
                pathway: .appleSystemCallRecording,
                availability: .unavailable(
                    reason: "Requires iOS 18.1 or later; detected \(context.operatingSystemVersion)."
                ),
                evidenceReference: appleCallRecordingEvidence
            )
        }

        let deviceRegion = context.deviceRegionCode.uppercased()
        let physicalCountry = context.physicalTestCountryCode.uppercased()
        guard !deviceRegion.isEmpty,
              !physicalCountry.isEmpty,
              deviceRegion != "ZZ",
              physicalCountry != "ZZ" else {
            return PathwayCapability(
                pathway: .appleSystemCallRecording,
                availability: .experimental(
                    reason: "Device region and physical test country must be confirmed before relying on Apple's regional availability."
                ),
                evidenceReference: appleCallRecordingEvidence
            )
        }

        guard !unavailableCountryCodes.contains(deviceRegion),
              !unavailableCountryCodes.contains(physicalCountry) else {
            return PathwayCapability(
                pathway: .appleSystemCallRecording,
                availability: .unavailable(
                    reason: "Apple currently lists call recording as unavailable for the device region or physical test market."
                ),
                evidenceReference: appleCallRecordingEvidence
            )
        }

        let language = context.languageCode
            .lowercased()
            .split(separator: "-")
            .first
            .map(String.init) ?? ""
        guard supportedLanguagePrefixes.contains(language) else {
            return PathwayCapability(
                pathway: .appleSystemCallRecording,
                availability: .experimental(
                    reason: "The configured language is not in Apple's published call-recording language list."
                ),
                evidenceReference: appleCallRecordingEvidence
            )
        }

        return PathwayCapability(
            pathway: .appleSystemCallRecording,
            availability: .requiresUserAction(
                reason: "The user must start recording in Phone.app, hear Apple's recording announcement, then export/share the saved audio from Notes. Public app APIs do not expose native Phone call audio or remote-start control."
            ),
            evidenceReference: appleCallRecordingEvidence
        )
    }

    /// A physically separate recorder can capture speakerphone output
    /// acoustically, independent of iOS call-audio APIs. It requires an
    /// explicit user-operated device and subsequent file import.
    public static func independentExternalRecorder() -> PathwayCapability {
        PathwayCapability(
            pathway: .independentExternalRecorder,
            availability: .requiresExternalHardware(
                reason: "Requires a separate recorder/microphone and speakerphone routing. Audio quality, echo, both-side audibility and consent must be verified per device and environment."
            ),
            evidenceReference: "https://support.apple.com/guide/iphone/make-a-recording-iph4d2a39a3b/27/ios"
        )
    }

    /// ReplayKit captures the app's own audio and microphone, not another
    /// app's private Phone-call stream. It remains useful for app-owned VoIP.
    public static func replayKitForNativeCellularCall() -> PathwayCapability {
        PathwayCapability(
            pathway: .replayKitAppCapture,
            availability: .unavailable(
                reason: "ReplayKit records app audio and microphone; it is not a public capture path for Phone.app cellular-call audio."
            ),
            evidenceReference: replayKitEvidence
        )
    }

    private static func parseVersion(_ value: String) -> (major: Int, minor: Int) {
        let components = value.split(separator: ".")
        guard let major = components.first.flatMap({ Int($0) }) else {
            return (0, 0)
        }
        let minor = components.count > 1 ? (Int(components[1]) ?? 0) : 0
        return (major, minor)
    }
}
