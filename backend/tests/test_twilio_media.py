from __future__ import annotations

import math
import os
import struct
import tempfile
import unittest
import wave

from providers.twilio.media import analyze_dual_channel_wav


def write_wav(path, channels=2, active=True):
    rate = 8000
    with wave.open(path, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        frames = []
        for index in range(rate):
            left = int(9000 * math.sin(2 * math.pi * 440 * index / rate)) if active else 0
            right = int(7000 * math.sin(2 * math.pi * 220 * index / rate)) if active else 0
            frames.extend((left, right) if channels == 2 else (left,))
        output.writeframes(struct.pack("<" + "h" * len(frames), *frames))


class DualChannelAnalysisTests(unittest.TestCase):
    def test_two_independently_active_channels_are_accepted(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
            path = temp.name
        try:
            write_wav(path)
            result = analyze_dual_channel_wav(path)
            self.assertEqual(result.sample_rate_hz, 8000)
            self.assertEqual(result.duration_seconds, 1.0)
            self.assertEqual(len(result.channel_activity), 2)
            self.assertGreater(result.channel_activity[0], 0)
            self.assertGreater(result.channel_activity[1], 0)
        finally:
            os.unlink(path)

    def test_mono_recording_is_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
            path = temp.name
        try:
            write_wav(path, channels=1)
            with self.assertRaises(ValueError):
                analyze_dual_channel_wav(path)
        finally:
            os.unlink(path)

    def test_silent_stereo_recording_is_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
            path = temp.name
        try:
            write_wav(path, active=False)
            with self.assertRaises(ValueError):
                analyze_dual_channel_wav(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
