"""
auth.py — Supabase JWT verification dependency
Uses the Supabase client to verify tokens instead of manual JWT decoding.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db import get_db

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    """
    Verify the Supabase JWT using the Supabase client and return the user.
    Raises 401 if invalid or expired.
    """
    token = credentials.credentials
    try:
        db = get_db()
        response = db.auth.get_user(token)
        user = response.user
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"user_id": str(user.id), "email": user.email or ""}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )
