"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import asyncio
import json
import uuid

import temporalio.exceptions
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from temporalio.client import Client

from app.dependencies.get_config import Settings, get_settings
from app.dependencies.get_temporal import get_temporal_client
from app.dependencies.temporal_sessions import (
    iter_running_session_states,
    session_handle,
)
from app.schemas import (
    PlayerReadyUpdate,
    PlayerRoleUpdate,
    SessionCreate,
    SessionResponse,
)
from app.temporal.workflows import LobbySessionInput

router = APIRouter(prefix="/api/v1/lobby", tags=["Lobby"])
security = HTTPBearer()

auth_dep = Depends(security)
settings_dep = Depends(get_settings)
temporal_dep = Depends(get_temporal_client)

TASK_QUEUE = "twineu-task-queue"
STREAM_INTERVAL_SECONDS = 3


@router.post("", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    _token: HTTPAuthorizationCredentials = auth_dep,
    settings: Settings = settings_dep,
    client: Client = temporal_dep,
):
    session_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    base_url = f"http://sess-{session_id}.{settings.base_domain}"

    workflow_input = LobbySessionInput(
        hcl_content=getattr(session_data, "hcl_content", ""),
        nomad_artifacts=getattr(session_data, "nomad_artifacts", []),
        session_name=session_data.name,
        admin_id=admin_id,
        template_id=session_data.template_id,
        base_url=base_url,
    )

    await client.start_workflow(
        "LobbySessionWorkflow",
        workflow_input,
        id=f"twineu-session-{session_id}",
        task_queue=TASK_QUEUE,
    )

    return SessionResponse(
        session_id=session_id,
        template_id=session_data.template_id,
        status="LOBBY",
        base_url=base_url,
    )


@router.post("/{session_id}/public")
async def make_session_public(
    session_id: str,
    _token: HTTPAuthorizationCredentials = auth_dep,
    client: Client = temporal_dep,
):
    await session_handle(client, session_id).signal("set_public", True)
    return {"message": "Session is now public"}


@router.post("/{session_id}/join")
async def join_session(
    session_id: str,
    _token: HTTPAuthorizationCredentials = auth_dep,
    client: Client = temporal_dep,
):
    player_id = str(uuid.uuid4())
    player_name = f"User_{player_id[:4]}"

    await session_handle(client, session_id).signal(
        "player_join", {"player_id": player_id, "name": player_name}
    )
    return {"message": "Successfully joined", "player_id": player_id}


@router.put("/{session_id}/players/{player_id}/ready")
async def update_player_ready_status(
    session_id: str,
    player_id: str,
    ready_update: PlayerReadyUpdate,
    _token: HTTPAuthorizationCredentials = auth_dep,
    client: Client = temporal_dep,
):
    await session_handle(client, session_id).signal(
        "update_player_ready",
        {"player_id": player_id, "is_ready": ready_update.is_ready},
    )
    return {"message": "Ready status updated"}


@router.put("/{session_id}/players/{player_id}/role")
async def update_player_role(
    session_id: str,
    player_id: str,
    role_update: PlayerRoleUpdate,
    _token: HTTPAuthorizationCredentials = auth_dep,
    client: Client = temporal_dep,
):
    await session_handle(client, session_id).signal(
        "assign_role", {"player_id": player_id, "role": role_update.role}
    )
    return {"message": "Role updated"}


@router.get("/public/stream")
async def stream_public_sessions(client: Client = temporal_dep):
    async def event_generator():
        try:
            while True:
                public_sessions = []
                try:
                    async for _execution, state in iter_running_session_states(client):
                        try:
                            if (
                                state.get("is_public")
                                and state.get("status") == "LOBBY"
                            ):
                                public_sessions.append(
                                    {
                                        "session_id": state["session_id"],
                                        "player_count": state["player_count"],
                                        "template_id": state["template_id"],
                                    }
                                )
                        except KeyError, TypeError, AttributeError:
                            pass
                except temporalio.exceptions.TemporalError as e:
                    print(f"Error reading workflows: {e}")

                yield f"data: {json.dumps(public_sessions)}\n\n"
                await asyncio.sleep(STREAM_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/sessions")
async def get_all_sessions(client: Client = temporal_dep):
    sessions = []
    try:
        async for execution, state in iter_running_session_states(client):
            sessions.append(
                {
                    "id": execution.id,
                    "name": state.get("session_name", f"Session {execution.id[:8]}"),
                    "status": state.get("status", "UNKNOWN"),
                }
            )
    except temporalio.exceptions.TemporalError as e:
        print(f"Error retrieving sessions: {e}")

    return sessions


@router.post("/{workflow_id}/start")
async def start_prepared_session(workflow_id: str, client: Client = temporal_dep):
    try:
        await client.get_workflow_handle(workflow_id).signal("request_start")
        return {"message": "Session successfully signaled as RUNNING."}
    except temporalio.exceptions.TemporalError as e:
        raise HTTPException(status_code=500, detail=f"Temporal Error: {e}")


@router.post("/{workflow_id}/stop")
async def stop_running_session(workflow_id: str, client: Client = temporal_dep):
    try:
        await client.get_workflow_handle(workflow_id).signal("request_stop")
        return {"message": "Session successfully signaled as STOPPED."}
    except temporalio.exceptions.TemporalError as e:
        raise HTTPException(status_code=500, detail=f"Temporal Error: {e}")
