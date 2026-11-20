from __future__ import annotations
import struct, tempfile, unittest
from pathlib import Path
from bridge_core.media_validation import MediaValidationError, validate_wav

def make_wav(path, *, channels=2, sample_rate=16000, seconds=1, bits=16):
    block = channels * (bits // 8)
    payload = b'\x00' * (sample_rate * seconds * block)
    fmt = struct.pack('<HHIIHH', 1, channels, sample_rate, sample_rate * block, block, bits)
    body = b'WAVE' + b'fmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(payload)) + payload
    path.write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)

class MediaValidationTests(unittest.TestCase):
    def test_valid_wav_reports_bounded_metadata_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'valid.wav'
            make_wav(path)
            result = validate_wav(path)
            self.assertEqual(result.channel_count, 2)
            self.assertEqual(result.sample_rate_hz, 16000)
            self.assertEqual(result.duration_seconds, 1)
            self.assertEqual(len(result.sha256), 64)

    def test_truncated_riff_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'truncated.wav'
            make_wav(path)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaises(MediaValidationError) as error:
                validate_wav(path)
            self.assertEqual(error.exception.code, 'wav_riff_length_mismatch')

    def test_unsupported_channel_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'many-channels.wav'
            make_wav(path, channels=4)
            with self.assertRaises(MediaValidationError) as error:
                validate_wav(path)
            self.assertEqual(error.exception.code, 'wav_channels_unsupported')

    def test_declared_chunk_cannot_extend_past_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad-chunk.wav'
            make_wav(path)
            raw = bytearray(path.read_bytes())
            data_header = raw.index(b'data')
            raw[data_header + 4:data_header + 8] = struct.pack('<I', 0x7fffffff)
            path.write_bytes(raw)
            with self.assertRaises(MediaValidationError) as error:
                validate_wav(path)
            self.assertEqual(error.exception.code, 'wav_chunk_out_of_bounds')

if __name__ == '__main__':
    unittest.main()
