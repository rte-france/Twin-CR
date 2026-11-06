"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""
import asyncio
import datetime
import hmac
import logging
import mimetypes
import re
import shutil
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
from uuid import uuid4

import tomlkit
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import case, func
from sqlmodel import select, Session

from backend.config import KEYCLOAK_CLIENT_ID, UPDATE_SESSION_STATE_TIMEOUT, CONFIGURATOR_CLIENT_ENDPOINT
from backend.db.constants import USERS_FOLDER_ID, ROOT_FOLDER_ID
from backend.db.engine import create_db_and_tables, SessionDep, StorageDep, SessionServiceDep, \
    CurrentUserDep, principal_handler, engine
from backend.db.models import GameSession, GameSessionCreate, GameSessionPrivate, User, TreeNode, \
    NodeType, NewFolder, SessionState, Template, TemplateFileRole, TemplateFilePublic, TemplateDetails, \
    TemplateFolder, AccessKey, AccessKeyTyped, GameSessionOwn, SessionConnect, TemplateRenamedResponse, TreeNodeResponse
from backend.services import storage_service
from backend.services.session_service import SessionService
from backend.services.storage_service import StorageService

TEMPLATE_NAME_RE = re.compile(r"[A-Za-z0-9 ._-]{1,100}")

# Paths inside the orchestrator container, as in the example config.toml files.
# RTE's build carries models the public one does not, so a context is tied to one.
DYNAWO_SCRIPT_PATHS = {
    "public": "/home/orchestrator/simulators/dynawo/dynawo.sh",
    "rte": "/home/orchestrator/simulators/dynawo-rte/dynawo.sh",
}

DYNAWO_DDB_PATHS = {
    "public": "/home/session-manager/simulators/dynawo/ddb",
    "rte": "/home/session-manager/simulators/dynawo-rte/ddb",
}

# Configurator rules of the models only in RTE's build, merged over the default ones (mounted by the Twin-CR compose override)
DYNAWO_EXTRA_RULES_DIRS = {
    "public": None,
    "rte": "/home/session-manager/dynawo_rules",
}

load_dotenv()
import main_configure # need env var
import dynawo_deps
import jobs_editor

