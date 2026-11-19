import SwiftUI
import UniformTypeIdentifiers

struct RecordingLibraryView: View {
    @State private var isImporterPresented = false
    @State private var isImporting = false
    @State private var importedCount = 0
    @State private var statusMessage = "Import a recording exported from Phone, Notes, or an external recorder."
    @State private var isError = false

    private let importService = RecordingImportService()

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: "waveform")
                    .font(.system(size: 48, weight: .regular))
                    .foregroundStyle(.tint)

                Text("Call Recordings")
                    .font(.largeTitle.weight(.semibold))

                Text(statusMessage)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(isError ? .red : .secondary)

                if importedCount > 0 {
                    Label("\(importedCount) recording(s) imported", systemImage: "checkmark.circle")
                        .foregroundStyle(.secondary)
                }

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

                Text("Files are imported only after you select them. The app does not access Phone or Notes private data.")
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
                    try await importService.importRecording(from: url, source: .filesApp)
                    importedCount += 1
                    statusMessage = "Recording imported and validated successfully."
                } catch {
                    statusMessage = error.localizedDescription
                    isError = true
                }
                isImporting = false
            }
        }
    }
}
