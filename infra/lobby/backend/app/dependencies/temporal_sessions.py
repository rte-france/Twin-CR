"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import asyncio

import temporalio.exceptions
from temporalio.client import Client

RUNNING_LOBBY_QUERY = (
    'WorkflowType="LobbySessionWorkflow" AND ExecutionStatus="Running"'
)
QUERY_TIMEOUT_SECONDS = 2.0


def session_workflow_id(session_id: str) -> str:
    return f"session-{session_id}"


def session_handle(client: Client, session_id: str):
    return client.get_workflow_handle(session_workflow_id(session_id))


async def iter_running_session_states(
    client: Client, timeout: float = QUERY_TIMEOUT_SECONDS
):
    async for execution in client.list_workflows(RUNNING_LOBBY_QUERY):
        try:
            handle = client.get_workflow_handle(execution.id)
            state = await asyncio.wait_for(handle.query("get_state"), timeout=timeout)
        except TimeoutError, temporalio.exceptions.TemporalError:
            continue
        yield execution, state
