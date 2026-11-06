"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import datetime
from pathlib import Path

from sqlalchemy import DateTime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

from backend.db.constants import ROOT_FOLDER_ID


class SessionState(str, Enum):
    WARMUP = "warmup"
    READY = "ready"
    ONGOING = "ongoing"
    CLEANUP = "cleanup"
    ENDED = "ended"

class GameSessionBase(SQLModel):
    name: str = Field(index=True)
    state: SessionState

class AccessKey(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    password: str
    validity_limit: datetime.datetime
    usage: str # Can be "unique"|"multi"
    revoked: bool = False

class AccessKeyTyped(SQLModel):
    id: int | None = None
    password: str
    validity_limit: datetime.datetime
    usage: str
    revoked: bool
    type: str

class GameSession(GameSessionBase, table=True):
    # Avoid reusing id's from deleted sessions
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime.datetime = Field(
        # Aware, like started_at and ended_at: the column is timezone-aware, and
        # a naive local default is what made the timestamps disagree.
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        sa_type=DateTime(timezone=True)  # type: ignore
    )
    started_at: datetime.datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True)  # type: ignore
    )
    ended_at: datetime.datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True) # type: ignore
    )
    gm_key_id: int | None = Field(default=None, foreign_key="accesskey.id")
    operator_key_id: int | None = Field(default=None, foreign_key="accesskey.id")
    golden_key_id: int | None = Field(default=None, foreign_key="accesskey.id")
    author: str | None = Field(default=None)
    # A participation only exists as part of a session, and game_session_id is
    # half of User's primary key, so the default cascade cannot blank it out.
    participants: list["User"] = Relationship(
        back_populates="game_session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    scada_backend_url: str | None = Field(default=None)
    gm_backend_url: str | None = Field(default=None)
    dsl_backend_url: str | None = Field(default=None)
    template_name: str | None = Field(default=None)
    template_uuid: str | None = Field(default=None)
    session_dsl_name: str | None = Field(default=None)
    session_config_toml_name: str | None = Field(default=None)

class GameSessionCreate(SQLModel):
    name: str
    dsl_name: str
    config_toml_name: str
    templateId: int

class GameSessionPublic(GameSessionBase):
    id: int
    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
    participants: list["User"]
    author: str | None

class GameSessionOwn(GameSessionBase):
    """
    What the author is shown about their own sessions.
    """
    id: int
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
    author: str | None
    template_name: str | None

class GameSessionPrivate(GameSessionPublic):
    scada_backend_url: str | None
    gm_backend_url: str | None
    dsl_backend_url: str | None

class User(SQLModel, table=True):
    """
    One user's participation in one session.

    Keyed on both columns: a user takes part in several sessions, and the role
    they hold is a property of the session they joined, not of the user.
    """
    username: str = Field(primary_key=True)
    game_session_id: int = Field(foreign_key="gamesession.id", primary_key=True)
    game_session: GameSession | None = Relationship(back_populates="participants")
    role: str # Can be "gm"|"scada" -> role in a session, not in keycloak

class SessionConnect(SQLModel):
    """
    A join attempt.
    """
    game_session_id: int
    password_gm: str = ""
    password_operator: str = ""

class NewFolder(SQLModel):
    name: str
    parent_id: int

class NodeType(str, Enum):
    folder = "folder"
    template = "template"

class TreeNode(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    parent_id: int = Field(default=ROOT_FOLDER_ID, foreign_key="treenode.id", index=True)
    name: str
    type: NodeType
    has_children: bool = False
    owner: str
    template_id: int | None = Field(default=None, foreign_key="template.id", unique=True, index=True)

class TreeNodeResponse(SQLModel):
    id: int
    parent_id: int
    name: str
    type: NodeType
    has_children: bool
    owner: str
    template_id: int | None = None
    children: list["TreeNodeResponse"] = []

class TemplateFileRole(str, Enum):
    """
    Where a stored file came from. The config.toml keys are used verbatim for the
    inputs a template declares, so a role maps straight back onto the toml.
    """
    config_toml = "config_toml_file"
    job = "job_file"
    dsl = "dsl_file"
    iidm = "iidm_file"
    dyd = "dyd_file"
    cyber_config = "cyber_config_file"
    scenario = "scenario_file"
    geo_data = "geo_data"
    asset_simulator_config = "asset_simulator_config_file"
    extra_io = "extra_io_file"
    mapping = "mapping_file"
    scada_iidm = "scada_backend.iidm_file"
    gm_iidm = "gm_backend.iidm_file"
    # Pulled in by walking the jobs file rather than named in the toml.
    jobs_dependency = "jobs_dependency"
    # Produced by main_configure during upload.
    generated = "generated"
    # config.toml other_files / other_dirs.
    other = "other"

class Template(SQLModel, table=True):
    """
    A template's identity. The file itself is stored in S3, the SQLModel stores its role and its relationships (owned by who, etc.)
    """
    id: int | None = Field(default=None, primary_key=True)
    name: str
    uuid: str

class TemplateFilePublic(SQLModel):
    # A config.toml key when the file is declared there, otherwise one of the
    # TemplateFileRole constants above.
    role: str
    # Path relative to the template root, so other_dirs keep their structure.
    filename: str
    s3_key: str

class TemplateDetails(SQLModel):
    name: str
    uuid: str
    owner: str
    files: list[TemplateFilePublic]

class TemplateFolder(SQLModel):
    node_id: int
    path: str

class TemplateRenamedResponse(SQLModel):
    template_id: int
    template_name: str