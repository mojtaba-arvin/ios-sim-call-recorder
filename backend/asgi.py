# Uvicorn factory for the authenticated session API.
from __future__ import annotations
import json, os
import psycopg
from bridge_core.http_api import BearerTokenAuthenticator, BridgeSessionsASGI
from bridge_core.persistence import PostgresBridgeRepository

def create_app():
    database_url = os.environ.get('DATABASE_URL','').strip()
    token_json = os.environ.get('BRIDGE_API_TOKEN_HASHES','')
    if not database_url: raise RuntimeError('DATABASE_URL must be injected by the deployment secret manager')
    if not token_json: raise RuntimeError('BRIDGE_API_TOKEN_HASHES must be injected by the deployment secret manager')
    try: token_hashes = json.loads(token_json)
    except json.JSONDecodeError as exc: raise RuntimeError('BRIDGE_API_TOKEN_HASHES must be valid JSON') from exc
    if not isinstance(token_hashes,dict): raise RuntimeError('BRIDGE_API_TOKEN_HASHES must be an object')
    repository = PostgresBridgeRepository(lambda: psycopg.connect(database_url))
    authenticator = BearerTokenAuthenticator(token_hashes)
    return BridgeSessionsASGI(repository=repository,authenticator=authenticator)
