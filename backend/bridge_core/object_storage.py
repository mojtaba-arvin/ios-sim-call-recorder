# Private S3-compatible media storage with server-side KMS encryption.
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID
from .media_validation import validate_wav

@dataclass(frozen=True, slots=True)
class StoredMediaObject:
    object_key: str
    byte_count: int
    sha256: str
    duration_seconds: float
    sample_rate_hz: int
    channel_count: int

class S3MediaObjectStore:
    def __init__(self, *, client, bucket: str, kms_key_id: str):
        if not bucket or not bucket.strip() or not kms_key_id or not kms_key_id.strip():
            raise ValueError('private bucket and KMS key are required')
        self._client,self._bucket,self._kms_key_id=client,bucket,kms_key_id

    @staticmethod
    def _key(*, tenant_id: str, session_id: str, media_id: str) -> str:
        if not isinstance(tenant_id,str) or not tenant_id.strip(): raise ValueError('tenant_id is required')
        try:
            session=UUID(session_id)
            media=UUID(media_id)
        except (ValueError,TypeError,AttributeError) as exc:
            raise ValueError('session and media identifiers must be UUIDs') from exc
        tenant_digest=hashlib.sha256(tenant_id.encode('utf-8')).hexdigest()[:32]
        return f'tenants/{tenant_digest}/sessions/{session}/media/{media}.wav'

    def put_wav(self, *, tenant_id: str, session_id: str, media_id: str, source_path: str | Path) -> StoredMediaObject:
        source=Path(source_path)
        metadata=validate_wav(source)
        key=self._key(tenant_id=tenant_id,session_id=session_id,media_id=media_id)
        self._client.upload_file(
            str(source),self._bucket,key,
            ExtraArgs={
                'ContentType':'audio/wav',
                'ServerSideEncryption':'aws:kms',
                'SSEKMSKeyId':self._kms_key_id,
                'BucketKeyEnabled':True,
                'Metadata':{'sha256':metadata.sha256},
            },
        )
        return StoredMediaObject(key,metadata.byte_count,metadata.sha256,metadata.duration_seconds,metadata.sample_rate_hz,metadata.channel_count)

    def download_wav(self, *, tenant_id: str, session_id: str, media_id: str, destination_path: str | Path) -> None:
        key=self._key(tenant_id=tenant_id,session_id=session_id,media_id=media_id)
        self._client.download_file(self._bucket,key,str(destination_path))

    def delete(self, *, tenant_id: str, session_id: str, media_id: str) -> None:
        key=self._key(tenant_id=tenant_id,session_id=session_id,media_id=media_id)
        self._client.delete_object(Bucket=self._bucket,Key=key)

    def presigned_download_url(self, *, tenant_id: str, session_id: str, media_id: str, expires_seconds: int = 60) -> str:
        if not 60 <= expires_seconds <= 300: raise ValueError('download URL lifetime must be between 1 and 300 seconds')
        key=self._key(tenant_id=tenant_id,session_id=session_id,media_id=media_id)
        return self._client.generate_presigned_url(
            'get_object',Params={'Bucket':self._bucket,'Key':key},ExpiresIn=expires_seconds,
        )
