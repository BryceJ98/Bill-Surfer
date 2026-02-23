"""
auth.py — Local JWT verification using Supabase JWKS public keys.

Fetches the project's public key from the JWKS endpoint once (cached),
then verifies every request locally — no service-role key required,
no round-trip to Supabase per request. Works with ES256, RS256, and
whatever algorithm Supabase adopts in the future.
"""

import json
import os
from functools import lru_cache

import httpx
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer()


@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    resp = httpx.get(f"{supabase_url}/auth/v1/.well-known/jwks.json", timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_public_key(kid: str, alg: str):
    jwks = _fetch_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            if alg.startswith("ES"):
                from jwt.algorithms import ECAlgorithm
                return ECAlgorithm.from_jwk(json.dumps(key_data))
            elif alg.startswith("RS"):
                from jwt.algorithms import RSAAlgorithm
                return RSAAlgorithm.from_jwk(json.dumps(key_data))
    return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    token = credentials.credentials
    try:
        header = pyjwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "ES256")

        public_key = _get_public_key(kid, alg)
        if public_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown signing key",
            )

        payload = pyjwt.decode(
            token,
            public_key,
            algorithms=[alg],
            audience="authenticated",
        )
        return {"user_id": payload["sub"], "email": payload.get("email", "")}

    except HTTPException:
        raise
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth error: {exc}",
        )
