"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import uuid

import httpx
import temporalio.exceptions
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException

from app.dependencies import templates_repo as repo
from app.dependencies.aliases import (
    CurrentUserDep,
    DbSessionDep,
    S3ClientDep,
    SettingsDep,
    TemporalClientDep,
)
from app.schemas import ArtifactPayload, LaunchPayload
from app.temporal.workflows import LobbySessionInput

router = APIRouter(prefix="/api/v1/nomad", tags=["Nomad"])

ARCHIVE_SUFFIXES = (".zip", ".tar.gz")
PRESIGNED_URL_TTL = 3600


def _normalize_destination(raw_destination: str) -> str:
    dest = raw_destination.strip("/")
    if dest == "alloc" or dest.startswith("alloc/"):
        return f"../{dest}"
    return dest


async def _build_nomad_artifacts(
    s3_client, bucket: str, artifacts_db, art_map: dict[str, ArtifactPayload]
):
    nomad_artifacts = []
    for art in artifacts_db:
        # 💡 Sécurité : on s'assure que l'ID existe bien dans la map du payload
        art_id = str(art["id"])
        req = art_map.get(art_id) or art_map.get(art["id"])

        if not req:
            continue  # Ignore silencieusement ou log un avertissement si l'artefact n'est plus valide

        presigned_url = await s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": art["s3_object_key"]},
            ExpiresIn=PRESIGNED_URL_TTL,
        )

        is_archive = art["name"].endswith(ARCHIVE_SUFFIXES)
        dest_folder = _normalize_destination(req.destination)
        relative_dest = dest_folder if is_archive else f"{dest_folder}/{art['name']}"

        nomad_artifacts.append(
            {
                "GetterSource": presigned_url,
                "RelativeDest": relative_dest,
                "GetterOptions": {"archive": "true" if is_archive else "false"},
                "GetterMode": "any" if is_archive else "file",
            }
        )

    return nomad_artifacts


@router.post("/{file_id}/launch")
async def launch_nomad_job(
    file_id: str,
    payload: LaunchPayload,
    db_session: DbSessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    s3_client: S3ClientDep,
    temporal_client: TemporalClientDep,
):
    # CORRECTION ZANZIBAR : Injection de current_user.id pour vérifier les droits HCL
    row = await repo.fetch_file_or_404(
        db_session, file_id, current_user.id, detail="HCL Template not found"
    )

    artifact_ids = [a.id for a in payload.artifacts]
    art_map = {a.id: a for a in payload.artifacts}

    # CORRECTION ZANZIBAR : Injection de current_user.id pour vérifier les droits des artefacts
    artifacts_db = await repo.fetch_artifacts(db_session, artifact_ids, current_user.id)

    try:
        s3_response = await s3_client.get_object(
            Bucket=settings.s3_bucket_name, Key=row["s3_object_key"]
        )
        hcl_content = (await s3_response["Body"].read()).decode("utf-8")
        nomad_artifacts = await _build_nomad_artifacts(
            s3_client, settings.s3_bucket_name, artifacts_db, art_map
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 Error: {e}")

    try:
        workflow_id = f"twineu-session-{file_id}-{uuid.uuid4().hex[:8]}"
        await temporal_client.start_workflow(
            "LobbySessionWorkflow",
            args=[
                LobbySessionInput(
                    hcl_content=hcl_content, nomad_artifacts=nomad_artifacts
                )
            ],
            id=workflow_id,
            task_queue="twineu-task-queue",
        )
        return {
            "message": "Nomad job deployment delegated to Temporal Workflow.",
            "workflow_id": workflow_id,
        }
    except temporalio.exceptions.TemporalError as e:
        raise HTTPException(status_code=500, detail=f"Temporal Start Error: {e}")


@router.get("/consul-sessions")
async def get_real_consul_sessions(
    current_user: CurrentUserDep,
    settings: SettingsDep,
):
    consul_api_url = f"{settings.consul_url.rstrip('/')}/v1/health/state/any"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(consul_api_url, timeout=5.0)
            response.raise_for_status()

            health_checks = response.json()
            services_status = {}
            for check in health_checks:
                service_id = check.get("ServiceID")
                if service_id:
                    services_status[service_id] = check.get("Status")

            return services_status

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Error communicating with Consul: {e}"
        )