template_router = APIRouter(prefix="/templates", tags=["Templates"])
session_router = APIRouter(prefix="/sessions", tags=["Sessions"])
tree_router = APIRouter(prefix="/tree", tags=["Tree"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    app.state.storage_service = StorageService()
    task = asyncio.create_task(update_session_state_job())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("uvicorn.error")

# Unhandled errors as JSON with a detail, which the clients surface, instead of Starlette's plain-text 500
@app.middleware("http")
async def unhandled_errors_as_json(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": f"{type(exc).__name__}: {exc}"},
        )

# TODO : For now, the workflow is mono-session, because we launch only one session locally.
#       Change this method when multi session will be available.
async def update_session_state_job() -> None:
    while True:
        try:
            configurator_status = await asyncio.to_thread(get_configurator_status)
            session_state = None
            if configurator_status == "NOT READY":
                session_state = SessionState.READY # session is ready to be initialized.
            elif configurator_status == "READY":
                session_state = SessionState.ONGOING  # session has been initialized. Configurator is ready to start simulation.

            with Session(engine) as session:
                session_ids = session.exec(select(GameSession.id).where(GameSession.state != SessionState.ENDED)).all()
                service = SessionService(session)
                service.update_sessions_state(session_ids, session_state)
        except Exception as e:
            logger.error("Configurator could not get the session status: %s", e)
        finally:
            await asyncio.sleep(UPDATE_SESSION_STATE_TIMEOUT)

def get_configurator_status() -> str:
    try:
        response = requests.get(f"{CONFIGURATOR_CLIENT_ENDPOINT}/status", timeout=UPDATE_SESSION_STATE_TIMEOUT - 1)
    except Exception as e:
        raise e
    if response.ok:
        configurator_status = response.json().get("status", response.text)
        return configurator_status
    else:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Configurator could not get the session status : {detail}",
        )

def require_role(role: str):
    """Reject unless the token grants this client role."""
    def check(current_user:CurrentUserDep):
        granted = (
            current_user.get("resource_access", {})
            .get(KEYCLOAK_CLIENT_ID, {})
            .get("roles", [])
        )
        if role not in granted:
            raise HTTPException(status_code=403, detail=f"Requires the {role} role")
        return current_user
    return check


def own_session(session, session_id: int, current_user) -> GameSession:
    """
    A session the caller authored, or 404/403.

    A role is not authorization: session_launcher says you may run exercises,
    not that you may run or delete someone else's.
    """
    game_session = session.get(GameSession, session_id)
    if game_session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if game_session.author != current_user["preferred_username"]:
        raise HTTPException(status_code=403, detail="Can't act on another user's session")
    return game_session


TEMPLATE_KEY_RE = re.compile(r"CONTEXTS/(?P<uuid>[^/]+)/")


def owner_of_key(session, key: str) -> str:
    """
    Who owns the template a storage key belongs to.

    The key arrives from the client, so it is resolved back to a template and
    its tree node rather than trusted.
    """
    match = TEMPLATE_KEY_RE.match(key)
    if not match:
        raise HTTPException(status_code=404, detail="Not a template file key")
    template = session.exec(
        select(Template).where(Template.uuid == match.group("uuid"))
    ).first()
    if template is None:
        raise HTTPException(status_code=404, detail="No template for that key")
    node = session.exec(
        select(TreeNode).where(TreeNode.template_id == template.id)
    ).first()
    if node is None:
        raise HTTPException(status_code=404, detail="Template is not attached to the tree")
    return node.owner


def require_key_owner(session, key: str, current_user) -> None:
    if owner_of_key(session, key) != current_user["preferred_username"]:
        raise HTTPException(status_code=403, detail="Can't read another user's template files")


def stored_name(upload_file: UploadFile | None) -> str | None:
    """The name a file is actually stored under, or None if it was not sent."""
    return safe_filename(upload_file) if upload_file else None


def safe_filename(upload_file: UploadFile) -> str:
    name = Path(upload_file.filename or "").name
    if not name or name.startswith("."):
        raise HTTPException(status_code=400, detail=f"Unusable filename: {upload_file.filename!r}")
    return name


#
# REST
#

@app.get("/")
def read_root():
    return {"Message": "Session Manager online"}

@app.get("/status")
def status():
    return {"status": "ok"}

### TEMPLATE TREE VIEW MANAGEMENT ###

@tree_router.get("/init_user")
def init_user(session: SessionDep, current_user: CurrentUserDep):
    """
    Initialize a user’s home directory if it does not exist
    :param session: db session dependency
    :param current_user: user logged in
    :return:
    """
    user_name = current_user["preferred_username"]
    statement = select(TreeNode).where(
        (TreeNode.parent_id == USERS_FOLDER_ID)
        & (TreeNode.name == user_name)
        & (TreeNode.type == NodeType.folder)
    )
    node = session.exec(statement).first()
    if not node:
        session.add(
            TreeNode(
                parent_id=USERS_FOLDER_ID,
                name=user_name,
                type=NodeType.folder,
                has_children=True,
                owner=user_name,
            )
        )
        session.commit()

@tree_router.get("/{folder_id}/children", response_model=list[TreeNode])
def get_children(folder_id: int, session: SessionDep):
    """
    Get the children nodes of a given folder, sorted alphabetically (case-insensitive)
    :param folder_id: the given folder id
    :param session: db session dependency
    :return: list of children nodes
    """
    return session.exec(
        select(TreeNode)
        .where(TreeNode.parent_id == folder_id)
        .order_by(
            case(
                (TreeNode.type == NodeType.folder, 0),
                else_=1,
            ),
            func.lower(TreeNode.name),
        )
    ).all()

@tree_router.get("/{folder_id}/subtree", response_model=list[TreeNodeResponse])
def get_tree(folder_id: int, session: SessionDep):
    """
    Get the subtree from a given folder (-> recursively the children nodes of a given folder), sorted alphabetically (case-insensitive)
    :param folder_id: the given folder id
    :param session: db session dependency
    :return: list of children nodes
    """
    return get_subtree(folder_id, session)

def get_subtree(folder_id: int, session: SessionDep) -> list[TreeNodeResponse]:
    # TreeNode.id != ROOT_FOLDER_ID is used to avoid infinite recursion, because we chose that a TreeNode MUST have a parent,
    # which is tricky for the root TreeNode, so we chose that the root is its own parent.
    children = session.exec(
        select(TreeNode)
        .where((TreeNode.parent_id == folder_id) & (TreeNode.id != ROOT_FOLDER_ID))
        .order_by(
            case(
                (TreeNode.type == NodeType.folder, 0),
                else_=1,
            ),
            func.lower(TreeNode.name),
        )
    ).all()

    result: list[TreeNodeResponse] = []
    for child in children:
        node = child.model_dump()
        if child.type == NodeType.folder and child.has_children:
            node["children"] = get_subtree(child.id, session)
        else:
            node["children"] = []
        result.append(node)
    return result

@tree_router.post("/new_folder")
def create_folder(new_folder: NewFolder, session: SessionDep,
                  current_user=Depends(require_role("template_manager"))):
    user_name = current_user["preferred_username"]
    parent_folder = session.get(TreeNode, new_folder.parent_id)

    if not parent_folder:
        raise HTTPException(status_code=404, detail="Parent folder not found")
    if parent_folder.type != NodeType.folder:
        raise HTTPException(status_code=404, detail="Parent is not a folder")
    if parent_folder.owner != user_name:
        raise HTTPException(status_code=403, detail="Can't add a folder to another user's folder")

    session.add(
        TreeNode(
            name=new_folder.name,
            type=NodeType.folder,
            parent_id=new_folder.parent_id,
            owner=user_name,
        )
    )
    # The flag FileTree uses to decide whether a folder is expandable.
    parent_folder.has_children = True
    session.add(parent_folder)
    session.commit()

@tree_router.get("/folders", response_model=list[TemplateFolder])
def get_template_folders(session: SessionDep, current_user: CurrentUserDep):
    """
    Get all template folders from logged user, with their absolute path from user's root folder
    :param session: db session dependency
    :param current_user: current user dependency
    :return: list of TemplateFolders
    """
    user_name = current_user["preferred_username"]
    nodes = session.exec(select(TreeNode).where((TreeNode.owner == user_name) & (TreeNode.type == NodeType.folder))).all()
    template_folders = build_template_folders(nodes)
    return template_folders

def build_template_folders(nodes: list[TreeNode]) -> list[TemplateFolder]:
    """
    Form given list of nodes, build a list of TemplateFolder, representing a folder tree
    where each TemplateFolder has its absolute path in TemplateFolder.path
    ex :
    /user1/my folder
    /user1/my folder/folder test
    :param nodes: list of TreeNodes
    :return: list of TemplateFolders
    """
    node_by_id: dict[int, TreeNode] = {
       node.id: node
       for node in nodes
       if node.id is not None
    }
    cache: dict[int, str] = {}

    def build_path(node: TreeNode) -> str:
        if node.id in cache:
            return cache[node.id]

        if node.parent_id is None or node.parent_id not in node_by_id:
            path = f"/{node.name}"
        else:
            parent = node_by_id[node.parent_id]
            path = f"{build_path(parent)}/{node.name}"

        cache[node.id] = path
        return path

    return [
        TemplateFolder(
            node_id=node.id,
            path=build_path(node),
        )
        for node in nodes
        if node.type == NodeType.folder and node.id is not None
    ]

@tree_router.delete("/{node_id}")
def delete_folder(session: SessionDep, storage: StorageDep, node_id: int,
                  current_user=Depends(require_role("template_manager"))):
    user_name = current_user["preferred_username"]
    statement = select(TreeNode).where(TreeNode.id == node_id)
    node_to_delete = session.exec(statement).first()
    if not node_to_delete :
        raise HTTPException(status_code=404, detail="Folder not found")
    elif node_to_delete.owner != user_name:
        raise HTTPException(status_code=403, detail="Can't delete a folder from another user")
    elif node_to_delete.owner == user_name and node_to_delete.parent_id == USERS_FOLDER_ID:
        raise HTTPException(status_code=403, detail="Can't delete your own root folder")
    else:
        delete_node(session, storage, node_to_delete)
        return {"parent_id": node_to_delete.parent_id}

# Delete node and its content recursively
def delete_template_of(session: SessionDep, storage: StorageDep, node: TreeNode) -> None:
    """Remove a template node's stored files and its rows."""
    template = session.get(Template, node.template_id) if node.template_id else None
    if template is None:
        return
    # By prefix, so anything under the template goes — including files the
    # upload wrote before a failure, which no per-file record would know about.
    storage.delete_template(template.uuid)
    session.delete(template)


def delete_node(session: SessionDep, storage: StorageDep, node: TreeNode) -> None:
    if node.type == NodeType.folder:
        children = session.exec(
            select(TreeNode).where(TreeNode.parent_id == node.id)
        ).all()

        for child in children:
            if child.type == NodeType.folder:
                delete_node(session, storage, child)
            else:
                delete_template_of(session, storage, child)
                session.delete(child)
    else:
        delete_template_of(session, storage, node)

    session.delete(node)
    session.commit()

### SESSIONS MANAGEMENT ###

@session_router.get("", response_model=list[GameSession])
def list_sessions(session: SessionDep, live_only: bool = True):
    """
    Get active sessions
    :param session:
    :param live_only:
    :return:
    """
    # Ordered, so a client diffing the response cannot mistake a reordering for
    # a change.
    statement = select(GameSession).order_by(GameSession.id)
    if live_only:
        statement = statement.where(GameSession.state != SessionState.ENDED)
    return session.exec(statement).all()

@session_router.get("/me", response_model=list[GameSessionOwn])
def list_sessions_from_user(session: SessionDep, current_user: CurrentUserDep):
    """
    Get list sessions from logged user
    :param session:
    :param current_user:
    :return:
    """
    user_name = current_user["preferred_username"]
    statement = select(GameSession).where(GameSession.author == user_name)
    res = session.exec(statement).all()
    return res

@session_router.post("/new_session", response_model=GameSessionPrivate)
def create_session(game_session: GameSessionCreate, session_service: SessionServiceDep,
                   current_user=Depends(require_role("session_launcher"))):
    """
    Create a Session from given parameters
    :param game_session:
    :param session_service:
    :param current_user:
    :return:
    """
    db_session = session_service.create_session(current_user["preferred_username"], game_session)
    return db_session

@session_router.get("/keys/{session_id}", response_model=list[AccessKeyTyped])
def get_access_keys(session_id: int, session_service: SessionServiceDep, session: SessionDep,
                    current_user=Depends(require_role("session_launcher"))):
    game_session = own_session(session, session_id, current_user)
    return session_service.get_access_keys(game_session)

@session_router.post("/key")
def set_access_key(access_key_typed: AccessKeyTyped, session_service: SessionServiceDep, session: SessionDep,
                   current_user=Depends(require_role("session_launcher"))):
    access_key = session.get(AccessKey, access_key_typed.id)
    if not access_key:
        raise HTTPException(status_code=404, detail="Access key not found")

    owner = session.exec(
        select(GameSession).where(
            (GameSession.gm_key_id == access_key.id)
            | (GameSession.operator_key_id == access_key.id)
            | (GameSession.golden_key_id == access_key.id)
        )
    ).first()
    if owner is None:
        raise HTTPException(status_code=404, detail="Access key is not attached to a session")
    if owner.author != current_user["preferred_username"]:
        raise HTTPException(status_code=403, detail="Can't edit another user's access keys")
    session_service.set_access_keys(access_key_typed, access_key)


@session_router.get("/{session_id}", response_model=GameSession)
def get_session(session_id: int, session: SessionDep):
    game_session = session.get(GameSession, session_id)
    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return game_session

@session_router.post("/{session_id}/launch", response_model=GameSession)
def launch_session(session_id: int, session_service: SessionServiceDep, session: SessionDep,
                   current_user=Depends(require_role("session_launcher"))):
    own_session(session, session_id, current_user)
    game_session = session_service.launch_session(session_id)
    return game_session

@session_router.post("/{session_id}/stop", response_model=GameSession)
def stop_session(session_id: int, session_service: SessionServiceDep, session: SessionDep,
                 current_user=Depends(require_role("session_launcher"))):
    own_session(session, session_id, current_user)
    game_session = session_service.stop_session(session_id)
    return game_session

@session_router.delete("/{session_id}/delete")
def delete_session(session_id: int, session_service: SessionServiceDep, session: SessionDep,
                   current_user=Depends(require_role("session_launcher"))):
    own_session(session, session_id, current_user)
    session_service.delete_session(session_id)

def matching_key(password_gm: str, password_operator: str,
                 gm_key: AccessKey, op_key: AccessKey,
                 golden_key: AccessKey) -> tuple[str, AccessKey] | None:
    """
    The role and the key that was actually presented, or None if none matched.

    The golden key is accepted in either field and takes the role of the field
    it was entered in, having no role of its own. The key comes back too, so the
    caller can check whether it is revoked, expired or single-use.
    """
    for password, role, own_key in (
        (password_gm, "gm", gm_key),
        (password_operator, "scada", op_key),
    ):
        if not password:
            continue
        if hmac.compare_digest(password, own_key.password):
            return role, own_key
        if hmac.compare_digest(password, golden_key.password):
            return role, golden_key
    return None


@session_router.post("/connect", response_model=GameSessionPrivate)
def connect_session(connect: SessionConnect, session: SessionDep,
                    current_user: CurrentUserDep):
    username = current_user["preferred_username"]
    game_session = session.get(GameSession, connect.game_session_id)

    if not game_session:
        raise HTTPException(status_code=404, detail="Session not found")

    golden_key = session.get(AccessKey, game_session.golden_key_id)
    gm_key = session.get(AccessKey, game_session.gm_key_id)
    op_key = session.get(AccessKey, game_session.operator_key_id)
    if not (golden_key and gm_key and op_key):
        raise HTTPException(status_code=500, detail="Session is missing its access keys")

    matched = matching_key(connect.password_gm, connect.password_operator,
                           gm_key, op_key, golden_key)
    if matched is None:
        raise HTTPException(status_code=401, detail="Incorrect password")
    role, key = matched

    if key.revoked:
        raise HTTPException(status_code=401, detail="That access key has been revoked")

    if key.validity_limit < datetime.datetime.now(datetime.UTC):
        raise HTTPException(status_code=401, detail="That access key has expired")

    participation = session.exec(
        select(User).where(
            (User.username == username) & (User.game_session_id == connect.game_session_id)
        )
    ).first()
    if participation is None:
        session.add(User(username=username, game_session_id=connect.game_session_id, role=role))
    else:
        participation.role = role

    # A single-use key is spent once it has let someone in.
    if key.usage == "unique":
        key.revoked = True
        session.add(key)

    session.commit()

    return game_session


### TEMPLATES MANAGEMENT ###

@template_router.get("/{template_id}", response_model=TemplateDetails)
def template_details(session: SessionDep, storage: StorageDep, template_id: int):
    """
    Get template details from given template id
    :param session: db session dependency
    :param template_id: given template id
    :return: Template details
    """
    template = session.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_node = session.exec(
        select(TreeNode).where(TreeNode.template_id == template_id)
    ).first()
    if not template_node:
        raise HTTPException(status_code=404, detail="Template is not attached to the tree")

    # The bucket says which files exist; the manifest only says what they are.
    data_prefix = storage_service.template_data_prefix(template.uuid)
    roles = storage.read_roles(template.uuid)

    return TemplateDetails(
        name=template.name,
        uuid=template.uuid,
        owner=template_node.owner,
        files=[
            TemplateFilePublic(
                role=roles.get(relative, TemplateFileRole.other.value),
                filename=relative,
                s3_key=f"{data_prefix}/{relative}",
            )
            for relative in storage.list_template_files(template.uuid)
        ],
    )

def write_file_path(working_dir, upload_file: UploadFile = File(...)):
    upload_file_path = working_dir / safe_filename(upload_file)
    with open(upload_file_path, "wb") as target:
        shutil.copyfileobj(upload_file.file, target)
    return upload_file_path

def validate_template_name(name: str) -> None:
    """
    The name goes into the S3 key, so it has to survive being a path segment: no
    slashes or dot-dot to climb out of the template prefix, and no # or ? to cut a
    URL short.
    """
    if not TEMPLATE_NAME_RE.fullmatch(name):
        raise HTTPException(
            status_code=400,
            detail="A template name may contain letters, digits, spaces, dots, "
                   "underscores and hyphens only, up to 100 characters",
        )


def _store_template(
    session,
    storage,
    *,
    template_name: str,
    folder_id: int,
    owner: str,
    working_dir: Path,
    files: dict[Path, TemplateFileRole],
) -> Template:
    """
    Upload every file to S3 under one template prefix and record a row for each.

    `files` maps an on-disk path inside working_dir to the role it plays. Paths
    are stored relative to working_dir so other_dirs keep their structure.
    """
    validate_template_name(template_name)

    template_uuid = f"{template_name}_{uuid4()}"
    template_folder_key = storage_service.template_data_prefix(template_uuid)

    parent = session.get(TreeNode, folder_id)
    if not parent or parent.type != NodeType.folder:
        raise HTTPException(status_code=404, detail="Parent folder not found")
    if parent.owner != owner:
        raise HTTPException(status_code=403, detail="Can't add a template to another user's folder")

    roles: dict[str, str] = {}
    for path, role in files.items():
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"Missing file: {path.name}")
        relative = path.relative_to(working_dir).as_posix()
        storage.upload_file(f"{template_folder_key}/{relative}", path, guess_content_type(path))
        roles[relative] = role
    storage.write_roles(template_uuid, roles)

    template = Template(name=template_name, uuid=template_uuid)
    session.add(template)
    session.flush()  # assign template.id before the tree node references it

    session.add(
        TreeNode(
            name=template_name,
            type=NodeType.template,
            parent_id=folder_id,
            owner=owner,
            has_children=False,
            template_id=template.id,
        )
    )
    parent.has_children = True
    session.add(parent)
    session.commit()
    session.refresh(template)
    return template


