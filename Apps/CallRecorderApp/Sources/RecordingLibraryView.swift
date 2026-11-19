import AVFoundation
import SwiftUI
import UIKit
import UniformTypeIdentifiers

struct RecordingLibraryView: View {
    @AppStorage("recordingRetentionDays") private var retentionDays = 0
    @State private var isImporterPresented = false
    @State private var isImporting = false
    @State private var recordings: [ImportedRecording] = []
    @State private var player: AVPlayer?
    @State private var playingRecordingID: UUID?
    @State private var isPlaying = false
    @State private var playbackCurrentTime = 0.0
    @State private var playbackDuration = 0.0
    @State private var isSeeking = false
    @State private var periodicTimeObserver: Any?
    @State private var playbackRequestID = UUID()
    @State private var shareRequestID = UUID()
    @State private var sharedRecordingID: UUID?
    @State private var sharedRecordingURL: URL?
    @State private var isShareSheetPresented = false
    @State private var statusMessage = "Import an audio file exported from Phone, Notes, or an external recorder."
    @State private var isError = false

    private let importService = RecordingImportService()

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Image(systemName: "waveform")
                    .font(.system(size: 42, weight: .regular))
                    .foregroundStyle(.tint)
                    .accessibilityHidden(true)

                Text("Call Recordings")
                    .font(.largeTitle.weight(.semibold))

                Text(isError ? "Error: \(statusMessage)" : statusMessage)
                    .multilineTextAlignment(.center)
                    .foregroundColor(isError ? .red : .secondary)
                    .accessibilityAddTraits(.updatesFrequently)

                Button {
                    isImporterPresented = true
                } label: {
                    Label("Import Audio File", systemImage: "square.and.arrow.down")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .accessibilityHint("Opens the file picker so you can select an audio recording you exported.")
                .disabled(isImporting)

                if isImporting {
                    ProgressView("Validating and importing…")
                        .accessibilityLabel("Importing recording")
                        .accessibilityValue("Validating and copying the selected audio file")
                }

                if recordings.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "waveform")
                            .font(.title)
                            .foregroundStyle(.secondary)
                            .accessibilityHidden(true)
                        Text("No recordings yet")
                            .font(.headline)
                        Text("Select an audio file to add it to your library.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxHeight: .infinity)
                } else {
                    List {
                        Section("Imported recordings") {
                            ForEach(recordings) { recording in
                                HStack(spacing: 12) {
                                    Image(systemName: "waveform")
                                        .foregroundStyle(.tint)
                                        .accessibilityHidden(true)
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
                                    .accessibilityElement(children: .ignore)
                                    .accessibilityLabel(recordingAccessibilitySummary(recording))
                                    Spacer(minLength: 8)
                                    Button {
                                        shareRecording(recording)
                                    } label: {
                                        Image(systemName: "square.and.arrow.up")
                                            .frame(width: 36, height: 36)
                                    }
                                    .buttonStyle(.borderless)
                                    .accessibilityLabel("Share \(recordingAccessibilityDate(recording))")

                                    Button {
                                        togglePlayback(for: recording)
                                    } label: {
                                        Image(systemName: playingRecordingID == recording.id && isPlaying ? "pause.fill" : "play.fill")
                                            .frame(width: 36, height: 36)
                                    }
                                    .buttonStyle(.borderless)
                                    .accessibilityLabel(playingRecordingID == recording.id && isPlaying ? "Pause \(recordingAccessibilityDate(recording))" : "Play \(recordingAccessibilityDate(recording))")
                                }
                            }
                            .onDelete(perform: deleteRecordings)
                        }
                    }
                    .listStyle(.plain)
                }

                if playingRecordingID != nil {
                    playbackControls
                }

