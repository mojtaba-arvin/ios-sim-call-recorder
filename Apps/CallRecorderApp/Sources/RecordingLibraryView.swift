import SwiftUI
import UniformTypeIdentifiers

struct RecordingLibraryView: View {
    @State private var isImporterPresented = false
    @State private var isImporting = false
    @State private var recordings: [ImportedRecording] = []
    @State private var statusMessage = "Import a recording exported from Phone, Notes, or an external recorder."
    @State private var isError = false

    private let importService = RecordingImportService()

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Image(systemName: "waveform")
                    .font(.system(size: 42, weight: .regular))
                    .foregroundStyle(.tint)

                Text("Call Recordings")
                    .font(.largeTitle.weight(.semibold))

                Text(statusMessage)
                    .multilineTextAlignment(.center)
                    .foregroundColor(isError ? .red : .secondary)

                Button {
                    isImporterPresented = true
                } label: {
                    Label("Import Audio File", systemImage: "square.and.arrow.down")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(isImporting)

                if isImporting {
                    ProgressView("Validating and importing…")
                }

                if recordings.isEmpty {
                    ContentUnavailableView(
                        "No Recordings",
                        systemImage: "waveform",
                        description: Text("Select an audio file to add it to your library.")
                    )
                    .frame(maxHeight: .infinity)
                } else {
                    List {
                        Section("Imported recordings") {
                            ForEach(recordings) { recording in
                                HStack(spacing: 12) {
                                    Image(systemName: "waveform")
                                        .foregroundStyle(.tint)
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("Recording")
                                            .font(.body.weight(.medium))
                                        Text(recording.importedAt.formatted(date: .abbreviated, time: .shortened))
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                        Text("\(formattedDuration(recording.durationSeconds)) · \(formattedSize(recording.byteCount))")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                            .onDelete(perform: deleteRecordings)
                        }
                    }
                    .listStyle(.plain)
                }

                Text("Files are imported only after you select them. The app does not access Phone or Notes private data. Swipe a recording to delete it.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding()
            .navigationTitle("Library")
            .navigationBarTitleDisplayMode(.inline)
            .fileImporter(
                isPresented: $isImporterPresented,
                allowedContentTypes: [.audio],
                allowsMultipleSelection: false,
                onCompletion: handleImportSelection
            )
            .task {
                await refreshRecordings()
            }
        }
    }

    private func handleImportSelection(_ result: Result<[URL], Error>) {
        switch result {
        case .failure(let error):
            statusMessage = error.localizedDescription
            isError = true
        case .success(let urls):
            guard let url = urls.first else { return }
            isImporting = true
            isError = false
            Task {
                do {
                    let recording = try await importService.importRecording(
                        from: url,
                        source: .filesApp
                    )
                    recordings.insert(recording, at: 0)
                    statusMessage = "Recording imported and validated successfully."
                } catch {
                    statusMessage = error.localizedDescription
                    isError = true
                }
                isImporting = false
            }
        }
    }

    private func refreshRecordings() async {
        do {
            recordings = try await importService.recordings()
        } catch {
            statusMessage = "The recording library could not be loaded."
            isError = true
        }
    }

    private func deleteRecordings(at offsets: IndexSet) {
        let ids = offsets.map { recordings[$0].id }
        Task {
            do {
                for id in ids {
                    try await importService.deleteRecording(id: id)
                }
                await refreshRecordings()
                statusMessage = "Selected recording(s) deleted."
                isError = false
            } catch {
                statusMessage = "A recording could not be deleted."
                isError = true
            }
        }
    }

    private func formattedDuration(_ duration: Double) -> String {
        let totalSeconds = max(0, Int(duration))
        return String(format: "%d:%02d", totalSeconds / 60, totalSeconds % 60)
    }

    private func formattedSize(_ byteCount: Int64) -> String {
        String(format: "%.1f MB", Double(byteCount) / 1_048_576)
    }
}
