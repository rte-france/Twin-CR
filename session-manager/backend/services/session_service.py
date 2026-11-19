"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging
import secrets
import tomllib
import time
import warnings
from datetime import datetime, timedelta, UTC
from urllib.parse import quote, urlsplit

import requests
from urllib3.exceptions import InsecureRequestWarning
from fastapi import HTTPException
from sqlmodel import func, select, Session

from backend.config import CONFIGURATOR_CLIENT_ENDPOINT, UPDATE_SESSION_STATE_TIMEOUT, NOMAD_ADDR, NOMAD_TOKEN, \
    SESSION_JOB_HCL, SESSION_JOB_VARIABLES, SESSION_INIT_TIMEOUT, SESSION_PUBLIC_URL, SESSION_ROUTER_URL
from backend.db.models import AccessKey, GameSession, GameSessionCreate, AccessKeyTyped, SessionState, Template, \
    GameSessionPrivate
from backend.services.storage_service import template_data_prefix
from backend.services.nomad_service import NomadSessionClient, session_job_id, WAITING, INITIALIZED, FAILED, GONE

# Sessions as Nomad jobs in the Nomad infrastructure, else the session services of compose
nomad = NomadSessionClient(NOMAD_ADDR, NOMAD_TOKEN, SESSION_JOB_HCL, SESSION_JOB_VARIABLES) if NOMAD_ADDR else None


# Path of each service under the URL of a session: those of the Traefik routes of the session job
SESSION_SERVICE_PATHS = {
    "scada_backend_url": "argus-scada",
    "gm_backend_url": "argus-gm",
    "dsl_backend_url": "twincr-core",
    "lobby_backend_url": "configurator-client",
}


# Resources of the session services a context can set in its config.toml ([resources.<task>] tables), passed to the
# session job (variable resources): tasks of the job, and their settings
SESSION_RESOURCE_TASKS = ("nats", "clickhouse", "twincr-core", "configurator-client", "argus-scada", "argus-gm", "automata")
SESSION_RESOURCE_SETTINGS = ("cpu", "memory", "memory_max")
SESSION_JAVA_TASKS = ("argus-scada", "argus-gm")  # Also java_opts


def session_resources(config_toml: bytes) -> dict[str, dict[str, str]]:
    """The [resources.<task>] tables of the config.toml of a context, for the session job. Unknown tasks or settings
    are ignored with a warning."""
    tables = tomllib.loads(config_toml.decode()).get("resources", {})
    resources: dict[str, dict[str, str]] = {}
    for task, settings in tables.items():
        if task not in SESSION_RESOURCE_TASKS or not isinstance(settings, dict):
            logger.warning(f"Ignored [resources.{task}] of the context: not a service of the session job")
            continue
        allowed = SESSION_RESOURCE_SETTINGS + (("java_opts",) if task in SESSION_JAVA_TASKS else ())
        for name, value in settings.items():
            if name not in allowed:
                logger.warning(f"Ignored resources.{task}.{name} of the context (allowed: {', '.join(allowed)})")
                continue
            resources.setdefault(task, {})[name] = str(value)
    return resources


# Endpoint answering once each service is ready
SESSION_SERVICE_READY_PATHS = {
    "scada_backend_url": "/health",
    "gm_backend_url": "/health",
    "dsl_backend_url": "/status",
    "lobby_backend_url": "/status",
}

logger = logging.getLogger("uvicorn.error")


def session_routes_live(session_id: int) -> bool:
    """Whether the public URLs of the services of a session answer through Traefik (it routes a service once its health
    check passes, then picks it up from Consul): the URLs given to Argus then work when it joins."""
    public = urlsplit(SESSION_PUBLIC_URL)
    base_path = f"{public.path.rstrip('/')}/{session_job_id(session_id)}"
    for field, service_path in SESSION_SERVICE_PATHS.items():
        url = f"{SESSION_ROUTER_URL.rstrip('/')}{base_path}/{service_path}{SESSION_SERVICE_READY_PATHS[field]}"
        try:
            # Reached by address: the Host header selects the route, the certificate is that of the public name
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InsecureRequestWarning)
                if not requests.get(url, headers={"Host": public.netloc}, verify=False, timeout=5).ok:
                    return False
        except requests.RequestException:
            return False
    return True


