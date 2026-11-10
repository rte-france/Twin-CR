"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import templates_repo as repo
from app.dependencies.aliases import S3ClientDep, SettingsDep
from app.dependencies.auth import get_current_user
from app.dependencies.get_db import get_db
from app.schemas import CurrentUser

router = APIRouter(prefix="/api/v1", tags=["Projects"])


class GroupCreate(BaseModel):
    name: str
    parent_id: str | None = None


class ProjectCreate(BaseModel):
    name: str
    group_id: str


class ProjectUpdate(BaseModel):
    name: str | None = None
    group_id: str | None = None


class ProjectDuplicate(BaseModel):
    target_group_id: str


async def check_permission(
    db: AsyncSession,
    user_id: str,
    object_namespace: str,
    object_id: str,
    allowed_roles: list[str],
) -> bool:
    query = text("""
        WITH RECURSIVE access_graph AS (
            SELECT object_namespace, object_id, relation, subject_namespace, subject_id
            FROM permissions_graph
            WHERE object_namespace = :obj_ns AND object_id = CAST(:obj_id AS UUID)

            UNION

            SELECT pg.object_namespace, pg.object_id, pg.relation, pg.subject_namespace, pg.subject_id
            FROM permissions_graph pg
            INNER JOIN access_graph ag
                ON pg.object_namespace = ag.subject_namespace
                AND pg.object_id = ag.subject_id
            WHERE ag.relation = 'parent'
        )
        SELECT 1
        FROM access_graph
        WHERE subject_namespace = 'user'
          AND subject_id = CAST(:user_id AS UUID)
          AND relation = ANY(:roles)
    """)
    result = await db.execute(
        query,
        {
            "obj_ns": object_namespace,
            "obj_id": object_id,
            "user_id": user_id,
            "roles": allowed_roles,
        },
    )
    return result.scalar() is not None


async def grant_role(
    db: AsyncSession, user_id: str, object_namespace: str, object_id: str, role: str
):
    await db.execute(
        text("""
            INSERT INTO permissions_graph (object_namespace, object_id, relation, subject_namespace, subject_id)
            VALUES (:obj_ns, CAST(:obj_id AS UUID), :role, 'user', CAST(:user_id AS UUID))
            ON CONFLICT DO NOTHING
        """),
        {
            "obj_ns": object_namespace,
            "obj_id": object_id,
            "role": role,
            "user_id": user_id,
        },
    )


async def set_parent(
    db: AsyncSession, child_ns: str, child_id: str, parent_ns: str, parent_id: str
):
    await db.execute(
        text("""
            INSERT INTO permissions_graph (object_namespace, object_id, relation, subject_namespace, subject_id)
            VALUES (:c_ns, CAST(:c_id AS UUID), 'parent', :p_ns, CAST(:p_id AS UUID))
            ON CONFLICT DO NOTHING
        """),
        {"c_ns": child_ns, "c_id": child_id, "p_ns": parent_ns, "p_id": parent_id},
    )


async def remove_parent(db: AsyncSession, child_ns: str, child_id: str):
    await db.execute(
        text("""
            DELETE FROM permissions_graph
            WHERE object_namespace = :c_ns
              AND object_id = CAST(:c_id AS UUID)
              AND relation = 'parent'
        """),
        {"c_ns": child_ns, "c_id": child_id},
    )