def guess_content_type(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(path.name)
    return content_type or "application/octet-stream"


@template_router.post("/new_template")
def create_template(
    storage: StorageDep,
    session: SessionDep,
    template_name: str = Form(...),
    folder_id: int = Form(...),
    job_file: UploadFile = File(...),
    dynawo_files: list[UploadFile] = File(default_factory=list),
    dynawo_relative_paths: list[str] = Form(default_factory=list),
    dsl_file: UploadFile | None = File(None),
    cyber_config_file: UploadFile | None = File(None),
    asset_simulator_config_file: UploadFile | None = File(None),
    extra_io_file: UploadFile | None = File(None),
    geo_data: UploadFile | None = File(None),
    scenario_file: UploadFile | None = File(None),
    mapping_file: UploadFile | None = File(None),
    scada_iidm_file: UploadFile | None = File(None),
    gm_iidm_file: UploadFile | None = File(None),
    other_files: list[UploadFile] = File(default_factory=list),
    automata_commands: list[str] = Form(default_factory=list),
    period: float = Form(1),
    dynawo_variant: str = Form("public"),
    current_user=Depends(require_role("template_manager")),
):
    """
    Create a template from a minimal set of inputs and generate the rest.

    Only the jobs file is required: the IIDM, dyd and par files it needs come
    with it in `dynawo_files` (the client resolves them via
    /templates/dynawo_dependencies), and the connectors, curves and SCADA I/O
    files plus the config.toml are generated here. So is the asset simulator
    config, unless one is uploaded.
    """
    user_name = current_user["preferred_username"]
    validate_template_name(template_name)
    if dynawo_variant not in DYNAWO_SCRIPT_PATHS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown dynawo_variant {dynawo_variant!r}; expected one of {', '.join(DYNAWO_SCRIPT_PATHS)}",
        )
    if len(dynawo_files) != len(dynawo_relative_paths):
        raise HTTPException(
            status_code=400,
            detail=f"Got {len(dynawo_files)} Dynawo files for {len(dynawo_relative_paths)} paths",
        )
    if cyber_config_file and not mapping_file:
        # Without a mapping the SCADA I/O falls back to naming its nodes after
        # the IIDM substations, which the supplied graph does not contain.
        raise HTTPException(
            status_code=400,
            detail="A telesignal mapping file is required alongside a cyber network file",
        )
    if scada_iidm_file and ".arc" in Path(safe_filename(scada_iidm_file)).suffixes:
        # The current limits are read from it with pypowsybl, which has no DIE importer. The file
        # picker cannot rule the arc out on its own, since it usually arrives as .arc.xz.
        raise HTTPException(
            status_code=400,
            detail="The SCADA grid model must be an XIIDM, optionally xz or zst compressed; the arc is not supported",
        )

    optional: dict[TemplateFileRole, UploadFile | None] = {
        TemplateFileRole.dsl: dsl_file,
        TemplateFileRole.cyber_config: cyber_config_file,
        TemplateFileRole.asset_simulator_config: asset_simulator_config_file,
        TemplateFileRole.extra_io: extra_io_file,
        TemplateFileRole.geo_data: geo_data,
        TemplateFileRole.scenario: scenario_file,
        TemplateFileRole.mapping: mapping_file,
        TemplateFileRole.scada_iidm: scada_iidm_file,
        TemplateFileRole.gm_iidm: gm_iidm_file,
    }

    with TemporaryDirectory() as tmp_dir:
        working_dir = Path(tmp_dir).resolve()
        stored: dict[Path, str] = {}

        job_path = write_file_path(working_dir, job_file)
        stored[job_path] = TemplateFileRole.job.value

        for upload, relative in zip(dynawo_files, dynawo_relative_paths):
            target = (working_dir / relative).resolve()
            if not target.is_relative_to(working_dir.resolve()):
                raise HTTPException(status_code=400, detail=f"Unsafe path: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as handle:
                shutil.copyfileobj(upload.file, handle)
            stored[target] = TemplateFileRole.jobs_dependency.value

        paths: dict[TemplateFileRole, Path] = {}
        for role, upload in optional.items():
            if upload is not None:
                paths[role] = write_file_path(working_dir, upload)
                stored[paths[role]] = role.value

        # Files only used at runtime (e.g. python automata), listed in the config.toml other_files
        other_names: list[str] = []
        for upload in other_files:
            target = working_dir / safe_filename(upload)
            if target in stored:
                raise HTTPException(status_code=400, detail=f"Other file {target.name} has the name of another input")
            stored[write_file_path(working_dir, upload)] = TemplateFileRole.other.value
            other_names.append(target.name)

        # The jobs file names its own inputs, so anything it references has to be
        # here before the configurator can run.
        missing = sorted(p.name for p in dynawo_deps.missing_dynawo_files(job_path))
        # The connectors file is an output, so it is expected to be absent.
        missing = [m for m in missing if not m.startswith("RTConnectors")]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"{job_file.filename} references files that were not uploaded: {', '.join(missing)}",
            )

        iidm_name = jobs_editor.JobsFile(job_path).iidm_file()
        if not iidm_name:
            raise HTTPException(
                status_code=400,
                detail=f"{job_file.filename} declares no iidmFile",
            )

        # Run main_configure in a child process, not a thread, to
        # 1. avoid pypowsybl locking the GIL
        # 2. reclaim the lxml/pypowsybl memory on completion
        try:
            with ProcessPoolExecutor(max_workers=1) as pool:
                generated_dyd, mock_cyber_config, generated_asset_simulator_config = pool.submit(
                    main_configure.main_from_jobs,
                    job_path,
                    DYNAWO_DDB_PATHS[dynawo_variant],
                    paths.get(TemplateFileRole.cyber_config),
                    paths.get(TemplateFileRole.mapping),
                    None,
                    True,
                    working_dir,
                    period,
                    asset_simulator_config_file is None,
                    paths.get(TemplateFileRole.scada_iidm),
                    DYNAWO_EXTRA_RULES_DIRS[dynawo_variant],
                    paths.get(TemplateFileRole.extra_io),
                ).result()
        except ValueError as e:
            # Invalid inputs, e.g. an extra io file with an unknown key or an id already generated
            raise HTTPException(status_code=400, detail=str(e))

        scada_suffix = "" if (paths.get(TemplateFileRole.cyber_config) and paths.get(TemplateFileRole.mapping)) else "_no_map"
        generated = [
            generated_dyd,
            "curves.xml",
            "game_master_inputs.json",
            "game_master_outputs.json",
            f"scada_outputs{scada_suffix}.json",
            f"scada_inputs{scada_suffix}.json",
        ]
        if mock_cyber_config:
            generated.append(mock_cyber_config)
        if generated_asset_simulator_config:
            generated.append(generated_asset_simulator_config)
        for name in generated:
            stored[working_dir / name] = TemplateFileRole.generated.value

        config_path = working_dir / "config.toml"
        config_path.write_text(
            build_config_toml(
                job_file=safe_filename(job_file),
                dsl_file=stored_name(dsl_file),
                cyber_config_file=stored_name(cyber_config_file) or mock_cyber_config,
                scenario_file=stored_name(scenario_file),
                geo_data=stored_name(geo_data),
                asset_simulator_config_file=stored_name(asset_simulator_config_file) or generated_asset_simulator_config,
                extra_io_file=stored_name(extra_io_file),
                other_files=other_names,
                automata_commands=[c.strip() for c in automata_commands if c.strip()],
                mapping_file=stored_name(mapping_file),
                scada_iidm_file=stored_name(scada_iidm_file),
                gm_iidm_file=stored_name(gm_iidm_file),
                connectors_dyd=generated_dyd,
                iidm_file=iidm_name,
                dynawo_path=DYNAWO_SCRIPT_PATHS[dynawo_variant],
                scada_suffix=scada_suffix,
                period=period,
            )
        )
        stored[config_path] = TemplateFileRole.config_toml.value

        template = _store_template(
            session, storage,
            template_name=template_name, folder_id=folder_id, owner=user_name,
            working_dir=working_dir, files=stored,
        )
        return {"template_id": template.id, "uuid": template.uuid}


