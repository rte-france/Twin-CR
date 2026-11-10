"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.dependencies import templates_repo as repo
from app.dependencies.aliases import S3ClientDep, SettingsDep
from app.dependencies.auth import get_current_user
from app.dependencies.get_db import get_db
from app.schemas import CurrentUser

# Si votre router est déclaré dans un autre fichier, ajustez le prefix
router = APIRouter(prefix="/api/v1/projects", tags=["Files"])

@router.get("/{project_id}/files/{file_id}/raw")
async def get_raw_file(
    project_id: str,
    file_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    s3_client: S3ClientDep,
    settings: SettingsDep,
):
    # 1. Vérifie si le fichier existe ET si l'utilisateur a le droit de le lire (Zanzibar)
    # Lève automatiquement une 404 si le fichier n'existe pas ou si refusé.
    file_node = await repo.fetch_file_or_404(db, file_id, user.id)

    s3_key = file_node.get("s3_object_key")
    if not s3_key:
        raise HTTPException(status_code=404, detail="File content not found in S3")

    # 2. Génère une URL présignée S3 pour que le frontend puisse télécharger le fichier
    try:
        presigned_url = await s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
            ExpiresIn=3600, # 1 heure
        )
        # Redirige le client directement vers le fichier S3
        return RedirectResponse(url=presigned_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Error: {str(e)}")
