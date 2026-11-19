"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging
import secrets
import time
import warnings
from datetime import datetime, timedelta, UTC
from urllib.parse import urlsplit

import requests
from urllib3.exceptions import InsecureRequestWarning
from fastapi import HTTPException
from sqlmodel import select, Session

from backend.config import CONFIGURATOR_CLIENT_ENDPOINT, UPDATE_SESSION_STATE_TIMEOUT, NOMAD_ADDR, NOMAD_TOKEN, \
    SESSION_JOB_HCL, SESSION_JOB_VARIABLES, SESSION_INIT_TIMEOUT, SESSION_PUBLIC_URL, SESSION_ROUTER_URL
from backend.db.models import AccessKey, GameSession, GameSessionCreate, AccessKeyTyped, SessionState, Template, \
    GameSessionPrivate
from backend.services.nomad_service import NomadSessionClient, session_job_id

# Sessions as Nomad jobs in the Nomad infrastructure, else the session services of compose
nomad = NomadSessionClient(NOMAD_ADDR, NOMAD_TOKEN, SESSION_JOB_HCL, SESSION_JOB_VARIABLES) if NOMAD_ADDR else None


# Path of each service under the URL of a session: those of the Traefik routes of the session job
SESSION_SERVICE_PATHS = {
    "scada_backend_url": "argus-scada",
    "gm_backend_url": "argus-gm",
    "dsl_backend_url": "twincr-core",
    "lobby_backend_url": "configurator-client",
}


# Endpoint answering once each service is ready
SESSION_SERVICE_READY_PATHS = {
    "scada_backend_url": "/health",
    "gm_backend_url": "/health",
    "dsl_backend_url": "/status",
    "lobby_backend_url": "/status",
}
SESSION_ROUTES_TIMEOUT = 60

logger = logging.getLogger("uvicorn.error")


def wait_session_routes(session_id: int) -> None:
    """Waits until the public URLs of the services of a session answer through Traefik (it routes a service once its
    health check passes, then picks it up from Consul): the URLs given to Argus then work when it joins. Best effort:
    on timeout, a warning only (Argus connects to its backends once they answer)."""
    public = urlsplit(SESSION_PUBLIC_URL)
    base_path = f"{public.path.rstrip('/')}/{session_job_id(session_id)}"
    deadline = time.monotonic() + SESSION_ROUTES_TIMEOUT
    for field, service_path in SESSION_SERVICE_PATHS.items():
        url = f"{SESSION_ROUTER_URL.rstrip('/')}{base_path}/{service_path}{SESSION_SERVICE_READY_PATHS[field]}"
        while True:
            try:
                # Reached by address: the Host header selects the route, the certificate is that of the public name
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", InsecureRequestWarning)
                    if requests.get(url, headers={"Host": public.netloc}, verify=False, timeout=5).ok:
                        break
            except requests.RequestException:
                pass
            if time.monotonic() > deadline:
                logger.warning(f"Route of {service_path} of session {session_id} not live after "
                               f"{SESSION_ROUTES_TIMEOUT} s ({url}, Host: {public.netloc})")
                return
            time.sleep(1)
    logger.info(f"Routes of session {session_id} live")


def session_private_view(game_session: GameSession) -> GameSessionPrivate:
    """The session with the URLs of its services, when they are per session (Nomad infrastructure)."""
    urls = {}
    if SESSION_PUBLIC_URL and game_session.id is not None:
        base = f"{SESSION_PUBLIC_URL.rstrip('/')}/{session_job_id(game_session.id)}"
        urls = {field: f"{base}/{path}" for field, path in SESSION_SERVICE_PATHS.items()}
    return GameSessionPrivate.model_validate(game_session, update=urls)


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

        if nomad is not None:
            self.launch_session_job(session_id, context_id, scenario_id, config_path)
            self.session.add(game_session)
            self.session.commit()
            self.session.refresh(game_session)
            return game_session

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

    def launch_session_job(self, session_id: int, context_id: str, scenario_id: str | None, config_path: str):
        """Submits the Nomad job of the session and waits for its initialization (done by the job itself)."""
        job_id = session_job_id(session_id)
        variables = {
            "context_id": context_id,
            "config_path": config_path,
            # Empty when the template has no DSL, so the configurator generates its minimal script
            "scenario_id": scenario_id or "",
        }
        if SESSION_PUBLIC_URL:
            # Host of the Traefik routes of the session, matching the URLs given to Argus
            variables["public_host"] = urlsplit(SESSION_PUBLIC_URL).hostname or ""
        nomad.submit(job_id, variables)
        try:
            nomad.wait_initialized(job_id, SESSION_INIT_TIMEOUT)
        except HTTPException:
            # Stopped but not purged: its logs stay available in Nomad to understand the failure
            nomad.stop(job_id)
            raise
        if SESSION_PUBLIC_URL and SESSION_ROUTER_URL:
            wait_session_routes(session_id)

    def update_sessions_state(self, session_ids: list[int], session_state: SessionState):
        for session_id in session_ids:
            game_session = self.session.get(GameSession, session_id)
            if game_session is not None:
                game_session.state = session_state
        self.session.commit()

    def stop_session(self, session_id: int):
        game_session = self.get_or_404(session_id)
        if nomad is not None:
            # Archive first (skipped if already done at the end of the simulation), the services are then removed
            job_id = session_job_id(session_id)
            nomad.archive(job_id)
            nomad.stop(job_id)
        game_session.ended_at = datetime.now(UTC)
        game_session.state = SessionState.ENDED
        self.session.commit()
        self.session.refresh(game_session)
        return game_session

    def delete_session(self, session_id: int):
        game_session = self.get_or_404(session_id)
        if nomad is not None:
            nomad.stop(session_job_id(session_id), purge=True)
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
