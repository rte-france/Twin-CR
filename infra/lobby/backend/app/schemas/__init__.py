"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

# schemas/__init__.py
from pydantic import BaseModel


class CurrentUser(BaseModel):
    id: str
    email: str | None = None


class SessionCreate(BaseModel):
    name: str
    template_id: str
    environment_id: str


class PlayerRoleUpdate(BaseModel):
    role: str


class PlayerReadyUpdate(BaseModel):
    is_ready: bool


class SessionResponse(BaseModel):
    session_id: str
    template_id: str
    status: str
    base_url: str


class Player(BaseModel):
    id: str
    name: str
    role: str | None = None
    is_ready: bool = False


class SessionStateResponse(BaseModel):
    session_id: str
    template_id: str
    status: str
    base_url: str
    players: dict[str, Player]
    player_count: int
    started_at: str | None = None
    running_duration_sec: float = 0.0


class SessionActionResponse(BaseModel):
    session_id: str
    message: str
    status: str


class ItemUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None


class RawFileUpdate(BaseModel):
    content: str
    is_base64: bool = True


class ArtifactPayload(BaseModel):
    id: str
    destination: str = "alloc"


class LaunchPayload(BaseModel):
    artifacts: list[ArtifactPayload] = []


class UpdateRawPayload(BaseModel):
    content: str


class DirectoryCreate(BaseModel):
    project_id: str
    name: str
    parent_id: str | None = None
