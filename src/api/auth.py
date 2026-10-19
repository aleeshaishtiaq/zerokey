import os
import re
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def _jwks_client(domain: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"https://{domain}/.well-known/jwks.json")


def require_authorized_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> str:
    domain = os.getenv("AUTH0_DOMAIN", "").strip().removeprefix("https://").rstrip("/")
    audience = os.getenv("AUTH0_AUDIENCE", "").strip()
    allowed_subjects = {
        subject.strip()
        for subject in os.getenv("AUTH0_ALLOWED_SUBJECTS", "").split(",")
        if subject.strip()
    }

    if (
        not re.fullmatch(r"[A-Za-z0-9.-]+\.auth0\.com", domain)
        or not audience
        or not allowed_subjects
    ):
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured for an approved staging user.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="A valid Auth0 access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    issuer = f"https://{domain}/"
    try:
        signing_key = _jwks_client(domain).get_signing_key_from_jwt(
            credentials.credentials
        )
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWKClientError as error:
        raise HTTPException(
            status_code=503,
            detail="Unable to verify Auth0 signing keys.",
        ) from error
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=401,
            detail="The Auth0 access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    subject = claims.get("sub")
    if not isinstance(subject, str) or subject not in allowed_subjects:
        raise HTTPException(
            status_code=403,
            detail="This identity is not approved for the staging demo.",
        )
    return subject
