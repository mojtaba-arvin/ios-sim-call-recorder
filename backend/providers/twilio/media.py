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
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from bridge_core.object_storage import S3MediaObjectStore
from bridge_core.media_validation import validate_wav, MediaValidationError
from bridge_core.domain import SessionState
from bridge_core.persistence import PostgresBridgeRepository
from providers.twilio.events import TwilioEventDecodeError

_RECORDING_SID = re.compile(r"^RE[0-9a-fA-F]{32}$")
_ACCOUNT_SID = re.compile(r"^AC[0-9a-fA-F]{32}$")
_MAX_MEDIA_BYTES = 500 * 1024 * 1024


def _validate_s3_redirect_url(url: str) -> None:
    """Allow only HTTPS S3 media redirects, never arbitrary redirect targets."""
    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        raise MediaRejected("media_redirect_url_invalid") from None

    suffix = ".amazonaws.com.cn" if hostname.endswith(".amazonaws.com.cn") else ".amazonaws.com"
    aws_suffix = hostname.endswith(suffix) and hostname != suffix.lstrip(".")
    prefix = hostname[:-len(suffix)].rstrip(".") if aws_suffix else ""
    labels = prefix.split(".") if prefix else []

    def valid_region(value: str) -> bool:
        return re.fullmatch(r"[a-z]{2,3}(?:-[a-z]+)*-[0-9]+", value) is not None

    s3_endpoint = False
    for index, label in enumerate(labels):
        tail = labels[index + 1:]
        if label == "s3":
            valid_tail = (
                tail == []
                or (len(tail) == 1 and valid_region(tail[0]))
                or (len(tail) == 2 and tail[0] == "dualstack" and valid_region(tail[1]))
            )
        elif label.startswith("s3-"):
            endpoint = label[3:]
            valid_tail = (
                (valid_region(endpoint) and tail == [])
                or (endpoint == "accelerate" and tail in ([], ["dualstack"]))
            )
        else:
            continue
        if valid_tail:
            s3_endpoint = True
            break

    if (
        parsed.scheme != "https"
        or not hostname
        or not aws_suffix
        or not s3_endpoint
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port not in (None, 443)
    ):
        raise MediaRejected("media_redirect_target_not_allowed")


class _TwilioS3RedirectHandler(urllib.request.HTTPRedirectHandler):
    """Constrain Twilio's media redirect and never forward Twilio credentials."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_s3_redirect_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
            redirected.remove_header("Proxy-Authorization")
            redirected.unredirected_hdrs.pop("Authorization", None)
            redirected.unredirected_hdrs.pop("Proxy-Authorization", None)
        return redirected


class MediaRejected(ValueError):
    def __init__(self, code: str, byte_count: int = 0):
        self.code, self.byte_count = code, byte_count
        super().__init__(code)


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
        token = self._claim(recording_sid, session_id, tenant_id)
        if token is None:
            return
        self._process_claim(recording_sid=recording_sid, session_id=session_id,
                            tenant_id=tenant_id, claim_token=token)

    def _claim(self, recording_sid: str, session_id: str, tenant_id: str) -> str | None:
        """Acquire a durable, idempotent lease before downloading or storing media."""
        media_id = uuid5(NAMESPACE_URL, f"twilio:{self.account_sid}:{recording_sid}")
        object_key = self.object_store._key(
            tenant_id=tenant_id, session_id=session_id, media_id=str(media_id),
        )
        token = uuid5(NAMESPACE_URL, f"twilio-claim:{self.account_sid}:{recording_sid}:{os.urandom(16).hex()}")
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO media_ingestions
                       (provider, provider_account_id, provider_recording_sid, media_id,
                        tenant_id, session_id, object_key, state, claim_token,
                        lease_expires_at, attempts, next_attempt_at, updated_at)
                       VALUES ('twilio',%s,%s,%s,%s,%s,%s,'processing',%s,
                               now()+interval '15 minutes',1,now(),now())
                       ON CONFLICT (provider, provider_account_id, provider_recording_sid)
                       DO UPDATE SET state='processing', claim_token=EXCLUDED.claim_token,
                           lease_expires_at=EXCLUDED.lease_expires_at,
                           attempts=media_ingestions.attempts+1, updated_at=now(),
                           cleanup_required=media_ingestions.cleanup_required
                               OR media_ingestions.state='processing',
                           last_error=NULL
                       WHERE (media_ingestions.state IN ('pending','retry')
                              AND media_ingestions.next_attempt_at <= now())
                          OR (media_ingestions.state='processing'
                              AND media_ingestions.lease_expires_at <= now())
                       RETURNING claim_token""",
                    (self.provider_account_id, recording_sid, media_id, tenant_id,
                     session_id, object_key, token),
                )
                row = cur.fetchone()
                if row:
                    return str(row[0])
                cur.execute(
                    """SELECT state, session_id, tenant_id FROM media_ingestions
                       WHERE provider='twilio' AND provider_account_id=%s
                         AND provider_recording_sid=%s""",
                    (self.provider_account_id, recording_sid),
                )
                existing = cur.fetchone()
                if existing and (existing[1] != session_id or existing[2] != tenant_id):
                    raise ValueError("recording identity is already bound to another session")
                return None

    def _process_claim(self, *, recording_sid: str, session_id: str,
                       tenant_id: str, claim_token: str) -> None:
        media_id = str(uuid5(NAMESPACE_URL, f"twilio:{self.account_sid}:{recording_sid}"))
        source = None
        try:
            if self._finalize_existing_asset(
                recording_sid=recording_sid, session_id=session_id,
                tenant_id=tenant_id, claim_token=claim_token,
            ):
                return
            with self.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT cleanup_required FROM media_ingestions
                           WHERE provider='twilio' AND provider_account_id=%s
                             AND provider_recording_sid=%s AND claim_token=%s""",
                        (self.provider_account_id, recording_sid, UUID(claim_token)),
                    )
                    cleanup_row = cur.fetchone()
                    if cleanup_row is None:
                        raise RuntimeError("media ingestion lease was lost")
            if cleanup_row[0]:
                # A previous attempt may have died during/after S3 upload. Delete
                # only when the durable upload-intent flag says an object may exist.
                self.object_store.delete(
                    tenant_id=tenant_id, session_id=session_id, media_id=media_id,
                )
                with self.connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE media_ingestions SET cleanup_required=false, updated_at=now()
                               WHERE provider='twilio' AND provider_account_id=%s
                                 AND provider_recording_sid=%s AND claim_token=%s""",
                            (self.provider_account_id, recording_sid, UUID(claim_token)),
                        )
                        if cur.rowcount != 1:
                            raise RuntimeError("media ingestion lease was lost")
            try:
                source = self._download(recording_sid)
            except MediaRejected as rejected:
                self._commit_asset(
                    recording_sid=recording_sid, session_id=session_id, tenant_id=tenant_id,
                    claim_token=claim_token, object_key=None, sha256=None,
                    byte_count=rejected.byte_count, duration=None, sample_rate=None,
                    channels=None, activity=[], channel_map=[], state="rejected",
                    validation_error=rejected.code,
                )
                return
            metadata = validate_wav(source, max_bytes=self.max_bytes)
            participants = self.resolver.expected_participants(session_id)
            try:
                analysis = analyze_dual_channel_wav(source)
                if len(participants) != 2:
                    raise ValueError("dual-channel ownership requires exactly two expected participants")
            except ValueError:
                self._commit_asset(
                    recording_sid=recording_sid, session_id=session_id, tenant_id=tenant_id,
                    claim_token=claim_token, object_key=None, sha256=metadata.sha256,
                    byte_count=metadata.byte_count, duration=metadata.duration_seconds,
                    sample_rate=metadata.sample_rate_hz, channels=metadata.channel_count,
                    activity=[], channel_map=[], state="rejected",
                    validation_error="dual_channel_verification_failed",
                )
                return
            self._mark_upload_started(recording_sid, claim_token)
            stored = self.object_store.put_wav(
                tenant_id=tenant_id, session_id=session_id, media_id=media_id, source_path=source,
            )
            self._commit_asset(
                recording_sid=recording_sid, session_id=session_id, tenant_id=tenant_id,
                claim_token=claim_token, object_key=stored.object_key, sha256=stored.sha256,
                byte_count=stored.byte_count, duration=analysis.duration_seconds,
                sample_rate=analysis.sample_rate_hz, channels=2,
                activity=list(analysis.channel_activity),
                channel_map={"channel_1": participants[0], "channel_2": participants[1]},
                state="verified", validation_error=None,
            )
        except MediaValidationError as rejected:
            self._commit_asset(
                recording_sid=recording_sid, session_id=session_id, tenant_id=tenant_id,
                claim_token=claim_token, object_key=None,
                sha256=self._sha256_file(source) if source else None,
                byte_count=source.stat().st_size if source else None,
                duration=None, sample_rate=None, channels=None, activity=[],
                channel_map=[], state="rejected", validation_error=rejected.code,
            )
        except Exception as exc:
            self._schedule_retry(recording_sid, claim_token, exc)
            raise
        finally:
            if source is not None:
                source.unlink(missing_ok=True)

    def _finalize_existing_asset(self, *, recording_sid, session_id, tenant_id, claim_token) -> bool:
        """Adopt an existing committed row and finalize only from its persisted state."""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT media_id, tenant_id, session_id, verification_state
                       FROM media_assets WHERE provider='twilio'
                         AND provider_account_id=%s AND provider_recording_sid=%s
                       FOR UPDATE""",
                    (self.provider_account_id, recording_sid),
                )
                asset = cur.fetchone()
                if asset is None:
                    return False
                if asset[1] != tenant_id or asset[2] != session_id:
                    raise ValueError("authoritative media asset belongs to another session")
                self._finalize_in_transaction(cur, session_id, asset[3] == "verified")
                cur.execute(
                    """UPDATE media_ingestions SET state=%s, claim_token=NULL,
                       lease_expires_at=NULL, cleanup_required=false, updated_at=now()
                       WHERE provider='twilio' AND provider_account_id=%s
                         AND provider_recording_sid=%s AND claim_token=%s""",
                    (asset[3], self.provider_account_id, recording_sid, UUID(claim_token)),
                )
                if cur.rowcount != 1:
                    raise RuntimeError("media ingestion lease was lost")
                return True

    def _commit_asset(self, *, recording_sid, session_id, tenant_id, claim_token,
                      object_key, sha256, byte_count, duration, sample_rate, channels,
                      activity, channel_map, state, validation_error):
        """Commit asset, authoritative state and session transition in one DB transaction."""
        expires = datetime.now(timezone.utc) + timedelta(days=self.retention_days)
        media_id = uuid5(NAMESPACE_URL, f"twilio:{self.account_sid}:{recording_sid}")
        token = UUID(claim_token)
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT state FROM media_ingestions
                       WHERE provider='twilio' AND provider_account_id=%s
                         AND provider_recording_sid=%s AND claim_token=%s FOR UPDATE""",
                    (self.provider_account_id, recording_sid, token),
                )
                if cur.fetchone() is None:
                    raise RuntimeError("media ingestion lease was lost")
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
                cur.execute(
                    """SELECT media_id, tenant_id, session_id, verification_state
                       FROM media_assets WHERE provider='twilio'
                         AND provider_account_id=%s AND provider_recording_sid=%s FOR UPDATE""",
                    (self.provider_account_id, recording_sid),
                )
                authoritative = cur.fetchone()
                if authoritative is None or authoritative[1] != tenant_id or authoritative[2] != session_id:
                    raise RuntimeError("authoritative media asset identity mismatch")
                final_state = authoritative[3]
                self._finalize_in_transaction(cur, session_id, final_state == "verified")
                cur.execute(
                    """UPDATE media_ingestions SET state=%s, claim_token=NULL,
                       lease_expires_at=NULL, cleanup_required=false, updated_at=now(),
                       object_key=COALESCE(%s, object_key)
                       WHERE provider='twilio' AND provider_account_id=%s
                         AND provider_recording_sid=%s AND claim_token=%s""",
                    (final_state, object_key, self.provider_account_id, recording_sid, token),
                )
                if cur.rowcount != 1:
                    raise RuntimeError("media ingestion lease was lost")

    @staticmethod
    def _finalize_in_transaction(cur, session_id: str, verified: bool) -> None:
        cur.execute(
            """SELECT session_id, expected_participants, expected_participant_refs, state,
                      joined_participants, consented_participants, consent_evidence,
                      failure_code, updated_at
               FROM bridge_sessions WHERE session_id=%s FOR UPDATE""",
            (session_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise LookupError("media session does not exist")
        session = PostgresBridgeRepository._session_from_row(row)
        if session.state in {SessionState.COMPLETED, SessionState.DEGRADED}:
            return
        if session.state is not SessionState.VERIFYING:
            raise ValueError("recording media arrived outside verification state")
        target = SessionState.COMPLETED if verified else SessionState.DEGRADED
        failure = None if verified else "media_channel_verification_failed"
        updated = session.transition(target, failure_code=failure, at=datetime.now(timezone.utc))
        cur.execute(
            "UPDATE bridge_sessions SET state=%s, failure_code=%s, updated_at=%s WHERE session_id=%s",
            (updated.state.value, updated.failure_code, updated.updated_at, session_id),
        )

    def _mark_upload_started(self, recording_sid: str, claim_token: str) -> None:
        """Persist cleanup intent before issuing the external S3 upload."""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE media_ingestions SET cleanup_required=true, updated_at=now()
                       WHERE provider='twilio' AND provider_account_id=%s
                         AND provider_recording_sid=%s AND claim_token=%s""",
                    (self.provider_account_id, recording_sid, UUID(claim_token)),
                )
                if cur.rowcount != 1:
                    raise RuntimeError("media ingestion lease was lost")

    def _schedule_retry(self, recording_sid: str, claim_token: str, exc: Exception) -> None:
        # Do not persist exception text: it may contain provider URLs or credentials.
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE media_ingestions
                       SET state=CASE WHEN attempts >= 8 THEN 'manual_cleanup' ELSE 'retry' END,
                           claim_token=NULL, lease_expires_at=NULL,
                           next_attempt_at=now()+make_interval(secs =>
                               LEAST(300, power(2, LEAST(attempts,8))::int)),
                           last_error=%s, updated_at=now()
                       WHERE provider='twilio' AND provider_account_id=%s
                         AND provider_recording_sid=%s AND claim_token=%s""",
                    (type(exc).__name__[:80], self.provider_account_id, recording_sid, UUID(claim_token)),
                )

    def recover_once(self, *, limit: int = 25) -> int:
        """Reclaim expired leases and due retries without a new provider callback."""
        if not 1 <= limit <= 100:
            raise ValueError("recovery batch limit is invalid")
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT provider_recording_sid, session_id, tenant_id
                       FROM media_ingestions
                       WHERE (state='retry' AND next_attempt_at <= now())
                          OR (state='processing' AND lease_expires_at <= now())
                       ORDER BY updated_at LIMIT %s""",
                    (limit,),
                )
                rows = cur.fetchall()
        recovered = 0
        for recording_sid, session_id, tenant_id in rows:
            token = self._claim(recording_sid, session_id, tenant_id)
            if token is None:
                continue
            self._process_claim(recording_sid=recording_sid, session_id=session_id,
                                tenant_id=tenant_id, claim_token=token)
            recovered += 1
        return recovered

    def _download(self, recording_sid: str) -> Path:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Recordings/{recording_sid}.wav?RequestedChannels=2"
        credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode("ascii")
        request = urllib.request.Request(url, headers={"Authorization": "Basic " + credentials})
        fd, filename = tempfile.mkstemp(prefix="twilio-recording-", suffix=".wav")
        os.close(fd)
        path = Path(filename)
        try:
            opener = urllib.request.build_opener(_TwilioS3RedirectHandler())
            with opener.open(request, timeout=20) as response, path.open("wb") as output:
                if response.status != 200:
                    raise RuntimeError("Twilio media download failed")
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise MediaRejected("media_size_exceeded", total)
                    output.write(chunk)
            if path.stat().st_size == 0:
                raise MediaRejected("media_empty", 0)
            return path
        except Exception:
            path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _existing(self, recording_sid: str) -> str | None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT verification_state FROM media_assets
                       WHERE provider='twilio' AND provider_account_id=%s
                       AND provider_recording_sid=%s""",
                    (self.provider_account_id, recording_sid),
                )
                row = cur.fetchone()
                return row[0] if row else None

    def _finalize_session(self, session_id: str, *, verified: bool) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT session_id, expected_participants, expected_participant_refs, state,
                              joined_participants, consented_participants, consent_evidence,
                              failure_code, updated_at
                       FROM bridge_sessions WHERE session_id=%s FOR UPDATE""",
                    (session_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise LookupError("media session does not exist")
                session = PostgresBridgeRepository._session_from_row(row)
                if session.state in {SessionState.COMPLETED, SessionState.DEGRADED}:
                    return
                if session.state is not SessionState.VERIFYING:
                    raise ValueError("recording media arrived outside verification state")
                target = SessionState.COMPLETED if verified else SessionState.DEGRADED
                failure = None if verified else "media_channel_verification_failed"
                updated = session.transition(
                    target, failure_code=failure, at=datetime.now(timezone.utc),
                )
                cur.execute(
                    "UPDATE bridge_sessions SET state=%s, failure_code=%s, updated_at=%s WHERE session_id=%s",
                    (updated.state.value, updated.failure_code, updated.updated_at, session_id),
                )

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
