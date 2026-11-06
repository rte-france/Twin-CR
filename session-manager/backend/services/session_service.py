"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import secrets
from datetime import datetime, timedelta, UTC

import requests
from fastapi import HTTPException
from sqlmodel import select, Session

from backend.config import CONFIGURATOR_CLIENT_ENDPOINT, UPDATE_SESSION_STATE_TIMEOUT
from backend.db.models import AccessKey, GameSession, GameSessionCreate, AccessKeyTyped, SessionState, Template


class SessionService:
    def __init__(self, db_session: Session):
        self.session = db_session

    def get_or_404(self, session_id: int) -> GameSession:
        game_session = self.session.get(GameSession, session_id)
        if game_session is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return game_session

    def create_session(self, user_name:str, game_session_create: GameSessionCreate):
        gm_key_id = self.generate_access_key("GM")
        op_key_id = self.generate_access_key("OP")
        gk_key_id = self.generate_access_key("GK")

        template = self.session.get(Template, game_session_create.templateId)
        if template is None:
            raise HTTPException(
                status_code=404,
                detail=f"Template {game_session_create.templateId} not found",
            )

        new_game_session = GameSession.model_validate(
            game_session_create,
            update={"state": SessionState.READY,
                    "template_name": template.name, "template_uuid": template.uuid, "session_config_toml_name": game_session_create.config_toml_name,
                    "session_dsl_name": game_session_create.dsl_name,
                    "gm_key_id": gm_key_id, "operator_key_id": op_key_id, "golden_key_id": gk_key_id},
        )
        new_game_session.author = user_name

        self.session.add(new_game_session)
        self.session.commit()
        self.session.refresh(new_game_session)
        return new_game_session

    def set_access_keys(self, access_key_typed: AccessKeyTyped, access_key: AccessKey):
        data = access_key_typed.model_dump(exclude={"type"})

        for key, value in data.items():
            setattr(access_key, key, value)

        self.session.add(access_key)
        self.session.commit()
        self.session.refresh(access_key)

    def get_access_keys(self, game_session: GameSession):
        gm_key = self.session.exec(select(AccessKey).where(AccessKey.id == game_session.gm_key_id)).first()
        op_key = self.session.exec(select(AccessKey).where(AccessKey.id == game_session.operator_key_id)).first()
        gk_key = self.session.exec(select(AccessKey).where(AccessKey.id == game_session.golden_key_id)).first()
        keys = [
            self.to_access_key_typed(gm_key, "GM"),
            self.to_access_key_typed(op_key, "OP"),
            self.to_access_key_typed(gk_key, "GK"),
        ]
        return keys

    def to_access_key_typed(self, key: AccessKey, key_type: str) -> AccessKeyTyped:
        return AccessKeyTyped(
            id=key.id,
            password=key.password,
            validity_limit=key.validity_limit,
            usage=key.usage,
            revoked=key.revoked,
            type=key_type,
        )

    def generate_access_key(self, prefix: str) -> int | None:
        key = AccessKey(
            password=self.generate_password(prefix),
            validity_limit=datetime.now(UTC) + timedelta(hours=24),
            usage="multi",
        )
        self.session.add(key)
        self.session.commit()
        self.session.refresh(key)
        return key.id

    def generate_password(self, prefix: str) -> str:
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

        def part():
            return "".join(secrets.choice(chars) for _ in range(4))

        return f"{prefix}-{part()}-{part()}"

    def launch_session(self, session_id: int):
        game_session = self.get_or_404(session_id)
        game_session.started_at = datetime.now(UTC)
        game_session.state = SessionState.ONGOING

        context_id = game_session.template_uuid
        scenario_id = game_session.session_dsl_name
        config_path = game_session.session_config_toml_name

        response = requests.get(
            f"{CONFIGURATOR_CLIENT_ENDPOINT}/init/{context_id}",
            params={
                # Omitted when the template has no DSL, so the configurator
                # generates its minimal script instead of matching every object.
                "scenario_id": scenario_id or None,
                "config_path": config_path,
            },
            timeout=300,
        )

        if not response.ok:
            # The configurator relays the orchestrator's reason in its body, and
            # raise_for_status would drop it, leaving the client a bare 500.
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Configurator could not start the session: {detail}",
            )

        self.session.add(game_session)
        self.session.commit()
        self.session.refresh(game_session)
        return game_session

    def update_sessions_state(self, session_ids: list[int], session_state: SessionState):
        for session_id in session_ids:
            game_session = self.session.get(GameSession, session_id)
            if game_session is not None:
                game_session.state = session_state
        self.session.commit()

    def stop_session(self, session_id: int):
        game_session = self.get_or_404(session_id)
        game_session.ended_at = datetime.now(UTC)
        game_session.state = SessionState.ENDED
        self.session.commit()
        self.session.refresh(game_session)
        return game_session

    def delete_session(self, session_id: int):
        game_session = self.get_or_404(session_id)
        # The foreign keys point from the session at its keys, so nothing
        # cascades the other way; participations do, via the relationship.
        keys = [self.session.get(AccessKey, key_id) for key_id in (
            game_session.gm_key_id,
            game_session.operator_key_id,
            game_session.golden_key_id,
        )]
        self.session.delete(game_session)
        for key in keys:
            if key is not None:
                self.session.delete(key)
        self.session.commit()
