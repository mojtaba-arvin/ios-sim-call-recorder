from __future__ import annotations

import hashlib
import json
import unittest

from bridge_core.domain import BridgeSession, InvalidTransition, SessionState
from bridge_core.http_api import BearerTokenAuthenticator, BridgeSessionsASGI


class FakeRepository:
    def __init__(self):
        self.sessions = {}
        self.owners = {}
        self.commands = []

    def ping(self):
        return None

    def create_session(self, session, *, tenant_id, commands=()):
        self.sessions[session.session_id] = session
        self.owners[session.session_id] = tenant_id
        self.commands.extend(commands)

    def get_session(self, session_id, *, tenant_id):
        if self.owners.get(session_id) != tenant_id:
            return None
        return self.sessions.get(session_id)

    def cancel_session(self, session_id, *, tenant_id):
        session = self.get_session(session_id, tenant_id=tenant_id)
        if session is None:
            raise KeyError(session_id)
        if session.state not in {SessionState.CREATED, SessionState.AWAITING_USER_ACTION}:
            raise InvalidTransition("provider activity may already exist")
        updated = session.transition(SessionState.CANCELLED)
        self.sessions[session_id] = updated
        return updated


class FakeAddressVault:
    def __init__(self):
        self.entries = {}
        self.deleted = []
    def store(self, *, tenant_id, participant_ref, address):
        self.entries[(tenant_id, participant_ref)] = address
    def delete(self, *, tenant_id, participant_ref):
        self.entries.pop((tenant_id, participant_ref), None)
        self.deleted.append((tenant_id, participant_ref))


class HTTPAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.token = "a" * 48
        self.repo = FakeRepository()
        self.app = BridgeSessionsASGI(
            repository=self.repo,
            authenticator=BearerTokenAuthenticator({
                hashlib.sha256(self.token.encode()).hexdigest(): "tenant-a",
            }),
        )

    async def request(self, method, path, *, token=None, body=None):
        raw = json.dumps(body).encode() if body is not None else b""
        messages = [{"type": "http.request", "body": raw, "more_body": False}]
        sent = []

        async def receive():
            return messages.pop(0)

        async def send(message):
            sent.append(message)

        headers = []
        if token is not None:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        await self.app(
            {"type": "http", "method": method, "path": path, "headers": headers, "query_string": b""},
            receive,
            send,
        )
        start = next(item for item in sent if item["type"] == "http.response.start")
        response = next(item for item in sent if item["type"] == "http.response.body")
        return start["status"], json.loads(response["body"])

    async def test_health_endpoints_are_available_without_tenant_credentials(self):
        status, payload = await self.request("GET", "/health/live")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

        status, payload = await self.request("GET", "/health/ready")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ready")

    async def test_authentication_required(self):
        status, payload = await self.request("GET", "/v1/bridge-sessions/unknown")
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "unauthorized")

    async def test_create_read_and_cancel_are_tenant_scoped(self):
        status, created = await self.request(
            "POST", "/v1/bridge-sessions", token=self.token,
            body={"participant_refs": ["opaque-a", "opaque-b"]},
        )
        self.assertEqual(status, 201)
        session_id = created["session_id"]
        self.assertEqual(created["state"], "created")
        self.assertNotIn("opaque-a", json.dumps(created))

        status, loaded = await self.request(
            "GET", f"/v1/bridge-sessions/{session_id}", token=self.token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(loaded["session_id"], session_id)

        other_token = "b" * 48
        self.app.authenticator = BearerTokenAuthenticator({
            hashlib.sha256(other_token.encode()).hexdigest(): "tenant-b",
        })
        status, payload = await self.request(
            "GET", f"/v1/bridge-sessions/{session_id}", token=other_token,
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "not_found")

    async def test_address_vault_provisioning_is_tenant_scoped_and_never_echoes_number(self):
        self.app.address_vault = FakeAddressVault()
        status, body = await self.request(
            "PUT", "/v1/participants/participant-opaque/address", token=self.token,
            body={"phone_number": "+14155550123"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "stored"})
        self.assertEqual(
            self.app.address_vault.entries[("tenant-a", "participant-opaque")],
            "+14155550123",
        )
        self.assertNotIn("+14155550123", json.dumps(body))
        status, body = await self.request(
            "DELETE", "/v1/participants/participant-opaque/address", token=self.token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "deleted"})
        self.assertEqual(self.app.address_vault.deleted, [("tenant-a", "participant-opaque")])

    async def test_create_session_atomically_enqueues_one_consent_command_per_participant(self):
        from providers.twilio.factory import TwilioConsentCommandFactory
        self.app.initial_commands = TwilioConsentCommandFactory(provider_account_id="twilio-main")
        status, created = await self.request(
            "POST", "/v1/bridge-sessions", token=self.token,
            body={"participant_refs": ["opaque-a", "opaque-b"]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["state"], "awaiting_user_action")
        self.assertEqual(len(self.repo.commands), 2)
        self.assertEqual({item.command_type for item in self.repo.commands}, {"consent.request"})
        self.assertTrue(all(item.session_id == created["session_id"] for item in self.repo.commands))
        self.assertNotIn("+", repr(self.repo.commands))

    async def test_invalid_participant_refs_are_rejected(self):
        status, payload = await self.request(
            "POST", "/v1/bridge-sessions", token=self.token,
            body={"participant_refs": ["same", "same"]},
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_request")

    async def test_cancel_before_provider_activity(self):
        status, created = await self.request(
            "POST", "/v1/bridge-sessions", token=self.token,
            body={"participant_refs": ["opaque-a", "opaque-b"]},
        )
        self.assertEqual(status, 201)
        status, cancelled = await self.request(
            "POST", f"/v1/bridge-sessions/{created['session_id']}/cancel",
            token=self.token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(cancelled["state"], "cancelled")

    async def test_oversized_body_is_rejected(self):
        sent = []
        chunks = [{"type": "http.request", "body": b"x" * 17000, "more_body": False}]

        async def receive():
            return chunks.pop(0)

        async def send(message):
            sent.append(message)

        await self.app(
            {"type": "http", "method": "POST", "path": "/v1/bridge-sessions",
             "headers": [(b"authorization", f"Bearer {self.token}".encode())]},
            receive, send,
        )
        start = next(item for item in sent if item["type"] == "http.response.start")
        self.assertEqual(start["status"], 400)


if __name__ == "__main__":
    unittest.main()
