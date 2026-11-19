public enum RecordingPathwayRegistryError: Error, Equatable, Sendable {
    case duplicatePathway(RecordingPathway)
}

/// Evaluates independent adapters concurrently while preserving registration order.
public struct RecordingPathwayRegistry: Sendable {
    private let adapters: [any RecordingPathwayAdapter]

    public init(adapters: [any RecordingPathwayAdapter]) throws {
        var seen = Set<RecordingPathway>()
        for adapter in adapters {
            guard seen.insert(adapter.pathway).inserted else {
                throw RecordingPathwayRegistryError.duplicatePathway(adapter.pathway)
            }
        }
        self.adapters = adapters
    }

    public func capabilities(
        for context: DeviceCompatibilityContext
    ) async -> [PathwayCapability] {
        await withTaskGroup(
            of: (Int, PathwayCapability).self,
            returning: [PathwayCapability].self
        ) { group in
            for (index, adapter) in adapters.enumerated() {
                group.addTask {
                    (index, await adapter.capability(for: context))
                }
            }

            var results: [Int: PathwayCapability] = [:]
            for await (index, capability) in group {
                results[index] = capability
            }
            return adapters.indices.compactMap { results[$0] }
        }
    }
}