def build_config_toml(*, job_file: str, dsl_file: str | None, cyber_config_file: str | None,
                      scenario_file: str | None, geo_data: str | None,
                      asset_simulator_config_file: str | None, extra_io_file: str | None,
                      mapping_file: str | None,
                      scada_iidm_file: str | None, gm_iidm_file: str | None,
                      connectors_dyd: str, iidm_file: str, dynawo_path: str,
                      scada_suffix: str, period: float, other_files: list[str] | None = None,
                      automata_commands: list[str] | None = None) -> str:
    """
    Write the config.toml for a guided upload.

    The orchestrator reads these with get_or_throw and refuses to start if any
    is absent (see Orchestrator/*/*.cpp): [master], [input_files] and [hmi], the
    last needing only `location`. [input_files.scada_backend] and
    [input_files.gm_backend] are optional. The
    Dynawo inputs proper are deliberately left out, since the orchestrator
    resolves those from the jobs file.
    """
    config = tomlkit.document()
    # Run by automata_launcher.py from the config.toml directory, e.g. "python tcp_blocker.py"
    config["automata_commands"] = list(automata_commands or [])

    master = tomlkit.table()
    master["period"] = period
    master["speedup"] = 1
    master["myEnvDynawo_path"] = dynawo_path
    config["master"] = master

    input_files = tomlkit.table()
    input_files["job_file"] = job_file
    # Required by DynawoInterface, and it is the generated connectors file.
    input_files["dyd_file"] = connectors_dyd
    # Read from the jobs file: the argus backends require it here.
    input_files["iidm_file"] = iidm_file
    if dsl_file:
        input_files["dsl_file"] = dsl_file
    # The orchestrator requires both; omitting rather than blanking them makes it
    # report the missing key instead of failing later on an empty filename.
    if scenario_file:
        input_files["scenario_file"] = scenario_file
    if cyber_config_file:
        input_files["cyber_config_file"] = cyber_config_file
    if geo_data:
        input_files["geo_data"] = geo_data
    if asset_simulator_config_file:
        input_files["asset_simulator_config_file"] = asset_simulator_config_file
    # Not read by the orchestrator: already applied to the generated io files, kept to regenerate them
    if extra_io_file:
        input_files["extra_io_file"] = extra_io_file
    input_files["game_master_inputs_file"] = "game_master_inputs.json"
    input_files["game_master_outputs_file"] = "game_master_outputs.json"
    input_files["scada_outputs_file"] = f"scada_outputs{scada_suffix}.json"
    input_files["scada_inputs_file"] = f"scada_inputs{scada_suffix}.json"
    # The generated curves.xml is not listed: it is uploaded with the template, and collected from the jobs file
    input_files["other_files"] = list(other_files or [])
    input_files["other_dirs"] = []

    if mapping_file or scada_iidm_file:
        scada_backend = tomlkit.table()
        if mapping_file:
            scada_backend["mapping_file"] = mapping_file
        if scada_iidm_file:
            scada_backend["iidm_file"] = scada_iidm_file
        input_files["scada_backend"] = scada_backend

    if gm_iidm_file:
        gm_backend = tomlkit.table()
        gm_backend["iidm_file"] = gm_iidm_file
        input_files["gm_backend"] = gm_backend

    config["input_files"] = input_files

    hmi = tomlkit.table()
    hmi["location"] = "SCADA"
    config["hmi"] = hmi

    return tomlkit.dumps(config)


