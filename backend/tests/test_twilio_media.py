from __future__ import annotations

import math
import os
import struct
import tempfile
import unittest
import wave
from unittest.mock import patch

from providers.twilio.media import (
    MediaRejected, TwilioRecordingMediaIngestor, _TwilioS3RedirectHandler,
)

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


class DownloadRequestTests(unittest.TestCase):
    class Response:
        status = 200
        def __init__(self, chunks):
            self.chunks = list(chunks)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return self.chunks.pop(0) if self.chunks else b""

    def make_ingestor(self, max_bytes=1024):
        return TwilioRecordingMediaIngestor(
            account_sid="AC" + "a" * 32,
            api_username="api-user",
            api_password="api-secret",
            provider_account_id="provider-account",
            connect=lambda: None,
            resource_resolver=None,
            object_store=object(),
            max_bytes=max_bytes,
        )

    def test_redirect_handler_rejects_non_s3_targets(self):
        handler = _TwilioS3RedirectHandler()
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://api.twilio.com/recording", headers={"Authorization": "Basic secret"}
        )
        for target in (
            "http://bucket.s3.us-east-1.amazonaws.com/object",
            "https://example.com/object",
            "https://bucket.s3.us-east-1.amazonaws.com.evil.test/object",
            "https://user:pass@bucket.s3.us-east-1.amazonaws.com/object",
            "https://bucket.s3.us-east-1.amazonaws.com:8443/object",
        ):
            with self.subTest(target=target), self.assertRaises(MediaRejected):
                handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_redirect_handler_allows_s3_and_strips_twilio_credentials(self):
        handler = _TwilioS3RedirectHandler()
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://api.twilio.com/recording", headers={"Authorization": "Basic secret"}
        )
        redirected = handler.redirect_request(
            request, None, 302, "Found", {},
            "https://bucket.s3.eu-central-1.amazonaws.com/object?signature=redacted",
        )
        self.assertEqual(redirected.full_url, "https://bucket.s3.eu-central-1.amazonaws.com/object?signature=redacted")
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertNotIn("Authorization", redirected.unredirected_hdrs)

    def test_download_requests_dual_channel_media(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
            path = temp.name
        os.unlink(path)
        response = self.Response([b"RIFF" + b"x" * 40])
        captured = {}
        class FakeOpener:
            def open(self, request, timeout):
                captured["url"] = request.full_url
                captured["timeout"] = timeout
                return response
        with patch("urllib.request.build_opener", return_value=FakeOpener()) as build_opener:
            downloaded = self.make_ingestor()._download("RE" + "b" * 32)
        try:
            self.assertIn("RequestedChannels=2", captured["url"])
            self.assertEqual(captured["timeout"], 20)
            self.assertIsInstance(build_opener.call_args.args[0], _TwilioS3RedirectHandler)
            self.assertTrue(os.path.exists(downloaded))
        finally:
            downloaded.unlink(missing_ok=True)

    def test_oversized_download_is_a_durable_rejection_signal(self):
        response = self.Response([b"x" * 1025])
        with patch("urllib.request.build_opener", return_value=type("FakeOpener", (), {"open": lambda self, request, timeout: response})()):
            with self.assertRaises(MediaRejected) as caught:
                self.make_ingestor(max_bytes=1024)._download("RE" + "b" * 32)
        self.assertEqual(caught.exception.code, "media_size_exceeded")
        self.assertEqual(caught.exception.byte_count, 1025)


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
