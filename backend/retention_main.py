"""Scheduled Twilio/S3 retention deletion worker."""
from __future__ import annotations

import os
from bridge_core.config import database_url_from_env
import time
import psycopg
import boto3
from twilio.rest import Client

from bridge_core.object_storage import S3MediaObjectStore
from providers.twilio.media import TwilioMediaRetentionWorker, TwilioRecordingMediaIngestor
from providers.twilio.resource_resolver import PostgresTwilioResourceResolver


def main():
    try:
        dsn=database_url_from_env()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    account=os.environ.get("TWILIO_ACCOUNT_SID","").strip()
    username=os.environ.get("TWILIO_API_KEY","").strip() or account
    password=os.environ.get("TWILIO_API_SECRET","").strip() or os.environ.get("TWILIO_AUTH_TOKEN","").strip()
    if not all((dsn,account,username,password,os.environ.get("MEDIA_BUCKET"),os.environ.get("MEDIA_KMS_KEY_ID"))):
        raise SystemExit("database, Twilio API and encrypted media storage configuration are required")
    connect=lambda:psycopg.connect(dsn)
    client=Client(username,password,account_sid=account,http_timeout=10)
    store=S3MediaObjectStore(
        client=boto3.client("s3"),bucket=os.environ["MEDIA_BUCKET"],
        kms_key_id=os.environ["MEDIA_KMS_KEY_ID"],
    )
    provider_account_id=os.environ.get("TWILIO_PROVIDER_ACCOUNT_ID","").strip()
    if not provider_account_id:
        raise SystemExit("TWILIO_PROVIDER_ACCOUNT_ID is required for ingestion recovery")
    resolver=PostgresTwilioResourceResolver(connect=connect,provider_account_id=provider_account_id)
    ingestor=TwilioRecordingMediaIngestor(
        account_sid=account,api_username=username,api_password=password,
        provider_account_id=provider_account_id,connect=connect,
        resource_resolver=resolver,object_store=store,
        retention_days=int(os.environ.get("MEDIA_RETENTION_DAYS","30")),
    )
    worker=TwilioMediaRetentionWorker(connect=connect,client=client,object_store=store)
    while True:
        try:
            ingestor.recover_once(limit=25)
            worker.run_once(limit=50)
        except Exception:
            # Do not log provider identifiers, credentials or media object keys.
            pass
        time.sleep(60)


if __name__ == "__main__":
    main()
