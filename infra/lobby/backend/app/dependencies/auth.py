"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import ssl
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.dependencies.get_config import get_settings
from app.schemas import CurrentUser

security = HTTPBearer()
settings = get_settings()

KC_URL = settings.keycloak_url.rstrip("/")
JWKS_URL = f"{KC_URL}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"

# --- ASTUCE POUR CONTOURNER L'ERREUR SSL EN DÉVELOPPEMENT ---
unverified_context = ssl.create_default_context()
unverified_context.check_hostname = False
unverified_context.verify_mode = ssl.CERT_NONE

# On passe le contexte SSL "laxiste" au client JWKS
jwks_client = PyJWKClient(JWKS_URL, ssl_context=unverified_context)
# -----------------------------------------------------------


async def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> CurrentUser:
    try:
        # 1. On va chercher la bonne clé publique (le SSL ne bloquera plus ici !)
        signing_key = jwks_client.get_signing_key_from_jwt(token.credentials)

        # 2. On décode le token
        payload = jwt.decode(
            token.credentials,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_aud": False,  # On ignore toujours l'audience pour l'instant
                "verify_exp": True,
            },
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401, detail="Le token ne contient pas de 'sub' (user_id)"
            )

        return CurrentUser(id=user_id)

    except jwt.PyJWKClientError as e:
        print(f"🔥 ERREUR RÉSEAU JWKS : Impossible de joindre {JWKS_URL} -> {e}")
        raise HTTPException(
            status_code=500,
            detail="Impossible de joindre Keycloak pour vérifier le token.",
        )

    except jwt.InvalidTokenError as e:
        print(f"🔥 ERREUR DE TOKEN JWT : {e}")
        raise HTTPException(status_code=401, detail=f"Token invalide : {e!s}")

    except Exception as e:  # noqa: BLE001
        print(f"🔥 ERREUR INCONNUE AUTH : {e}")
        raise HTTPException(
            status_code=500, detail="Erreur interne d'authentification."
        )
