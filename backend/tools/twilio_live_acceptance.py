#!/usr/bin/env python3
"""Opt-in end-to-end Twilio acceptance probe against an explicitly named staging API.

This script places real PSTN calls. It is inert unless --execute and all
staging/approval environment guards are present.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from providers.twilio.media import analyze_dual_channel_wav  # noqa: E402

_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
_TERMINAL = {"completed", "failed", "degraded", "cancelled"}


class HarnessError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise HarnessError(f"missing required environment variable: {name}")
    return value


def _json_request(base_url: str, token: str, method: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise HarnessError("API response exceeded 1 MiB")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        # Do not echo response bodies: provider errors can contain identifiers.
        raise HarnessError(f"API request failed with HTTP {exc.code}: {method} {path}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HarnessError(f"API request failed: {type(exc).__name__}") from None


def _download_verified_media(url: str, destination: str):
    if not url.startswith("https://"):
        raise HarnessError("media download URL must use HTTPS")
    request = urllib.request.Request(url, headers={"Accept": "audio/wav"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, open(destination, "wb") as target:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 500 * 1024 * 1024:
                    raise HarnessError("media exceeded 500 MiB safety limit")
                target.write(chunk)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HarnessError(f"media download failed: {type(exc).__name__}") from None


def run(args) -> dict:
    if not args.execute:
        return {
            "status": "dry-run",
            "message": "No API request or PSTN call was made. Re-run with --execute after staging approval.",
        }

    if _required_env("BRIDGE_ENVIRONMENT").lower() != "staging":
        raise HarnessError("BRIDGE_ENVIRONMENT must be exactly 'staging'")
    if _required_env("TWILIO_LIVE_TEST_APPROVED").lower() != "true":
        raise HarnessError("TWILIO_LIVE_TEST_APPROVED=true is required for real PSTN calls")

    base_url = _required_env("BRIDGE_BASE_URL").rstrip("/")
    if not base_url.startswith("https://"):
        raise HarnessError("BRIDGE_BASE_URL must use HTTPS")
    from urllib.parse import urlsplit
    hostname = (urlsplit(base_url).hostname or "").lower()
    if "staging" not in hostname or "prod" in hostname:
        raise HarnessError("BRIDGE_BASE_URL hostname must explicitly identify a non-production staging host")
    token = _required_env("BRIDGE_API_TOKEN")
    phone_a = _required_env("TWILIO_TEST_PARTICIPANT_A")
    phone_b = _required_env("TWILIO_TEST_PARTICIPANT_B")
    if not _E164.fullmatch(phone_a) or not _E164.fullmatch(phone_b) or phone_a == phone_b:
        raise HarnessError("two distinct E.164 test participant numbers are required")
    if not 60 <= args.timeout_seconds <= 1800:
        raise HarnessError("timeout must be between 60 and 1800 seconds")
    if args.expect_state not in {"completed", "failed"}:
        raise HarnessError("expected state must be completed or failed")

    run_id = uuid4().hex
    refs = [f"live-test-{run_id}-a", f"live-test-{run_id}-b"]
    for ref, phone in zip(refs, (phone_a, phone_b)):
        _json_request(base_url, token, "PUT", f"/v1/participants/{ref}/address", {"phone_number": phone})

    created = _json_request(
        base_url, token, "POST", "/v1/bridge-sessions", {"participant_refs": refs}
    )
    session_id = created.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise HarnessError("session creation response did not include a session ID")

    deadline = time.monotonic() + args.timeout_seconds
    latest = created
    while time.monotonic() < deadline:
        latest = _json_request(
            base_url, token, "GET", f"/v1/bridge-sessions/{session_id}"
        )
        state = latest.get("state")
        if state in _TERMINAL:
            break
        time.sleep(args.poll_seconds)
    else:
        raise HarnessError(
            f"session did not reach a terminal state within {args.timeout_seconds}s; "
            f"inspect the private staging logs and cancel/reconcile manually"
        )

    state = latest.get("state")
    if state != args.expect_state:
        raise HarnessError(
            f"unexpected terminal state: expected {args.expect_state}, received {state}"
        )

    evidence = {
        "status": "passed",
        "scenario": "two-party-consent-and-recording" if state == "completed" else "negative-consent-or-call-outcome",
        "session_id": session_id,
        "terminal_state": state,
        "expected_participants": latest.get("expected_participants"),
        "consented_participants": latest.get("consented_participants"),
        "joined_participants": latest.get("joined_participants"),
        "failure_code": latest.get("failure_code"),
    }

    if state == "completed":
        if latest.get("expected_participants") != 2 or latest.get("consented_participants") != 2:
            raise HarnessError("completed session did not prove consent from both expected participants")
        media = _json_request(
            base_url, token, "GET", f"/v1/bridge-sessions/{session_id}/media"
        )
        url = media.get("download_url")
        if not isinstance(url, str):
            raise HarnessError("verified media response did not include a download URL")
        with tempfile.NamedTemporaryFile(prefix="twilio-live-", suffix=".wav", delete=False) as handle:
            media_path = handle.name
        try:
            _download_verified_media(url, media_path)
            analysis = analyze_dual_channel_wav(media_path)
        finally:
            try:
                os.unlink(media_path)
            except FileNotFoundError:
                pass
        evidence.update({
            "media_sha256": media.get("sha256"),
            "media_channel_count": media.get("channel_count"),
            "media_duration_seconds": analysis.duration_seconds,
            "channel_activity": list(analysis.channel_activity),
            "media_downloaded_and_verified": True,
            "retention_cleanup": "pending retention worker; verify Twilio and S3 deletion separately",
        })
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="perform real PSTN calls; requires explicit staging approval")
    parser.add_argument("--expect-state", choices=("completed", "failed"), default="completed")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args()
    try:
        result = run(args)
    except HarnessError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
