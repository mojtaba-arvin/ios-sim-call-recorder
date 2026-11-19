import Foundation

/// Opaque, auditable evidence that every expected participant consented.
public struct ConsentEvidence: Equatable, Sendable {
    public let reference: String
    public let policyVersion: String
    public let participantIdentifiers: Set<String>
    public let consentTimestamps: [String: Date]
    public let disclosureTimestamp: Date

    public init(
        reference: String,
        policyVersion: String,
        participantIdentifiers: Set<String>,
        consentTimestamps: [String: Date],
        disclosureTimestamp: Date
    ) {
        self.reference = reference
        self.policyVersion = policyVersion
        self.participantIdentifiers = participantIdentifiers
        self.consentTimestamps = consentTimestamps
        self.disclosureTimestamp = disclosureTimestamp
    }

    /// Structural checks only. A trusted verifier must still validate the
    /// evidence reference against the authoritative consent/audit store.
    public var isStructurallyComplete: Bool {
        let normalizedReference = reference.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedPolicy = policyVersion.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedReference.isEmpty,
              !normalizedPolicy.isEmpty,
              !participantIdentifiers.isEmpty,
              Set(consentTimestamps.keys) == participantIdentifiers else {
            return false
        }

        return consentTimestamps.values.allSatisfy { $0 >= disclosureTimestamp }
    }
}

public protocol ConsentEvidenceVerifying: Sendable {
    /// Verifies authenticity, policy version, participant coverage and audit
    /// persistence. Implementations should fail closed on unavailable storage.
    func verify(_ evidence: ConsentEvidence, sessionID: UUID) async throws -> Bool
}