@template_router.post("/dynawo_dependencies")
def dynawo_dependencies(xml_file: UploadFile = File(...)):
    """
    Names one Dynawo XML file references, so a client can walk the graph without
    reimplementing the convention. A jobs file yields its solver/network/curves
    inputs and dyd files; a dyd file yields the par files its models need.
    """
    with TemporaryDirectory() as tmp_dir:
        path = write_file_path(Path(tmp_dir), xml_file)
        try:
            if path.suffix == ".dyd":
                names = dynawo_deps.dyd_references(path)
            else:
                names = dynawo_deps.jobs_references(path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not parse {xml_file.filename}: {exc}")
    return {"references": sorted(names)}


def declared_inputs(input_files) -> tuple[dict[str, str], set[str]]:
    """
    The files an [input_files] table declares: {file: role} and other_files.

    Subsections such as [input_files.scada_backend] share the layout; their keys
    become "scada_backend.iidm_file", matching TemplateFileRole.
    """
    by_name: dict[str, str] = {}
    others: set[str] = set()

    def collect(section, prefix: str):
        for key, value in section.items():
            if key in ("other_files", "other_dirs"):
                continue
            if isinstance(value, str):
                by_name.setdefault(str(value), prefix + key)
            elif isinstance(value, dict) and not prefix:
                collect(value, f"{key}.")
        others.update(str(f) for f in section.get("other_files", []))

    collect(input_files, "")
    return by_name, others


@template_router.post("/new_template_expert")
def create_template_expert(
    storage: StorageDep,
    session: SessionDep,
    template_name: str = Form(...),
    folder_id: int = Form(...),
    config_toml_file: UploadFile = File(...),
    files: list[UploadFile] = File(default_factory=list),
    relative_paths: list[str] = Form(default_factory=list),
    current_user=Depends(require_role("template_manager")),
):
    """
    Create a template from an already-valid context: the config.toml is taken as
    authoritative and its files are stored as given, with nothing generated.

    `files` carries the context, `relative_paths` the path each one should keep
    inside the template (parallel lists, so other_dirs survive intact).
    """
    user_name = current_user["preferred_username"]
    validate_template_name(template_name)
    if len(files) != len(relative_paths):
        raise HTTPException(
            status_code=400,
            detail=f"Got {len(files)} files for {len(relative_paths)} paths; they must match",
        )

    with TemporaryDirectory() as tmp_dir:
        working_dir = Path(tmp_dir).resolve()
        config_path = write_file_path(working_dir, config_toml_file)

        written: dict[str, Path] = {}
        for upload, relative in zip(files, relative_paths):
            # Client-supplied path: keep it inside the template root.
            target = (working_dir / relative).resolve()
            if not target.is_relative_to(working_dir.resolve()):
                raise HTTPException(status_code=400, detail=f"Unsafe path: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as handle:
                shutil.copyfileobj(upload.file, handle)
            written[relative] = target

        config = tomlkit.parse(config_path.read_text())
        declared = config.get("input_files", {})

        job_name = declared.get("job_file")
        if not job_name:
            raise HTTPException(status_code=400, detail="config.toml declares no job_file")
        job_path = written.get(job_name)
        if job_path is None:
            raise HTTPException(status_code=400, detail=f"job_file {job_name} was not uploaded")

        # The jobs file pulls in par and dyd files that need not appear in the
        # toml at all, so the context is only complete once those are present.
        missing = sorted(p.name for p in dynawo_deps.missing_dynawo_files(job_path))
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"{job_name} references files that were not uploaded: {', '.join(missing)}",
            )
        closure = dynawo_deps.collect_dynawo_files(job_path)

        # other_dirs are not checked: an empty one is legitimate.
        declared_by_name, declared_others = declared_inputs(declared)
        missing = sorted(
            name for name in {*declared_by_name, *declared_others} if name not in written
        )
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"config.toml declares files that were not uploaded: {', '.join(missing)}",
            )

        # A file's role is the config.toml key that names it, so it maps straight
        # back onto the toml; anything only the jobs graph knows about is marked
        # as such, and the rest is other_files/other_dirs material.
        stored: dict[Path, str] = {config_path: TemplateFileRole.config_toml.value}
        for relative, path in written.items():
            if relative in declared_by_name:
                stored[path] = declared_by_name[relative]
            elif path in closure:
                stored[path] = TemplateFileRole.jobs_dependency.value
            else:
                stored[path] = TemplateFileRole.other.value

        template = _store_template(
            session, storage,
            template_name=template_name, folder_id=folder_id, owner=user_name,
            working_dir=working_dir, files=stored,
        )
        return {"template_id": template.id, "uuid": template.uuid}

