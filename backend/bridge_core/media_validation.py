# Server-side structural validation for untrusted WAV media.
from __future__ import annotations
import hashlib, os, struct
from dataclasses import dataclass
from pathlib import Path

MAX_BYTES = 500 * 1024 * 1024
MAX_DURATION_SECONDS = 24 * 60 * 60
MIN_SAMPLE_RATE = 8_000
MAX_SAMPLE_RATE = 192_000

class MediaValidationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

@dataclass(frozen=True, slots=True)
class ValidatedWAV:
    byte_count: int
    duration_seconds: float
    sample_rate_hz: int
    channel_count: int
    bits_per_sample: int
    encoding: str
    data_bytes: int
    sha256: str

def validate_wav(path: str | os.PathLike[str], *, max_bytes: int = MAX_BYTES) -> ValidatedWAV:
    file_path = Path(path)
    try:
        byte_count = file_path.stat().st_size
    except OSError as exc:
        raise MediaValidationError('media_unavailable') from exc
    if byte_count <= 0 or byte_count > max_bytes:
        raise MediaValidationError('media_size_invalid')
    try:
        with file_path.open('rb') as stream:
            header = stream.read(12)
            if len(header) != 12 or header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                raise MediaValidationError('wav_header_invalid')
            riff_end = 8 + struct.unpack('<I', header[4:8])[0]
            if riff_end < 12 or riff_end != byte_count:
                raise MediaValidationError('wav_riff_length_mismatch')
            fmt = None
            data_size = None
            offset = 12
            while offset + 8 <= riff_end:
                stream.seek(offset)
                chunk_header = stream.read(8)
                if len(chunk_header) != 8:
                    raise MediaValidationError('wav_chunk_header_truncated')
                chunk_id, chunk_length = chunk_header[:4], struct.unpack('<I', chunk_header[4:])[0]
                chunk_data_start = offset + 8
                chunk_end = chunk_data_start + chunk_length + (chunk_length & 1)
                if chunk_end < chunk_data_start or chunk_end > riff_end:
                    raise MediaValidationError('wav_chunk_out_of_bounds')
                if chunk_id == b'fmt ':
                    if fmt is not None or chunk_length < 16:
                        raise MediaValidationError('wav_format_invalid')
                    stream.seek(chunk_data_start)
                    raw = stream.read(16)
                    if len(raw) != 16:
                        raise MediaValidationError('wav_format_truncated')
                    fmt = struct.unpack('<HHIIHH', raw)
                elif chunk_id == b'data':
                    if data_size is not None:
                        raise MediaValidationError('wav_multiple_data_chunks_unsupported')
                    data_size = chunk_length
                offset = chunk_end
            if offset != riff_end or fmt is None or data_size is None or data_size <= 0:
                raise MediaValidationError('wav_chunks_incomplete')
            audio_format, channels, sample_rate, byte_rate, block_align, bits = fmt
            if audio_format not in (1, 3):
                raise MediaValidationError('wav_encoding_unsupported')
            if not 1 <= channels <= 2:
                raise MediaValidationError('wav_channels_unsupported')
            if not MIN_SAMPLE_RATE <= sample_rate <= MAX_SAMPLE_RATE:
                raise MediaValidationError('wav_sample_rate_unsupported')
            if bits not in (8, 16, 24, 32) or (audio_format == 3 and bits != 32):
                raise MediaValidationError('wav_bit_depth_unsupported')
            expected_align = channels * (bits // 8)
            if block_align != expected_align or byte_rate != sample_rate * block_align or data_size % block_align:
                raise MediaValidationError('wav_frame_alignment_invalid')
            duration = data_size / byte_rate
            if duration <= 0 or duration > MAX_DURATION_SECONDS:
                raise MediaValidationError('wav_duration_invalid')
            digest = hashlib.sha256()
            stream.seek(0)
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk: break
                digest.update(chunk)
    except MediaValidationError:
        raise
    except OSError as exc:
        raise MediaValidationError('media_read_failed') from exc
    return ValidatedWAV(byte_count, duration, sample_rate, channels, bits,
                        'pcm' if audio_format == 1 else 'ieee_float', data_size, digest.hexdigest())
