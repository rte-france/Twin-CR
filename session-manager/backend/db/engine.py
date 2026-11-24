"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import create_engine, SQLModel, Session, select

from backend.config import DB_ECHO, DB_URL
from backend.db.constants import ROOT_FOLDER_ID, USERS_FOLDER_ID, COMMON_FOLDER_ID, SYSTEM_OWNER
from backend.principal_handler import PrincipalHandler
from backend.services.session_service import SessionService
from backend.services.storage_service import StorageService
from backend.db.models import TreeNode, NodeType

# The fixed nodes every tree starts with. The root is a real row so that
# ROOT_FOLDER_ID resolves as a parent instead of dangling, and so the top level
# stays reachable as the children of folder 0.
SEED_NODES = (
    (ROOT_FOLDER_ID, None, "Root"),
    (USERS_FOLDER_ID, ROOT_FOLDER_ID, "Users"),
    (COMMON_FOLDER_ID, ROOT_FOLDER_ID, "Common"),
)

engine = create_engine(DB_URL, echo=DB_ECHO)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    initialize_tree()

def initialize_tree():
    with Session(engine) as session:
        for node_id, parent_id, name in SEED_NODES:
            # Looked up by id, not by name: a user folder that happens to be
            # called "Users" must not make this think the tree is already seeded.
            if session.get(TreeNode, node_id) is not None:
                continue
            session.add(
                TreeNode(
                    id=node_id,
                    parent_id=parent_id,
                    name=name,
                    type=NodeType.folder,
                    has_children=True,
                    owner=SYSTEM_OWNER,
                )
            )
        session.commit()

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

def get_storage_service(request: Request) -> StorageService:
    return request.app.state.storage_service
StorageDep = Annotated[StorageService, Depends(get_storage_service)]

def get_session_service(session: SessionDep) -> SessionService:
    return SessionService(session)
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]

principal_handler = PrincipalHandler()
CurrentUserDep = Annotated[dict, Depends(principal_handler.get_current_user)]