@template_router.patch("/rename/{template_id}", response_model=TemplateRenamedResponse)
def rename_template(session: SessionDep, template_id: int, template_new_name: str,
                    current_user=Depends(require_role("template_manager"))):
    user_name = current_user["preferred_username"]
    template = session.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template_node = session.exec(select(TreeNode).where(TreeNode.template_id == template_id)).first()
    if not template_node:
        raise HTTPException(status_code=404, detail="Template is not attached to the tree")
    if template_node.owner != user_name:
        raise HTTPException(status_code=403, detail="Template node is not owned by the user requesting the renaming action")
    validate_template_name(template_new_name)

    template.name = template_new_name
    template_node.name = template_new_name

    session.commit()
    session.refresh(template_node)
    session.refresh(template)

    return TemplateRenamedResponse(
        template_id=template.id,
        template_name=template.name
    )

@template_router.post("/share_template")
def share_template():
    raise HTTPException(status_code=404, detail="Not implemented")

### STORAGE ###

@app.get("/file/{key:path}")
def get_file_content(key: str, storage: StorageDep, session: SessionDep,
                     current_user: CurrentUserDep):
    """
    Get a file's raw bytes from storage, for a template the caller owns.

    Binaries come back as-is; the client decodes text itself.
    """
    require_key_owner(session, key, current_user)
    try:
        content = storage.download_file(key)
    except ClientError:
        raise HTTPException(status_code=404, detail="No such file")
    filename = Path(key).name
    return Response(
        content=content,
        media_type=guess_content_type(Path(filename)),
        # RFC 5987 form, so non-ASCII names survive.
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )

@app.get("/file-info/{key:path}")
def get_file_info(key: str, storage: StorageDep, session: SessionDep,
                  current_user: CurrentUserDep):
    require_key_owner(session, key, current_user)
    try:
        return {"size": storage.get_file_size(key)}
    except ClientError:
        raise HTTPException(status_code=404, detail="No such file")

# Attached here rather than per route, so a new endpoint is authenticated by
# default and opting out has to be written down.
app.include_router(template_router, dependencies=[Depends(principal_handler.get_current_user)])
app.include_router(session_router, dependencies=[Depends(principal_handler.get_current_user)])
app.include_router(tree_router, dependencies=[Depends(principal_handler.get_current_user)])
