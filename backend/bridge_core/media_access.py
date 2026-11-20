"""Tenant-authorized short-lived download access for verified media assets."""
from __future__ import annotations


class PostgresMediaDownloadService:
    def __init__(self, *, connect, object_store):
        self._connect, self._object_store = connect, object_store

    def create_download(self, *, tenant_id: str, session_id: str) -> dict | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT media_id, sha256, byte_count, duration_seconds,
                              sample_rate_hz, channel_count, channel_activity, channel_map
                       FROM media_assets
                       WHERE tenant_id=%s AND session_id=%s
                         AND verification_state='verified' AND deleted_at IS NULL
                       ORDER BY created_at DESC LIMIT 1""",
                    (tenant_id, session_id),
                )
                row = cur.fetchone()
        if row is None:
            return None
        media_id, digest, byte_count, duration, sample_rate, channels, activity, channel_map = row
        url = self._object_store.presigned_download_url(
            tenant_id=tenant_id, session_id=session_id, media_id=str(media_id),
            expires_seconds=120,
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO media_access_audit
                       (tenant_id, session_id, media_id, action, expires_in_seconds)
                       VALUES (%s,%s,%s,'download_url_issued',120)""",
                    (tenant_id, session_id, media_id),
                )
        return {
            "media_id": str(media_id),
            "sha256": digest,
            "byte_count": byte_count,
            "duration_seconds": duration,
            "sample_rate_hz": sample_rate,
            "channel_count": channels,
            "channel_activity": activity,
            "channel_map": channel_map,
            "download_url": url,
            "expires_in_seconds": 120,
        }