# Placement time of the jobs of the sessions in warmup: their start timeout (SESSION_INIT_TIMEOUT) counts from there, a
# session waiting for cluster resources waits as long as needed
_placed_since: dict[str, float] = {}


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
        name = game_session_create.name.strip()
        duplicate = self.session.exec(
            select(GameSession).where(
                func.lower(func.trim(GameSession.name)) == name.lower(),
                GameSession.state != SessionState.ENDED,
            )
        ).first()
        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A session named \"{duplicate.name}\" already exists (#{duplicate.id}, {duplicate.state.value}): "
                       f"choose another name, or end that session first",
            )
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

    def launch_session(self, session_id: int, storage=None):
        game_session = self.get_or_404(session_id)
        if game_session.state != SessionState.READY:
            raise HTTPException(status_code=409, detail=f"Session {session_id} is {game_session.state.value}, not ready")
        game_session.started_at = datetime.now(UTC)
        game_session.state = SessionState.ONGOING

        context_id = game_session.template_uuid
        scenario_id = game_session.session_dsl_name
        config_path = game_session.session_config_toml_name

        if nomad is not None:
            # Not waited: the session stays in warmup, followed by the session monitor (monitor_nomad_sessions), until
            # ready (ongoing) or failed (back to ready, with the reason in status_detail)
            self.launch_session_job(session_id, context_id, scenario_id, config_path, storage)
            game_session.state = SessionState.WARMUP
            game_session.status_detail = "Submitting the session job"
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

    def launch_session_job(self, session_id: int, context_id: str, scenario_id: str | None, config_path: str,
                           storage=None):
        """Submits the Nomad job of the session (initialized by the job itself)."""
        job_id = session_job_id(session_id)
        variables = {
            "context_id": quote(context_id, safe=""),
            "config_path": quote(config_path, safe=""),
            # Empty when the template has no DSL, so the configurator generates its minimal script
            "scenario_id": quote(scenario_id or "", safe=""),
        }
        if SESSION_PUBLIC_URL:
            # Host of the Traefik routes of the session, matching the URLs given to Argus
            variables["public_host"] = urlsplit(SESSION_PUBLIC_URL).hostname or ""
        if storage is not None:
            # Resources of the services set by the context (else the defaults of the job)
            config_key = f"{template_data_prefix(context_id)}/{config_path}"
            try:
                resources = session_resources(storage.download_file(config_key))
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not read the resources of {config_key}: {exc}")
            if resources:
                variables["resources"] = resources
        nomad.stop(job_id, purge=True)  # Stop any previous failed launch of the session
        nomad.submit(job_id, variables)

    def monitor_nomad_sessions(self):
        """Follows the jobs of the sessions in warmup and ongoing (called periodically in the Nomad infrastructure):
        warmup → ongoing once ready, or back to ready if the launch fails; ongoing → ended if the job failed or
        disappeared (e.g. lost with its node). The progress is shown in status_detail."""
        sessions = self.session.exec(
            select(GameSession).where(GameSession.state.in_([SessionState.WARMUP, SessionState.ONGOING]))
        ).all()
        for game_session in sessions:
            job_id = session_job_id(game_session.id)
            try:
                progress = nomad.progress(job_id)
                if game_session.state == SessionState.WARMUP:
                    self._follow_launch(game_session, job_id, progress)
                elif progress.phase in (FAILED, GONE):
                    logger.warning(f"Session {game_session.id} ended unexpectedly: {progress.detail}")
                    game_session.state = SessionState.ENDED
                    game_session.ended_at = datetime.now(UTC)
                    game_session.status_detail = f"Ended unexpectedly: {progress.detail}"
            except HTTPException as exc:
                logger.warning(f"Could not follow session {game_session.id}: {exc.detail}")
        self.session.commit()

    def _follow_launch(self, game_session: GameSession, job_id: str, progress):
        if progress.phase in (FAILED, GONE):
            self._fail_launch(game_session, job_id, progress.detail, stop=progress.phase == FAILED)
            return
        if progress.phase != WAITING:
            _placed_since.setdefault(job_id, time.monotonic())
        if job_id in _placed_since and time.monotonic() - _placed_since[job_id] > SESSION_INIT_TIMEOUT:
            self._fail_launch(game_session, job_id, f"Not ready after {SESSION_INIT_TIMEOUT:.0f} s", stop=True)
            return
        if (progress.phase == INITIALIZED and nomad.backends_ready(job_id)
                and (not (SESSION_PUBLIC_URL and SESSION_ROUTER_URL) or session_routes_live(game_session.id))):
            logger.info(f"Session {game_session.id} ready")
            _placed_since.pop(job_id, None)
            game_session.state = SessionState.ONGOING
            game_session.status_detail = None
            return
        game_session.status_detail = progress.detail

    def _fail_launch(self, game_session: GameSession, job_id: str, reason: str, stop: bool):
        logger.warning(f"Launch of session {game_session.id} failed: {reason}")
        if stop:
            # Stopped but not purged: its logs stay available in Nomad to understand the failure
            nomad.stop(job_id)
        _placed_since.pop(job_id, None)
        game_session.state = SessionState.READY
        game_session.started_at = None
        game_session.status_detail = f"Launch failed: {reason}"

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
            _placed_since.pop(job_id, None)
        game_session.status_detail = None
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
