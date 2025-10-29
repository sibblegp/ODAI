import requests
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import httpx
import base64
import hashlib
from typing import Tuple
from dataclasses import dataclass
from typing import Optional, Dict
import time
import urllib.parse

ISSUER = "https://mcp.asana.com"
REGISTRATION_ENDPOINT = "https://mcp.asana.com/register"
AUTHORIZATION_ENDPOINT = "https://mcp.asana.com/authorize"
TOKEN_ENDPOINT = "https://mcp.asana.com/token"

ASANA_ROUTER = APIRouter(prefix='/auth/asana')

PENDING_OAUTH = {}

class OAuthDiscoveryError(Exception):
    pass

@dataclass
class RegisteredClient:
    issuer: str
    client_id: str
    client_secret: Optional[str] = None
    registration_client_uri: Optional[str] = None
    registration_access_token: Optional[str] = None
    token_endpoint_auth_method: str = "none"
    expires_at: Optional[float] = None

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce() -> Tuple[str, str]:
    verifier = _b64url(os.urandom(40))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge

async def register_asana_dynamic_client() -> "RegisteredClient":
    reg_endpoint = REGISTRATION_ENDPOINT
    
    # Choose a client auth method: env override > server-supported > sensible default
    supported = ['none']
    env_method = ['none']
    method_order = []
    if env_method:
        method_order.append(env_method)
    # Prefer none when available (PKCE public client), then post, then basic
    method_order += ["none", "client_secret_post", "client_secret_basic"]
    desired = next((m for m in method_order if (
        not supported or m in supported)), "none")

    body = {
        "application_type": "web",
        "redirect_uris": ["http://localhost:8000/auth/asana/callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": desired,
        "client_name": "MCP Chat Backend",
    }
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(reg_endpoint, headers=headers, json=body)
        print(r.json())
        if r.status_code >= 400:
            raise HTTPException(
                status_code=502, detail=f"Dynamic client registration failed: {r.text}")
        data = r.json()

    # client_secret_expires_at is epoch seconds (0 or omitted for non-expiring)
    expires_at = None
    csea = data.get("client_secret_expires_at")
    if isinstance(csea, (int, float)) and csea > 0:
        expires_at = float(csea)

    reg = RegisteredClient(
        issuer=ISSUER,
        client_id=data["client_id"],
        client_secret=data.get("client_secret"),
        registration_client_uri=data.get("registration_client_uri"),
        registration_access_token=data.get("registration_access_token"),
        token_endpoint_auth_method=data.get(
            "token_endpoint_auth_method", desired),
        expires_at=expires_at,
    )

    # If AS returned a method needing a secret but didn't provide one, fail early
    if reg.token_endpoint_auth_method in ("client_secret_post", "client_secret_basic") and not reg.client_secret:
        raise HTTPException(
            status_code=502, detail="AS selected a confidential client auth method but returned no client_secret")

    return reg


@ASANA_ROUTER.get('/login')
async def connect():
    reg = await register_asana_dynamic_client()
    #issuer = reg.issuer


    # Choose client: prefer explicit env var; otherwise dynamically register and cache by issuer
    client_id = reg.client_id
    code_verifier, code_challenge = generate_pkce()
    state = _b64url(os.urandom(24))


    # Persist pending auth request
    PENDING_OAUTH[state] = {
        #"sid": sid,
        #"server": server,
        "code_verifier": code_verifier,
        #"meta": meta,
        "ts": time.time(),
        'client_id': client_id,
        'client_secret': reg.client_secret,
    }


    # Determine the issuer and client to use


    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": "http://localhost:8000/auth/asana/callback",
        # "scope": "openid profile offline_access", # scopes vary per server; adjust as needed
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        # Resource Indicators (recommended for MCP auth)
        "resource": "https://mcp.asana.com",
    }
    
    url = AUTHORIZATION_ENDPOINT + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@ASANA_ROUTER.get('/callback')
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if state not in PENDING_OAUTH:
        raise HTTPException(status_code=400, detail="Unknown or expired state")
    
    entry = PENDING_OAUTH[state]

    client_id = entry['client_id']
    client_secret = entry['client_secret']

    token_endpoint = TOKEN_ENDPOINT
    code_verifier = entry["code_verifier"]
    #server = entry["server"]
    #sid = entry["sid"]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        body = {
            'client_id': client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:8000/auth/asana/callback",
            'code_verifier': code_verifier
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = await client.post(token_endpoint, data=body, headers=headers)
        print(r.json())
        if r.status_code >= 400:
            raise HTTPException(
                status_code=502, detail=f"Token endpoint failed: {r.text}")
        data = r.json()
    
    return {'data': data, 'client_id': client_id}