"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from fastapi import APIRouter, HTTPException
from temporalio.client import Client, WorkflowQueryFailedError
from temporalio.service import RPCError

from app.dependencies.aliases import CurrentUserDep, TemporalClientDep
from app.dependencies.temporal_sessions import session_handle
from app.schemas import SessionActionResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["Session"])


async def _signal_and_respond(
    client: Client, session_id: str, signal: str, message: str, status: str
) -> SessionActionResponse:
    await session_handle(client, session_id).signal(signal)
    return SessionActionResponse(session_id=session_id, message=message, status=status)


@router.post("/{session_id}/init", response_model=SessionActionResponse)
async def init_session(
    session_id: str,
    current_user: CurrentUserDep,
    client: TemporalClientDep,
):
    return await _signal_and_respond(
        client, session_id, "request_init", "Initialization started", "INIT"
    )


@router.post("/{session_id}/start", response_model=SessionActionResponse)
async def start_session(
    session_id: str,
    current_user: CurrentUserDep,
    client: TemporalClientDep,
):
    return await _signal_and_respond(
        client, session_id, "request_start", "Starting countdown", "STARTING"
    )


@router.post("/{session_id}/stop", response_model=SessionActionResponse)
async def stop_session(
    session_id: str,
    current_user: CurrentUserDep,
    client: TemporalClientDep,
):
    return await _signal_and_respond(
        client, session_id, "request_stop", "Stopping", "STOPPING"
    )


@router.get("/{session_id}")
async def get_session_state(
    session_id: str,
    current_user: CurrentUserDep,
    client: TemporalClientDep,
):
    try:
        return await session_handle(client, session_id).query("get_state")
    except WorkflowQueryFailedError, RPCError:
        raise HTTPException(status_code=404, detail="Session not found or terminated")