@router.get("/groups")
async def list_groups(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    query = text("""
        WITH RECURSIVE
        -- 1. Les dossiers auxquels on a accès directement
        direct_access AS (
            SELECT object_id
            FROM permissions_graph
            WHERE subject_namespace = 'user'
              AND subject_id = CAST(:user_id AS UUID)
              AND object_namespace = 'group'
        ),
        -- 2. On DESCEND (pour voir le contenu des dossiers partagés)
        accessible_down AS (
            SELECT g.id, g.name, g.parent_id
            FROM groups g
            INNER JOIN direct_access da ON g.id = da.object_id

            UNION

            SELECT g.id, g.name, g.parent_id
            FROM groups g
            INNER JOIN accessible_down ad ON g.parent_id = ad.id
        ),
        -- 3. On REMONTE (pour récupérer l'arborescence visuelle parente)
        accessible_up AS (
            SELECT g.id, g.name, g.parent_id
            FROM groups g
            INNER JOIN direct_access da ON g.id = da.object_id

            UNION

            SELECT g.id, g.name, g.parent_id
            FROM groups g
            INNER JOIN accessible_up au ON g.id = au.parent_id
        )
        -- 4. On assemble tout pour le frontend !
        SELECT id, name, parent_id FROM accessible_down
        UNION
        SELECT id, name, parent_id FROM accessible_up
    """)
    result = await db.execute(query, {"user_id": user.id})
    return [dict(row) for row in result.mappings()]


@router.post("/groups")
async def create_group(
    group: GroupCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    if group.parent_id:
        is_authorized = await check_permission(
            db, user.id, "group", group.parent_id, ["owner", "admin", "editor"]
        )
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Forbidden")

    new_id = str(uuid.uuid4())

    await db.execute(
        text("""
            INSERT INTO groups (id, name, parent_id)
            VALUES (CAST(:id AS UUID), :name, CAST(:parent_id AS UUID))
        """),
        {"id": new_id, "name": group.name, "parent_id": group.parent_id},
    )

    await grant_role(db, user.id, "group", new_id, "owner")

    if group.parent_id:
        await set_parent(db, "group", new_id, "group", group.parent_id)

    await db.commit()
    return {"id": new_id, "name": group.name, "parent_id": group.parent_id}


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    is_authorized = await check_permission(
        db, user.id, "group", group_id, ["owner", "admin"]
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Forbidden")

    await db.execute(
        text("DELETE FROM groups WHERE id = CAST(:id AS UUID)"), {"id": group_id}
    )

    await db.execute(
        text("""
            DELETE FROM permissions_graph
            WHERE object_id = CAST(:id AS UUID)
               OR subject_id = CAST(:id AS UUID)
        """),
        {"id": group_id},
    )

    await db.commit()
    return {"status": "deleted"}


@router.get("/projects")
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    group_id: str | None = None,
):
    if group_id:
        is_authorized = await check_permission(
            db, user.id, "group", group_id, ["owner", "admin", "editor", "viewer"]
        )
        if not is_authorized:
            # AU LIEU DE RAISE HTTP 403, on renvoie simplement une liste vide !
            # Ainsi, Louis verra que le dossier r&d est vide pour lui (hormis son sous-dossier).
            return []

        query = text(
            "SELECT id, name, group_id FROM projects WHERE group_id = CAST(:group_id AS UUID)"
        )
        params = {"group_id": group_id}

    else:
        # Requête pour TOUS les projets auxquels j'ai accès (via groupe ou direct)
        query = text("""
            WITH RECURSIVE
            -- 1. Les groupes auxquels j'ai accès direct
            direct_group_access AS (
                SELECT object_id
                FROM permissions_graph
                WHERE subject_namespace = 'user'
                  AND subject_id = CAST(:user_id AS UUID)
                  AND object_namespace = 'group'
            ),
            -- 2. Tous les sous-groupes
            accessible_groups AS (
                SELECT g.id FROM groups g INNER JOIN direct_group_access dga ON g.id = dga.object_id
                UNION
                SELECT g.id FROM groups g INNER JOIN accessible_groups ag ON g.parent_id = ag.id
            ),
            -- 3. Les projets auxquels j'ai accès direct
            direct_project_access AS (
                SELECT object_id
                FROM permissions_graph
                WHERE subject_namespace = 'user'
                  AND subject_id = CAST(:user_id AS UUID)
                  AND object_namespace = 'project'
            )
            -- 4. Résultat final : Projets dans mes groupes + Mes projets directs
            SELECT p.id, p.name, p.group_id
            FROM projects p
            WHERE p.group_id IN (SELECT id FROM accessible_groups)
               OR p.id IN (SELECT object_id FROM direct_project_access)
        """)
        params = {"user_id": user.id}

    result = await db.execute(query, params)
    return [dict(row) for row in result.mappings()]


@router.post("/projects")
async def create_project(
    project: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    is_authorized = await check_permission(
        db, user.id, "group", project.group_id, ["owner", "admin", "editor"]
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Forbidden")

    new_id = str(uuid.uuid4())

    await db.execute(
        text("""
            INSERT INTO projects (id, name, group_id)
            VALUES (CAST(:id AS UUID), :name, CAST(:group_id AS UUID))
        """),
        {"id": new_id, "name": project.name, "group_id": project.group_id},
    )

    await set_parent(db, "project", new_id, "group", project.group_id)
    await db.commit()

    return {"id": new_id, "name": project.name, "group_id": project.group_id}


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    update: ProjectUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    is_authorized = await check_permission(
        db, user.id, "project", project_id, ["owner", "admin", "editor"]
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Forbidden")

    sets = []
    params = {"id": project_id}

    if update.name is not None:
        sets.append("name = :name")
        params["name"] = update.name

    if update.group_id is not None:
        is_target_authorized = await check_permission(
            db, user.id, "group", update.group_id, ["owner", "admin", "editor"]
        )
        if not is_target_authorized:
            raise HTTPException(status_code=403, detail="Forbidden")

        sets.append("group_id = CAST(:group_id AS UUID)")
        params["group_id"] = update.group_id

    if sets:
        await db.execute(
            text(f"UPDATE projects SET {', '.join(sets)} WHERE id = CAST(:id AS UUID)"),
            params,
        )

        if update.group_id is not None:
            await remove_parent(db, "project", project_id)
            await set_parent(db, "project", project_id, "group", update.group_id)

        await db.commit()

    return {"status": "updated"}


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    is_authorized = await check_permission(
        db, user.id, "project", project_id, ["owner", "admin"]
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Forbidden")

    await db.execute(
        text("DELETE FROM projects WHERE id = CAST(:id AS UUID)"), {"id": project_id}
    )

    await db.execute(
        text("""
            DELETE FROM permissions_graph
            WHERE object_id = CAST(:id AS UUID)
               OR subject_id = CAST(:id AS UUID)
        """),
        {"id": project_id},
    )

    await db.commit()
    return {"status": "deleted"}


@router.post("/projects/{project_id}/duplicate")
async def duplicate_project(
    project_id: str,
    payload: ProjectDuplicate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: SettingsDep,
    s3_client: S3ClientDep,
):
    is_authorized_target = await check_permission(
        db, user.id, "group", payload.target_group_id, ["owner", "admin", "editor"]
    )
    if not is_authorized_target:
        raise HTTPException(status_code=403, detail="Forbidden")

    is_authorized_source = await check_permission(
        db, user.id, "project", project_id, ["owner", "admin", "editor", "viewer"]
    )
    if not is_authorized_source:
        raise HTTPException(status_code=403, detail="Forbidden")

    source_proj = await db.execute(
        text("SELECT name FROM projects WHERE id = CAST(:p_id AS UUID)"),
        {"p_id": project_id},
    )
    proj_row = source_proj.mappings().first()

    if not proj_row:
        raise HTTPException(status_code=404, detail="Project not found")

    new_project_name = f"{proj_row['name']} (Copy)"
    new_project_id = str(uuid.uuid4())

    try:
        await db.execute(
            text("""
                INSERT INTO projects (id, name, group_id)
                VALUES (CAST(:id AS UUID), :name, CAST(:group_id AS UUID))
            """),
            {
                "id": new_project_id,
                "name": new_project_name,
                "group_id": payload.target_group_id,
            },
        )

        await set_parent(
            db, "project", new_project_id, "group", payload.target_group_id
        )

        rows = await repo.fetch_all_nodes_for_project(db, project_id)
        nodes = [dict(r) for r in rows]

        id_mapping = {}
        pending = nodes[:]

        while pending:
            progress = False
            for node in pending[:]:
                old_parent_id = node.get("parent_id")

                if old_parent_id is None or str(old_parent_id) in id_mapping:
                    old_id = str(node["id"])
                    new_id = str(uuid.uuid4())
                    id_mapping[old_id] = new_id

                    new_parent_id = (
                        id_mapping.get(str(old_parent_id)) if old_parent_id else None
                    )

                    if node.get("is_directory"):
                        await repo.insert_directory(
                            db_session=db,
                            dir_id=new_id,
                            project_id=new_project_id,
                            name=node["name"],
                            parent_id=new_parent_id,
                        )
                    else:
                        old_s3_key = node.get("s3_object_key")
                        new_s3_key = f"projects/{new_project_id}/{new_id}"

                        if old_s3_key:
                            await s3_client.copy_object(
                                CopySource={
                                    "Bucket": settings.s3_bucket_name,
                                    "Key": old_s3_key,
                                },
                                Bucket=settings.s3_bucket_name,
                                Key=new_s3_key,
                            )

                        await repo.upsert_file(
                            db_session=db,
                            file_id=new_id,
                            project_id=new_project_id,
                            name=node["name"],
                            s3_key=new_s3_key,
                            parent_id=new_parent_id,
                        )

                    parent_namespace = "file" if new_parent_id else "project"
                    parent_id_for_graph = (
                        new_parent_id if new_parent_id else new_project_id
                    )

                    await set_parent(
                        db, "file", new_id, parent_namespace, parent_id_for_graph
                    )

                    pending.remove(node)
                    progress = True

            if not progress:
                break

        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "id": new_project_id,
        "name": new_project_name,
        "group_id": payload.target_group_id,
    }


class ShareRequest(BaseModel):
    target_user_id: str
    role: str


@router.post("/groups/{group_id}/share")
async def share_group(
    group_id: str,
    payload: ShareRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    is_authorized = await check_permission(
        db, user.id, "group", group_id, ["owner", "admin"]
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Forbidden")

    valid_roles = ["owner", "admin", "editor", "viewer"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    await grant_role(db, payload.target_user_id, "group", group_id, payload.role)

    await db.commit()

    return {
        "status": "success",
        "group_id": group_id,
        "target_user_id": payload.target_user_id,
        "role": payload.role,
    }
