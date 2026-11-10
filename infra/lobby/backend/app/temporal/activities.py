"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

# temporal/activities.py
import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.dependencies.get_config import get_settings


@activity.defn
async def deploy_nomad_job(
    session_id: str, hcl_text: str, nomad_artifacts: list
) -> str:
    settings = get_settings()
    activity.logger.info(f"Starting deployment for session {session_id}")

    headers = {}
    if settings.nomad_token:
        headers["X-Nomad-Token"] = settings.nomad_token

    async with httpx.AsyncClient() as http_client:
        parse_resp = await http_client.post(
            f"{settings.nomad_url}/v1/jobs/parse",
            json={"JobHCL": hcl_text, "Canonicalize": True},
            headers=headers,
        )

        if parse_resp.status_code != 200:
            error_msg = parse_resp.text
            activity.logger.error(f"Nomad Parse Error: {error_msg}")
            raise ApplicationError(
                f"Syntax error in HCL file: {error_msg}",
                non_retryable=True,
            )

        job_json = parse_resp.json()

        job_json["ID"] = f"twineu-sim-{session_id}"
        job_json["Name"] = f"Session {session_id}"

        if nomad_artifacts:
            try:
                task = job_json["TaskGroups"][0]["Tasks"][0]
                if task.get("Artifacts") is None:
                    task["Artifacts"] = []
                task["Artifacts"].extend(nomad_artifacts)
            except KeyError, IndexError:
                raise ApplicationError(
                    "Invalid HCL structure: Cannot find a TaskGroup/Task to inject artifacts into.",
                    non_retryable=True,
                )

        deploy_resp = await http_client.post(
            f"{settings.nomad_url}/v1/jobs", json={"Job": job_json}, headers=headers
        )

        if deploy_resp.status_code != 200:
            raise ApplicationError(
                f"Nomad Deploy Error: {deploy_resp.text}", non_retryable=True
            )

    activity.logger.info("Nomad job successfully deployed.")
    return "Infrastructure Deployed"


@activity.defn
async def destroy_nomad_job(session_id: str) -> str:
    settings = get_settings()
    activity.logger.info(f"Purging Nomad job for session {session_id}")

    job_id = f"twineu-sim-{session_id}"

    headers = {}
    if settings.nomad_token:
        headers["X-Nomad-Token"] = settings.nomad_token

    async with httpx.AsyncClient() as http_client:
        resp = await http_client.delete(
            f"{settings.nomad_url}/v1/job/{job_id}?purge=true", headers=headers
        )
        if resp.status_code != 404 and resp.status_code != 200:
            raise ApplicationError(f"Nomad Delete Error: {resp.text}")

    return "Infrastructure Purged"
