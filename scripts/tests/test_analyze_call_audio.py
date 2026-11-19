from __future__ import annotations

import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyze_call_audio import analyze_wav


class CallAudioAnalysisTests(unittest.TestCase):
    def write_wav(self, path: Path, channels: list[list[int]], sample_rate: int = 8_000) -> None:
        frame_count = len(channels[0])
        self.assertTrue(all(len(channel) == frame_count for channel in channels))
        with wave.open(str(path), "wb") as output:
            output.setnchannels(len(channels))
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            frames = bytearray()
            for frame in range(frame_count):
                for channel in channels:
                    frames.extend(struct.pack("<h", channel[frame]))
            output.writeframes(bytes(frames))

    def test_reports_stereo_channel_signal_and_duration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            count = 8_000
            left = [int(16_000 * math.sin(2 * math.pi * 440 * i / 8_000)) for i in range(count)]
            right = [int(8_000 * math.sin(2 * math.pi * 880 * i / 8_000)) for i in range(count)]
            self.write_wav(path, [left, right])

            result = analyze_wav(path)

            self.assertEqual(result["channel_count"], 2)
            self.assertEqual(result["duration_seconds"], 1.0)
            metrics = result["analysis"]["channels"]
            self.assertLess(metrics[0]["rms_dbfs"], -8)
            self.assertGreater(metrics[0]["rms_dbfs"], -11)
            self.assertGreater(metrics[1]["rms_dbfs"], metrics[0]["rms_dbfs"] - 8)
            self.assertEqual(metrics[0]["silent_window_ratio"], 0.0)

    def test_reports_longest_silent_gap_in_frames_not_rounded_windows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            active = [int(12_000 * math.sin(2 * math.pi * 330 * i / 8_000)) for i in range(4_000)]
            self.write_wav(path, [[0] * 4_000 + active])

            result = analyze_wav(path)

            self.assertEqual(result["analysis"]["channels"][0]["longest_silent_gap_seconds"], 0.5)

    def test_identifies_a_silent_channel_without_claiming_speaker_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            count = 4_000
            active = [int(12_000 * math.sin(2 * math.pi * 330 * i / 8_000)) for i in range(count)]
            self.write_wav(path, [active, [0] * count])

            result = analyze_wav(path)

            self.assertEqual(result["analysis"]["channels"][1]["silent_window_ratio"], 1.0)
            self.assertIn("do not identify which participant", result["limitations"][0])

    def test_reports_clipping_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            self.write_wav(path, [[32767] * 800])

            result = analyze_wav(path)

            self.assertEqual(result["analysis"]["channels"][0]["clipped_sample_ratio"], 1.0)

    def test_rejects_truncated_wav_payload_instead_of_reporting_shorter_duration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.wav"
            self.write_wav(path, [[1_000] * 8_000])
            path.write_bytes(path.read_bytes()[:-512])

            with self.assertRaisesRegex(ValueError, "truncated or inconsistent"):
                analyze_wav(path)

    def test_rejects_invalid_silence_threshold_and_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            self.write_wav(path, [[100] * 800])
            with self.assertRaises(ValueError):
                analyze_wav(path, silence_threshold_dbfs=0)
            with self.assertRaises(ValueError):
                analyze_wav(path, window_ms=1)

    def test_rejects_malformed_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.wav"
            path.write_bytes(b"not a wave file")
            with self.assertRaises((wave.Error, EOFError)):
                analyze_wav(path)


if __name__ == "__main__":
    unittest.main()
