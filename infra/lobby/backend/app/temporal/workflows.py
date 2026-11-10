"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

# temporal/workflows.py
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from .activities import deploy_nomad_job, destroy_nomad_job


@dataclass
class LobbySessionInput:
    hcl_content: str = ""
    nomad_artifacts: list = None
    session_name: str = ""
    admin_id: str = ""
    template_id: str = ""
    base_url: str = ""


@workflow.defn
class LobbySessionWorkflow:
    def __init__(self):
        self.session_id = ""
        self.session_name = ""
        self.admin_id = ""
        self.template_id = ""
        self.base_url = ""
        self.status = "LOBBY"
        self.is_public = False
        self.players: dict[str, dict[str, Any]] = {}
        self.countdown = 0
        self.stop_requested = False

        self._init_requested = False
        self._start_requested = False
        self.started_at: str | None = None
        self.start_time_unix: float = 0.0

    @workflow.run
    async def run(self, *args, **kwargs):
        input_data = LobbySessionInput()

        if len(args) == 1:
            if isinstance(args[0], LobbySessionInput):
                input_data = args[0]
            elif isinstance(args[0], dict):
                for k, v in args[0].items():
                    if hasattr(input_data, k):
                        setattr(input_data, k, v)
        elif len(args) == 2:
            input_data.hcl_content = args[0]
            input_data.nomad_artifacts = args[1]
        elif len(args) >= 5:
            input_data.session_name = args[1] if isinstance(args[1], str) else ""
            input_data.admin_id = args[2] if isinstance(args[2], str) else ""
            input_data.template_id = args[3] if isinstance(args[3], str) else ""
            input_data.base_url = args[4] if isinstance(args[4], str) else ""

        self.session_id = workflow.info().workflow_id.replace("twineu-session-", "")
        self.session_name = input_data.session_name
        self.admin_id = input_data.admin_id
        self.template_id = input_data.template_id
        self.base_url = input_data.base_url

        self.status = "PREPARING"

        if input_data.hcl_content:
            await workflow.execute_activity(
                deploy_nomad_job,
                args=[
                    self.session_id,
                    input_data.hcl_content,
                    input_data.nomad_artifacts or [],
                ],
                start_to_close_timeout=timedelta(minutes=5),
            )

        self.status = "READY"

        await workflow.wait_condition(
            lambda: self._start_requested or self.stop_requested
        )

        if self.stop_requested:
            await workflow.execute_activity(
                destroy_nomad_job,
                self.session_id,
                start_to_close_timeout=timedelta(minutes=2),
            )
            self.status = "STOPPED"
            return

        self.status = "RUNNING"
        self.started_at = workflow.now().isoformat()
        self.start_time_unix = workflow.time()

        await workflow.wait_condition(lambda: self.stop_requested)

        await workflow.execute_activity(
            destroy_nomad_job,
            self.session_id,
            start_to_close_timeout=timedelta(minutes=2),
        )

        self.status = "STOPPED"

    @workflow.signal
    def set_public(self, is_public: bool):
        if self.status == "LOBBY":
            self.is_public = is_public

    @workflow.signal
    def player_join(self, payload: dict[str, str]):
        if self.status == "LOBBY":
            player_id = payload["player_id"]
            self.players[player_id] = {
                "id": player_id,
                "name": payload["name"],
                "role": None,
                "is_ready": False,
            }

    @workflow.signal
    def assign_role(self, payload: dict[str, str]):
        player_id = payload["player_id"]
        if player_id in self.players:
            self.players[player_id]["role"] = payload["role"]

    @workflow.signal
    def update_player_ready(self, payload: dict[str, Any]):
        player_id = str(payload["player_id"])
        if player_id in self.players:
            self.players[player_id]["is_ready"] = bool(payload["is_ready"])

    @workflow.signal
    def request_init(self):
        if self.status == "LOBBY":
            self._init_requested = True

    @workflow.signal
    def request_start(self):
        if self.status in ["INIT", "READY"]:
            self._start_requested = True

    @workflow.signal
    def request_stop(self):
        self.stop_requested = True

    @workflow.query
    def get_state(self) -> dict[str, Any]:
        running_duration = 0.0
        if self.status == "RUNNING":
            running_duration = workflow.time() - self.start_time_unix

        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "template_id": self.template_id,
            "status": self.status,
            "base_url": self.base_url,
            "players": self.players,
            "player_count": len(self.players),
            "started_at": self.started_at,
            "running_duration_sec": running_duration,
            "is_public": self.is_public,
            "countdown": self.countdown,
        }
