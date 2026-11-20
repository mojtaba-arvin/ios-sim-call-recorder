"""Verified Twilio Conference recording retrieval, storage and retention.

Only completed recordings with two independently active WAV channels are
accepted. Channel separation follows Twilio's Conference recording contract:
channel 1 is the first participant; channel 2 is the mix of all other
participants. The production workflow therefore restricts a bridge to two
participants when it promises two-sided channel isolation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import struct
import tempfile
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from bridge_core.object_storage import S3MediaObjectStore
from bridge_core.media_validation import validate_wav
from providers.twilio.events import TwilioEventDecodeError

_RECORDING_SID = re.compile(r"^RE[0-9a-fA-F]{32}$")
_ACCOUNT_SID = re.compile(r"^AC[0-9a-fA-F]{32}$")
_MAX_MEDIA_BYTES = 500 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DualChannelAnalysis:
    duration_seconds: float
    sample_rate_hz: int
    channel_activity: tuple[float, float]
    channel_peak: tuple[float, float]


def analyze_dual_channel_wav(path: str | Path) -> DualChannelAnalysis:
    """Require stereo PCM16 and measurable activity on both independent tracks."""
    try:
        with wave.open(str(path), "rb") as source:
            channels = source.getnchannels()
            width = source.getsampwidth()
            rate = source.getframerate()
            frames = source.getnframes()
            compression = source.getcomptype()
            if channels != 2 or width != 2 or compression != "NONE" or rate < 8000:
                raise ValueError("recording is not stereo PCM16")
            duration = frames / rate
            if duration <= 0 or duration > 24 * 60 * 60:
                raise ValueError("recording duration is outside supported bounds")
            active = [0, 0]
            peak = [0.0, 0.0]
            windows = 0
            frames_per_window = max(1, rate // 2)
            while True:
                raw = source.readframes(frames_per_window)
                if not raw:
                    break
                sample_count = len(raw) // 2
                samples = struct.unpack("<" + "h" * sample_count, raw)
                per_channel = [[], []]
                for index in range(0, len(samples) - 1, 2):
                    per_channel[0].append(samples[index] / 32768.0)
                    per_channel[1].append(samples[index + 1] / 32768.0)
                for channel in range(2):
                    if not per_channel[channel]:
                        continue
                    rms = (sum(value * value for value in per_channel[channel]) / len(per_channel[channel])) ** 0.5
                    peak[channel] = max(peak[channel], max(abs(value) for value in per_channel[channel]))
                    if rms >= 0.003:
                        active[channel] += 1
                windows += 1
    except (wave.Error, EOFError, struct.error) as exc:
        raise ValueError("recording WAV is malformed") from exc
    if windows == 0:
        raise ValueError("recording contains no audio frames")
    ratios = (active[0] / windows, active[1] / windows)
    peaks = (peak[0], peak[1])
    if any(ratio < 0.005 for ratio in ratios) or any(value < 0.01 for value in peaks):
        raise ValueError("both participant channels must contain audible activity")
    return DualChannelAnalysis(duration, rate, ratios, peaks)


class TwilioRecordingMediaIngestor:
    def __init__(
        self, *, account_sid: str, api_username: str, api_password: str,
        provider_account_id: str, connect, resource_resolver,
        object_store: S3MediaObjectStore, retention_days: int = 30,
        max_bytes: int = _MAX_MEDIA_BYTES,
    ):
        if not _ACCOUNT_SID.fullmatch(account_sid):
            raise ValueError("valid Twilio Account SID is required")
        if not api_username or not api_password or not provider_account_id:
            raise ValueError("Twilio API credentials and account mapping are required")
        if not 1 <= retention_days <= 3650:
            raise ValueError("retention_days must be between 1 and 3650")
        if not 1024 <= max_bytes <= _MAX_MEDIA_BYTES:
            raise ValueError("max_bytes exceeds the supported media limit")
        self.account_sid, self.username, self.password = account_sid, api_username, api_password
        self.provider_account_id, self.connect = provider_account_id, connect
        self.resolver, self.object_store = resource_resolver, object_store
        self.retention_days, self.max_bytes = retention_days, max_bytes

    def __call__(self, request, accepted: bool = True) -> None:
        if not request.public_url.rstrip("/").endswith("/recording"):
            return
        fields = self._fields(request.form_parameters or {})
        if fields.get("AccountSid") != self.account_sid or fields.get("RecordingStatus") != "completed":
            return
        recording_sid = fields.get("RecordingSid", "")
        conference_sid = fields.get("ConferenceSid", "")
        if not _RECORDING_SID.fullmatch(recording_sid) or not re.fullmatch(r"CF[0-9a-fA-F]{32}", conference_sid):
            raise TwilioEventDecodeError("recording callback identifiers are invalid")
        session_id, _ = self.resolver(None, conference_sid)
        tenant_id = self.resolver.tenant_for_session(session_id)
        media_id = str(uuid5(NAMESPACE_URL, f"twilio:{self.account_sid}:{recording_sid}"))
        existing = self._existing(recording_sid)
        if existing:
            return
        source = self._download(recording_sid)
        try:
            metadata = validate_wav(source, max_bytes=self.max_bytes)
            participants = self.resolver.expected_participants(session_id)
            try:
                analysis = analyze_dual_channel_wav(source)
                if len(participants) != 2:
                    raise ValueError("dual-channel ownership requires exactly two expected participants")
            except ValueError:
                self._persist_asset(
                    media_id=media_id, tenant_id=tenant_id, session_id=session_id,
                    recording_sid=recording_sid, object_key=None, sha256=metadata.sha256,
                    byte_count=metadata.byte_count, duration=metadata.duration_seconds,
                    sample_rate=metadata.sample_rate_hz, channels=metadata.channel_count,
                    activity=[], channel_map=[], state="rejected",
                    validation_error="dual_channel_verification_failed",
                )
                return
            stored = self.object_store.put_wav(
                tenant_id=tenant_id, session_id=session_id, media_id=media_id, source_path=source,
            )
            self._persist_asset(
                media_id=media_id, tenant_id=tenant_id, session_id=session_id,
                recording_sid=recording_sid, object_key=stored.object_key, sha256=stored.sha256,
                byte_count=stored.byte_count, duration=analysis.duration_seconds,
                sample_rate=analysis.sample_rate_hz, channels=2,
                activity=list(analysis.channel_activity),
                channel_map={"channel_1": participants[0], "channel_2": participants[1]},
                state="verified", validation_error=None,
            )
        finally:
            source.unlink(missing_ok=True)

    def _persist_asset(
        self, *, media_id, tenant_id, session_id, recording_sid, object_key,
        sha256, byte_count, duration, sample_rate, channels, activity,
        channel_map, state, validation_error,
    ):
        expires = datetime.now(timezone.utc) + timedelta(days=self.retention_days)
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO media_assets
                    (media_id, tenant_id, session_id, provider, provider_account_id,
                     provider_recording_sid, object_key, sha256, byte_count, duration_seconds,
                     sample_rate_hz, channel_count, channel_activity, channel_map,
                     verification_state, validation_error, retention_expires_at)
                    VALUES (%s,%s,%s,'twilio',%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)
                    ON CONFLICT (provider, provider_account_id, provider_recording_sid) DO NOTHING""",
                    (media_id, tenant_id, session_id, self.provider_account_id, recording_sid,
                     object_key, sha256, byte_count, duration, sample_rate, channels,
                     json.dumps(activity), json.dumps(channel_map), state, validation_error, expires),
                )

    def _download(self, recording_sid: str) -> Path:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Recordings/{recording_sid}.wav"
        credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode("ascii")
        request = urllib.request.Request(url, headers={"Authorization": "Basic " + credentials})
        fd, filename = tempfile.mkstemp(prefix="twilio-recording-", suffix=".wav")
        os.close(fd)
        path = Path(filename)
        try:
            with urllib.request.urlopen(request, timeout=20) as response, path.open("wb") as output:
                if response.status != 200:
                    raise RuntimeError("Twilio media download failed")
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise ValueError("Twilio recording exceeds media size limit")
                    output.write(chunk)
            if path.stat().st_size == 0:
                raise ValueError("Twilio returned an empty recording")
            return path
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def _existing(self, recording_sid: str) -> bool:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT 1 FROM media_assets
                       WHERE provider='twilio' AND provider_account_id=%s
                       AND provider_recording_sid=%s""",
                    (self.provider_account_id, recording_sid),
                )
                return cur.fetchone() is not None

    @staticmethod
    def _fields(parameters):
        fields = {}
        for key, value in parameters.items():
            if isinstance(value, (tuple, list)):
                if len(value) != 1:
                    raise ValueError("duplicate Twilio recording callback field")
                value = value[0]
            if not isinstance(value, str):
                raise ValueError("invalid Twilio recording callback field")
            fields[key] = value
        return fields


class TwilioMediaRetentionWorker:
    """Retryable two-phase deletion across Twilio and private object storage."""

    def __init__(self, *, connect, client, object_store: S3MediaObjectStore):
        self.connect, self.client, self.object_store = connect, client, object_store

    def run_once(self, *, limit: int = 50) -> int:
        if not 1 <= limit <= 200:
            raise ValueError("retention batch limit is invalid")
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT media_id, tenant_id, session_id, provider_recording_sid,
                              object_key, twilio_deleted_at, object_deleted_at
                       FROM media_assets
                       WHERE retention_expires_at <= now() AND deleted_at IS NULL
                       ORDER BY retention_expires_at LIMIT %s FOR UPDATE SKIP LOCKED""",
                    (limit,),
                )
                rows = cur.fetchall()
        completed = 0
        for media_id, tenant_id, session_id, recording_sid, object_key, twilio_deleted, object_deleted in rows:
            if not twilio_deleted:
                try:
                    self.client.recordings(recording_sid).delete()
                except Exception as exc:
                    if getattr(exc, "status", None) != 404:
                        continue
                with self.connect() as conn:
                    conn.execute("UPDATE media_assets SET twilio_deleted_at=now() WHERE media_id=%s", (media_id,))
            if not object_deleted:
                if object_key:
                    self.object_store.delete(
                        tenant_id=tenant_id, session_id=session_id, media_id=str(media_id),
                    )
                with self.connect() as conn:
                    conn.execute("UPDATE media_assets SET object_deleted_at=now() WHERE media_id=%s", (media_id,))
            with self.connect() as conn:
                conn.execute(
                    """UPDATE media_assets SET deleted_at=now()
                       WHERE media_id=%s AND twilio_deleted_at IS NOT NULL
                       AND object_deleted_at IS NOT NULL""",
                    (media_id,),
                )
            completed += 1
        return completed
