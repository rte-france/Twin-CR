"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import jwt
from jwt.exceptions import PyJWKClientError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.config import JWKS_URL, KEYCLOAK_CLIENT_ID, DEV_MODE
import ssl

class PrincipalHandler:
    """
    Who the caller is, according to a token this service has verified itself.
    """

    def __init__(self):
        if DEV_MODE:
            ssl._create_default_https_context = ssl._create_unverified_context
        self.security_scheme = HTTPBearer()
        # Fetches the realm's public keys once and caches them, so verification does not
        # cost a round trip per request.
        self._jwks_client = jwt.PyJWKClient(JWKS_URL)

    def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ):
        token = credentials.credentials
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        except PyJWKClientError as exc:
            raise HTTPException(
                status_code=401,
                detail=f"Could not verify the token against {JWKS_URL}: {exc}",
            )

        try:
            # The issuer is not checked: it is the Keycloak URL as Argus reached it
            # (e.g. https://localhost:8443), not KEYCLOAK_INTERNAL_URL.
            # Keycloak access tokens carry aud="account", hence verify_aud=False;
            # azp is checked below instead.
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {exc}",
            )

        if claims.get("typ") != "Bearer":
            raise HTTPException(
                status_code=401,
                detail="Not an access token",
            )

        if claims.get("azp") != KEYCLOAK_CLIENT_ID:
            raise HTTPException(
                status_code=401,
                detail=f"Token was not issued for {KEYCLOAK_CLIENT_ID}",
            )

        if not claims.get("preferred_username"):
            raise HTTPException(
                status_code=401,
                detail="Token carries no preferred_username claim",
            )

        return claims
