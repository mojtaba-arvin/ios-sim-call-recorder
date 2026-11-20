# Tenant-scoped encrypted mapping from opaque participant references to E.164 addresses.
from __future__ import annotations
import os, re, json
from dataclasses import dataclass
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_E164 = re.compile(r'^\+[1-9][0-9]{7,14}$')

class AddressVaultIntegrityError(RuntimeError):
    pass

class ParticipantAddressInUseError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class EncryptedParticipantAddressCodec:
    key: bytes
    def __post_init__(self):
        if not isinstance(self.key,bytes) or len(self.key)!=32:
            raise ValueError('address vault key must be exactly 32 bytes')

    def encrypt(self, *, tenant_id: str, participant_ref: str, address: str) -> bytes:
        self._validate_scope(tenant_id,participant_ref)
        if not isinstance(address,str) or not _E164.fullmatch(address):
            raise ValueError('participant address must be a valid E.164 number')
        nonce=os.urandom(12)
        aad=f'{tenant_id}\0{participant_ref}'.encode('utf-8')
        return nonce + AESGCM(self.key).encrypt(nonce,address.encode('ascii'),aad)

    def decrypt(self, *, tenant_id: str, participant_ref: str, ciphertext: bytes) -> str:
        self._validate_scope(tenant_id,participant_ref)
        if not isinstance(ciphertext,bytes) or len(ciphertext)<29:
            raise AddressVaultIntegrityError('address ciphertext is malformed')
        aad=f'{tenant_id}\0{participant_ref}'.encode('utf-8')
        try:
            value=AESGCM(self.key).decrypt(ciphertext[:12],ciphertext[12:],aad).decode('ascii')
        except (InvalidTag,UnicodeDecodeError) as exc:
            raise AddressVaultIntegrityError('address ciphertext authentication failed') from exc
        if not _E164.fullmatch(value):
            raise AddressVaultIntegrityError('decrypted participant address is invalid')
        return value

    @staticmethod
    def _validate_scope(tenant_id,participant_ref):
        if not isinstance(tenant_id,str) or not tenant_id.strip() or len(tenant_id)>128:
            raise ValueError('tenant identifier is invalid')
        if not isinstance(participant_ref,str) or not participant_ref or participant_ref!=participant_ref.strip() or any(c.isspace() for c in participant_ref) or len(participant_ref)>128:
            raise ValueError('opaque participant reference is invalid')

class PostgresParticipantAddressResolver:
    def __init__(self, *, connect, codec: EncryptedParticipantAddressCodec):
        self._connect,self._codec=connect,codec

    def _ensure_not_in_use(self, cur, *, tenant_id: str, participant_ref: str) -> None:
        cur.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"{tenant_id}\\0{participant_ref}",),
        )
        cur.execute(
            """SELECT 1 FROM bridge_sessions
               WHERE tenant_id=%s
                 AND expected_participant_refs @> %s::jsonb
                 AND state NOT IN ('completed','degraded','failed','cancelled')
               LIMIT 1 FOR UPDATE""",
            (tenant_id, json.dumps([participant_ref])),
        )
        if cur.fetchone():
            raise ParticipantAddressInUseError("participant address is bound to an active session")

    def store(self, *, tenant_id: str, participant_ref: str, address: str) -> None:
        ciphertext=self._codec.encrypt(tenant_id=tenant_id,participant_ref=participant_ref,address=address)
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_not_in_use(cur, tenant_id=tenant_id, participant_ref=participant_ref)
                cur.execute(
                    "SELECT 1 FROM participant_address_vault WHERE tenant_id=%s AND participant_ref=%s FOR UPDATE",
                    (tenant_id, participant_ref),
                )
                action = "replaced" if cur.fetchone() else "created"
                cur.execute(
                    """INSERT INTO participant_address_vault
                       (tenant_id,participant_ref,ciphertext,updated_at)
                       VALUES (%s,%s,%s,now())
                       ON CONFLICT (tenant_id,participant_ref)
                       DO UPDATE SET ciphertext=EXCLUDED.ciphertext,updated_at=now()""",
                    (tenant_id, participant_ref, ciphertext),
                )
                cur.execute(
                    """INSERT INTO participant_address_audit
                       (tenant_id,participant_ref,action,actor_tenant_id)
                       VALUES (%s,%s,%s,%s)""",
                    (tenant_id, participant_ref, action, tenant_id),
                )

    def resolve(self, *, tenant_id: str, participant_ref: str) -> str:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT ciphertext FROM participant_address_vault WHERE tenant_id=%s AND participant_ref=%s',(tenant_id,participant_ref))
                row=cur.fetchone()
        if row is None: raise LookupError('participant address not found')
        ciphertext=row[0] if isinstance(row[0],bytes) else bytes(row[0])
        return self._codec.decrypt(tenant_id=tenant_id,participant_ref=participant_ref,ciphertext=ciphertext)

    def delete(self, *, tenant_id: str, participant_ref: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_not_in_use(cur, tenant_id=tenant_id, participant_ref=participant_ref)
                cur.execute(
                    "DELETE FROM participant_address_vault WHERE tenant_id=%s AND participant_ref=%s",
                    (tenant_id, participant_ref),
                )
                if cur.rowcount:
                    cur.execute(
                        """INSERT INTO participant_address_audit
                           (tenant_id,participant_ref,action,actor_tenant_id)
                           VALUES (%s,%s,'deleted',%s)""",
                        (tenant_id, participant_ref, tenant_id),
                    )
