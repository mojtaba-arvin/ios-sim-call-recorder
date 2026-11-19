#!/usr/bin/env python3
"""Privacy-preserving PCM WAV quality metrics for manual call-audio validation."""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import wave
from pathlib import Path


def _decode_sample(data: bytes, width: int) -> float:
    if width == 1:
        return (data[0] - 128) / 128.0
    if width == 2:
        return struct.unpack("<h", data)[0] / 32768.0
    if width == 3:
        value = int.from_bytes(data, byteorder="little", signed=False)
        if value & 0x800000:
            value -= 1 << 24
        return value / 8_388_608.0
    if width == 4:
        return struct.unpack("<i", data)[0] / 2_147_483_648.0
    raise ValueError("Unsupported PCM sample width")


def _dbfs(amplitude: float) -> float | None:
    if amplitude <= 0:
        return None
    return round(20.0 * math.log10(amplitude), 2)


def _read_window(
    source: wave.Wave_read,
    frame_count: int,
    channels: int,
    sample_width: int,
    silence_threshold: float,
) -> tuple[list[float], list[float], list[int], int, list[int]]:
    raw = source.readframes(frame_count)
    frame_size = channels * sample_width
    complete_frames = len(raw) // frame_size
    sumsquares = [0.0] * channels
    peaks = [0.0] * channels
    clipped = [0] * channels

    for frame_index in range(complete_frames):
        frame_offset = frame_index * frame_size
        for channel in range(channels):
            offset = frame_offset + channel * sample_width
            sample = _decode_sample(raw[offset : offset + sample_width], sample_width)
            magnitude = abs(sample)
            sumsquares[channel] += sample * sample
            peaks[channel] = max(peaks[channel], magnitude)
            if magnitude >= 0.999:
                clipped[channel] += 1

    rms = [
        math.sqrt(total / complete_frames) if complete_frames else 0.0
        for total in sumsquares
    ]
    silent = [1 if value < silence_threshold else 0 for value in rms]
    return sumsquares, peaks, clipped, complete_frames, silent


def analyze_wav(
    path: Path,
    *,
    silence_threshold_dbfs: float = -50.0,
    window_ms: int = 100,
) -> dict[str, object]:
    if not -120.0 <= silence_threshold_dbfs < 0.0:
        raise ValueError("Silence threshold must be between -120 and 0 dBFS")
    if not 10 <= window_ms <= 2_000:
        raise ValueError("Window size must be between 10 and 2000 milliseconds")

    silence_threshold = 10.0 ** (silence_threshold_dbfs / 20.0)
    with wave.open(str(path), "rb") as source:
        if source.getcomptype() != "NONE":
            raise ValueError("Only uncompressed PCM WAV is supported")
        channels = source.getnchannels()
        sample_rate = source.getframerate()
        sample_width = source.getsampwidth()
        declared_frames = source.getnframes()
        if channels < 1 or channels > 8:
            raise ValueError("WAV must contain between 1 and 8 channels")
        if sample_rate <= 0 or declared_frames <= 0:
            raise ValueError("WAV must contain audio frames and a valid sample rate")
        if sample_width not in (1, 2, 3, 4):
            raise ValueError("Unsupported PCM sample width")

        window_frames = max(1, round(sample_rate * window_ms / 1000.0))
        total_sumsquares = [0.0] * channels
        total_peaks = [0.0] * channels
        total_clipped = [0] * channels
        total_samples = 0
        silent_windows = [0] * channels
        total_windows = 0
        current_silent_windows = [0] * channels
        longest_silent_windows = [0] * channels

        while True:
            sumsquares, peaks, clipped, frames, silent = _read_window(
                source,
                window_frames,
                channels,
                sample_width,
                silence_threshold,
            )
            if frames == 0:
                break
            total_windows += 1
            total_samples += frames
            for channel in range(channels):
                total_sumsquares[channel] += sumsquares[channel]
                total_peaks[channel] = max(total_peaks[channel], peaks[channel])
                total_clipped[channel] += clipped[channel]
                if silent[channel]:
                    silent_windows[channel] += 1
                    current_silent_windows[channel] += 1
                    longest_silent_windows[channel] = max(
                        longest_silent_windows[channel],
                        current_silent_windows[channel],
                    )
                else:
                    current_silent_windows[channel] = 0

    if total_samples == 0:
        raise ValueError("WAV contains no decodable samples")

    channel_results = []
    for channel in range(channels):
        rms = math.sqrt(total_sumsquares[channel] / total_samples)
        channel_results.append(
            {
                "channel_index": channel,
                "rms_dbfs": _dbfs(rms),
                "peak_dbfs": _dbfs(total_peaks[channel]),
                "clipped_sample_ratio": round(total_clipped[channel] / total_samples, 6),
                "silent_window_ratio": round(silent_windows[channel] / max(total_windows, 1), 6),
                "longest_silent_gap_seconds": round(
                    longest_silent_windows[channel] * window_ms / 1000.0,
                    3,
                ),
            }
        )

    return {
        "format": "PCM WAV",
        "sample_rate_hz": sample_rate,
        "channel_count": channels,
        "duration_seconds": round(total_samples / sample_rate, 3),
        "sample_width_bits": sample_width * 8,
        "analysis": {
            "window_ms": window_ms,
            "silence_threshold_dbfs": silence_threshold_dbfs,
            "channels": channel_results,
        },
        "limitations": [
            "Signal metrics do not identify which participant is speaking.",
            "Non-silent audio does not prove intelligible speech or participant consent.",
            "Channel count does not prove speaker separation.",
            "This tool analyzes local uncompressed PCM WAV files only.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav_file", type=Path)
    parser.add_argument("--silence-threshold-dbfs", type=float, default=-50.0)
    parser.add_argument("--window-ms", type=int, default=100)
    args = parser.parse_args()

    try:
        result = analyze_wav(
            args.wav_file,
            silence_threshold_dbfs=args.silence_threshold_dbfs,
            window_ms=args.window_ms,
        )
    except (OSError, EOFError, wave.Error, ValueError, struct.error):
        print(
            "Unable to analyze this file. Supply a valid, uncompressed PCM WAV file.",
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