                VStack(spacing: 4) {
                    Text("Files are imported only after you select them. The app does not access Phone or Notes private data.")
                    Text(retentionDescription)
                }
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            }
            .padding()
            .navigationTitle("Library")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Picker("Automatically delete recordings", selection: $retentionDays) {
                            Text("Never").tag(0)
                            Text("After 30 days").tag(30)
                            Text("After 90 days").tag(90)
                            Text("After 1 year").tag(365)
                        }
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Recording retention settings")
                }
            }
            .fileImporter(
                isPresented: $isImporterPresented,
                allowedContentTypes: [.audio],
                allowsMultipleSelection: false,
                onCompletion: handleImportSelection
            )
            .sheet(isPresented: $isShareSheetPresented, onDismiss: {
                shareRequestID = UUID()
                sharedRecordingID = nil
                sharedRecordingURL = nil
            }) {
                if let sharedRecordingURL {
                    ActivityView(activityItems: [sharedRecordingURL])
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .AVPlayerItemDidPlayToEndTime)) { notification in
                guard
                    let currentItem = player?.currentItem,
                    let finishedItem = notification.object as? AVPlayerItem,
                    finishedItem === currentItem
                else {
                    return
                }
                player?.pause()
                player?.seek(to: .zero)
                playbackCurrentTime = 0
                isPlaying = false
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { notification in
                handleAudioInterruption(notification)
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)) { notification in
                handleAudioRouteChange(notification)
            }
            .task {
                _ = await refreshRecordings()
            }
            .onChange(of: retentionDays) { _ in
                Task {
                    guard await refreshRecordings() else { return }
                    statusMessage = retentionDays == 0
                        ? "Automatic deletion is off. Recordings will be kept until you delete them."
                        : "Retention updated. Recordings older than \(retentionDays) days were removed."
                    isError = false
                }
            }
            .onDisappear {
                stopPlayback()
            }
        }
    }

    private var playbackControls: some View {
        VStack(spacing: 8) {
            Slider(
                value: $playbackCurrentTime,
                in: 0...max(playbackDuration, 1),
                onEditingChanged: { editing in
                    isSeeking = editing
                    if !editing {
                        seekToCurrentPosition()
                    }
                }
            )
            .accessibilityLabel("Playback position")
            .accessibilityValue("\(formattedDuration(playbackCurrentTime)) of \(formattedDuration(playbackDuration))")
            .accessibilityHint("Adjust to move to a different position in the recording.")

            HStack {
                Text(formattedDuration(playbackCurrentTime))
                    .accessibilityLabel("Elapsed time")
                Spacer()
                Button {
                    toggleCurrentPlayback()
                } label: {
                    Image(systemName: isPlaying ? "pause.fill" : "play.fill")
                        .frame(minWidth: 44, minHeight: 44)
                }
                .accessibilityLabel(isPlaying ? "Pause playback" : "Resume playback")
                Spacer()
                Text(formattedDuration(playbackDuration))
                    .accessibilityLabel("Total duration")
            }
            .font(.caption.monospacedDigit())
        }
        .padding(.horizontal, 4)
    }

    private var retentionDescription: String {
        retentionDays == 0
            ? "Retention: keep recordings until you delete them."
            : "Retention: automatically delete recordings after \(retentionDays) days."
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

    private func togglePlayback(for recording: ImportedRecording) {
        if playingRecordingID == recording.id {
            toggleCurrentPlayback()
            return
        }

        let requestID = UUID()
        playbackRequestID = requestID
        Task {
            do {
                let url = try await importService.playbackURL(for: recording.id)
                guard playbackRequestID == requestID else { return }
                stopPlayback(invalidatePendingRequests: false)
                let nextPlayer = AVPlayer(url: url)
                player = nextPlayer
                playingRecordingID = recording.id
                playbackCurrentTime = 0
                playbackDuration = recording.durationSeconds
                isPlaying = true
                installPeriodicTimeObserver(on: nextPlayer)
                nextPlayer.play()
                statusMessage = "Playing selected recording. Check that both sides of the conversation are audible."
                isError = false
            } catch {
                guard playbackRequestID == requestID else { return }
                statusMessage = error.localizedDescription
                isError = true
                stopPlayback()
            }
        }
    }

    private func toggleCurrentPlayback() {
        guard let player else { return }
        if isPlaying {
            player.pause()
            isPlaying = false
        } else {
            player.play()
            isPlaying = true
        }
    }

    private func installPeriodicTimeObserver(on player: AVPlayer) {
        removePeriodicTimeObserver()
        periodicTimeObserver = player.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.25, preferredTimescale: 600),
            queue: .main
        ) { time in
            guard !isSeeking else { return }
            let seconds = time.seconds
            guard seconds.isFinite else { return }
            playbackCurrentTime = min(max(seconds, 0), playbackDuration)
        }
    }

    private func removePeriodicTimeObserver() {
        guard let periodicTimeObserver, let player else {
            periodicTimeObserver = nil
            return
        }
        player.removeTimeObserver(periodicTimeObserver)
        self.periodicTimeObserver = nil
    }

    private func seekToCurrentPosition() {
        guard let player, playbackDuration > 0 else { return }
        let target = min(max(playbackCurrentTime, 0), playbackDuration)
        player.seek(
            to: CMTime(seconds: target, preferredTimescale: 600),
            toleranceBefore: .zero,
            toleranceAfter: .zero
        )
    }

    private func stopPlayback(invalidatePendingRequests: Bool = true) {
        if invalidatePendingRequests {
            playbackRequestID = UUID()
        }
        player?.pause()
        removePeriodicTimeObserver()
        player = nil
        playingRecordingID = nil
        isPlaying = false
        playbackCurrentTime = 0
        playbackDuration = 0
        isSeeking = false
    }

    private func handleAudioInterruption(_ notification: Notification) {
        guard
            let userInfo = notification.userInfo,
            let rawType = userInfo[AVAudioSessionInterruptionTypeKey] as? UInt,
            let type = AVAudioSession.InterruptionType(rawValue: rawType)
        else {
            return
        }

        switch type {
        case .began:
            player?.pause()
            isPlaying = false
            statusMessage = "Playback paused because another app or system service interrupted audio. Resume when ready."
            isError = false
        case .ended:
            // Do not resume automatically: the user explicitly chooses when audio starts again.
            isPlaying = false
            statusMessage = "Audio is available again. Press play to resume the recording."
            isError = false
        @unknown default:
            player?.pause()
            isPlaying = false
        }
    }

    private func handleAudioRouteChange(_ notification: Notification) {
        guard
            let rawReason = notification.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
            let reason = AVAudioSession.RouteChangeReason(rawValue: rawReason)
        else {
            return
        }

        if reason == .oldDeviceUnavailable {
            // Avoid unexpectedly routing a private recording to the speaker when
            // headphones or another private output are disconnected.
            player?.pause()
            isPlaying = false
            statusMessage = "Playback paused because the audio output was disconnected. Press play to continue."
            isError = false
        }
    }

    private func shareRecording(_ recording: ImportedRecording) {
        let requestID = UUID()
        shareRequestID = requestID
        Task {
            do {
                let url = try await importService.playbackURL(for: recording.id)
                guard shareRequestID == requestID,
                      recordings.contains(where: { $0.id == recording.id }) else {
                    return
                }
                sharedRecordingID = recording.id
                sharedRecordingURL = url
                isShareSheetPresented = true
                statusMessage = "Choose an app or destination to export this recording."
                isError = false
            } catch {
                guard shareRequestID == requestID else { return }
                statusMessage = error.localizedDescription
                isError = true
            }
        }
    }

    @discardableResult
    private func refreshRecordings() async -> Bool {
        do {
            let updatedRecordings = try await importService.recordings(retentionDays: retentionDays)
            recordings = updatedRecordings
            if let playingRecordingID,
               !updatedRecordings.contains(where: { $0.id == playingRecordingID }) {
                stopPlayback()
            }
            if let sharedRecordingID,
               !updatedRecordings.contains(where: { $0.id == sharedRecordingID }) {
                shareRequestID = UUID()
                isShareSheetPresented = false
                self.sharedRecordingID = nil
                sharedRecordingURL = nil
            }
            return true
        } catch {
            statusMessage = error.localizedDescription
            isError = true
            return false
        }
    }

    private func deleteRecordings(at offsets: IndexSet) {
        let ids = offsets.map { recordings[$0].id }
        // Invalidate any in-flight file lookup before deleting from storage.
        shareRequestID = UUID()
        if let playingRecordingID, ids.contains(playingRecordingID) {
            stopPlayback()
        }
        if let sharedRecordingID, ids.contains(sharedRecordingID) {
            isShareSheetPresented = false
            self.sharedRecordingID = nil
            sharedRecordingURL = nil
        }
        Task {
            do {
                for id in ids {
                    try await importService.deleteRecording(id: id)
                }
                guard await refreshRecordings() else { return }
                statusMessage = "Selected recording(s) deleted."
                isError = false
            } catch {
                statusMessage = "A recording could not be deleted."
                isError = true
            }
        }
    }

    private func recordingAccessibilityDate(_ recording: ImportedRecording) -> String {
        "recording from \(recording.importedAt.formatted(date: .abbreviated, time: .shortened))"
    }

    private func recordingAccessibilitySummary(_ recording: ImportedRecording) -> String {
        "\(recordingAccessibilityDate(recording)), duration \(formattedDuration(recording.durationSeconds)), size \(formattedSize(recording.byteCount))"
    }

    private func formattedDuration(_ duration: Double) -> String {
        let totalSeconds = max(0, Int(duration))
        return String(format: "%d:%02d", totalSeconds / 60, totalSeconds % 60)
    }

    private func formattedSize(_ byteCount: Int64) -> String {
        String(format: "%.1f MB", Double(byteCount) / 1_048_576)
    }
}

private struct ActivityView: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(
            activityItems: activityItems,
            applicationActivities: nil
        )
    }

    func updateUIViewController(
        _ controller: UIActivityViewController,
        context: Context
    ) {}
}
