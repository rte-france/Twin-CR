"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

TREE_COLUMNS = (
    "pf.id, pf.name, pf.s3_object_key, pf.is_directory, pf.parent_id, pf.project_id"
)


async def check_project_write_access(
    db_session: AsyncSession, project_id: str, user_id: str
) -> bool:
    query = text("""
        WITH RECURSIVE access_graph AS (
            SELECT object_namespace, object_id, relation, subject_namespace, subject_id
            FROM permissions_graph
            WHERE object_namespace = 'project' AND object_id = CAST(:project_id AS UUID)

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
          AND relation IN ('owner', 'admin', 'editor')
    """)
    result = await db_session.execute(
        query, {"project_id": project_id, "user_id": user_id}
    )
    return result.scalar() is not None


async def check_project_read_access(
    db_session: AsyncSession, project_id: str, user_id: str
) -> bool:
    query = text("""
        WITH RECURSIVE access_graph AS (
            SELECT object_namespace, object_id, relation, subject_namespace, subject_id
            FROM permissions_graph
            WHERE object_namespace = 'project' AND object_id = CAST(:project_id AS UUID)

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
    """)
    result = await db_session.execute(
        query, {"project_id": project_id, "user_id": user_id}
    )
    return result.scalar() is not None


async def fetch_all_nodes_for_project(
    db_session: AsyncSession, project_id: str
) -> Sequence[RowMapping]:
    query = text(f"""
        SELECT {TREE_COLUMNS}
        FROM project_files pf
        WHERE pf.project_id = CAST(:project_id AS UUID)
    """)
    result = await db_session.execute(query, {"project_id": project_id})
    return result.mappings().all()


async def fetch_all_nodes(
    db_session: AsyncSession, user_id: str
) -> Sequence[RowMapping]:
    query = text(f"""
        WITH RECURSIVE accessible_entities AS (
            SELECT object_namespace, object_id
            FROM permissions_graph
            WHERE subject_namespace = 'user' AND subject_id = CAST(:user_id AS UUID)

            UNION

            SELECT pg.object_namespace, pg.object_id
            FROM permissions_graph pg
            INNER JOIN accessible_entities ae
                ON pg.subject_namespace = ae.object_namespace
               AND pg.subject_id = ae.object_id
            WHERE pg.relation = 'parent'
        )
        SELECT {TREE_COLUMNS}
        FROM project_files pf
        INNER JOIN accessible_entities ae
            ON pf.id = ae.object_id AND ae.object_namespace = 'file'
    """)
    result = await db_session.execute(query, {"user_id": user_id})
    return result.mappings().all()


async def list_directory_rows(
    db_session: AsyncSession, user_id: str
) -> Sequence[RowMapping]:
    query = text("""
        WITH RECURSIVE accessible_entities AS (
            SELECT object_namespace, object_id
            FROM permissions_graph
            WHERE subject_namespace = 'user' AND subject_id = CAST(:user_id AS UUID)

            UNION

            SELECT pg.object_namespace, pg.object_id
            FROM permissions_graph pg
            INNER JOIN accessible_entities ae
                ON pg.subject_namespace = ae.object_namespace
               AND pg.subject_id = ae.object_id
            WHERE pg.relation = 'parent'
        )
        SELECT pf.id, pf.name, pf.parent_id
        FROM project_files pf
        INNER JOIN accessible_entities ae
            ON pf.id = ae.object_id AND ae.object_namespace = 'file'
        WHERE pf.is_directory = TRUE
    """)
    result = await db_session.execute(query, {"user_id": user_id})
    return result.mappings().all()


async def fetch_file_or_404(
    db_session: AsyncSession,
    item_id: str,
    user_id: str,
    *,
    detail: str = "File not found",
) -> RowMapping:
    query = text("""
        WITH RECURSIVE access_graph AS (
            SELECT object_namespace, object_id, relation, subject_namespace, subject_id
            FROM permissions_graph
            WHERE object_namespace = 'file' AND object_id = CAST(:id AS UUID)

            UNION

            SELECT pg.object_namespace, pg.object_id, pg.relation, pg.subject_namespace, pg.subject_id
            FROM permissions_graph pg
            INNER JOIN access_graph ag
                ON pg.object_namespace = ag.subject_namespace
                AND pg.object_id = ag.subject_id
            WHERE ag.relation = 'parent'
        )
        SELECT pf.s3_object_key, pf.is_directory
        FROM project_files pf
        WHERE pf.id = CAST(:id AS UUID)
          AND EXISTS (
              SELECT 1
              FROM access_graph
              WHERE subject_namespace = 'user' AND subject_id = CAST(:user_id AS UUID)
          )
    """)
    result = await db_session.execute(query, {"id": item_id, "user_id": user_id})
    row = result.mappings().first()
    if not row or row["is_directory"]:
        raise HTTPException(status_code=404, detail=detail)
    return row


async def check_write_access(
    db_session: AsyncSession, item_id: str, user_id: str
) -> bool:
    query = text("""
        WITH RECURSIVE access_graph AS (
            SELECT object_namespace, object_id, relation, subject_namespace, subject_id
            FROM permissions_graph
            WHERE object_namespace = 'file' AND object_id = CAST(:id AS UUID)

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
          AND relation IN ('owner', 'admin', 'editor')
    """)
    result = await db_session.execute(query, {"id": item_id, "user_id": user_id})
    return result.scalar() is not None


async def upsert_file(
    db_session: AsyncSession,
    *,
    file_id: str,
    project_id: str,
    name: str,
    s3_key: str,
    parent_id: str | None,
) -> None:
    # 1. Insertion de la donnée
    query = text("""
        INSERT INTO project_files (id, project_id, name, s3_object_key, is_directory, parent_id)
        VALUES (CAST(:id AS UUID), CAST(:project_id AS UUID), :name, :s3_key, FALSE, CAST(:parent_id AS UUID))
        ON CONFLICT (id) DO UPDATE
        SET name = :name, s3_object_key = :s3_key, parent_id = CAST(:parent_id AS UUID)
    """)
    await db_session.execute(
        query,
        {
            "id": file_id,
            "project_id": project_id,
            "name": name,
            "s3_key": s3_key,
            "parent_id": parent_id,
        },
    )

    # 2. NOUVEAU : Insertion de la permission dans le graphe
    parent_ns = "file" if parent_id else "project"
    parent_graph_id = parent_id if parent_id else project_id

    await db_session.execute(
        text("""
            INSERT INTO permissions_graph (object_namespace, object_id, relation, subject_namespace, subject_id)
            VALUES ('file', CAST(:c_id AS UUID), 'parent', :p_ns, CAST(:p_id AS UUID))
            ON CONFLICT DO NOTHING
        """),
        {"c_id": file_id, "p_ns": parent_ns, "p_id": parent_graph_id},
    )


async def insert_directory(
    db_session: AsyncSession,
    *,
    dir_id: str,
    project_id: str,
    name: str,
    parent_id: str | None,
) -> None:
    # 1. Insertion de la donnée
    query = text("""
        INSERT INTO project_files (id, project_id, name, s3_object_key, is_directory, parent_id)
        VALUES (CAST(:id AS UUID), CAST(:project_id AS UUID), :name, NULL, TRUE, CAST(:parent_id AS UUID))
    """)
    await db_session.execute(
        query,
        {"id": dir_id, "project_id": project_id, "name": name, "parent_id": parent_id},
    )

    # 2. NOUVEAU : Insertion de la permission dans le graphe
    parent_ns = "file" if parent_id else "project"
    parent_graph_id = parent_id if parent_id else project_id

    await db_session.execute(
        text("""
            INSERT INTO permissions_graph (object_namespace, object_id, relation, subject_namespace, subject_id)
            VALUES ('file', CAST(:c_id AS UUID), 'parent', :p_ns, CAST(:p_id AS UUID))
            ON CONFLICT DO NOTHING
        """),
        {"c_id": dir_id, "p_ns": parent_ns, "p_id": parent_graph_id},
    )


async def update_item_fields(
    db_session: AsyncSession,
    *,
    item_id: str,
    update_dict: dict,
) -> bool:
    if not update_dict:
        return True

    set_clauses = []
    params = {"id": item_id}

    if "name" in update_dict:
        set_clauses.append("name = :name")
        params["name"] = update_dict["name"]

    if "parent_id" in update_dict:
        set_clauses.append("parent_id = CAST(:parent_id AS UUID)")
        params["parent_id"] = update_dict["parent_id"]

    if not set_clauses:
        return True

    query = text(
        f"UPDATE project_files SET {', '.join(set_clauses)} WHERE id = CAST(:id AS UUID) RETURNING id"
    )
    result = await db_session.execute(query, params)
    return result.first() is not None


async def fetch_artifacts(
    db_session: AsyncSession, artifact_ids: list[str], user_id: str
) -> Sequence[RowMapping]:
    if not artifact_ids:
        return []

    query = text("""
        WITH RECURSIVE accessible_entities AS (
            SELECT object_namespace, object_id
            FROM permissions_graph
            WHERE subject_namespace = 'user' AND subject_id = CAST(:user_id AS UUID)

            UNION

            SELECT pg.object_namespace, pg.object_id
            FROM permissions_graph pg
            INNER JOIN accessible_entities ae
                ON pg.subject_namespace = ae.object_namespace
               AND pg.subject_id = ae.object_id
            WHERE pg.relation = 'parent'
        )
        SELECT pf.id, pf.name, pf.s3_object_key
        FROM project_files pf
        INNER JOIN accessible_entities ae
            ON pf.id = ae.object_id AND ae.object_namespace = 'file'
        WHERE pf.id = ANY(CAST(:ids AS UUID[])) AND pf.is_directory = False
    """)
    result = await db_session.execute(query, {"ids": artifact_ids, "user_id": user_id})
    return result.mappings().all()


async def fetch_item_and_descendants(
    db_session: AsyncSession, item_id: str, user_id: str
) -> Sequence[RowMapping]:
    query = text("""
        WITH RECURSIVE access_graph AS (
            SELECT object_namespace, object_id, relation, subject_namespace, subject_id
            FROM permissions_graph
            WHERE object_namespace = 'file' AND object_id = CAST(:item_id AS UUID)

            UNION

            SELECT pg.object_namespace, pg.object_id, pg.relation, pg.subject_namespace, pg.subject_id
            FROM permissions_graph pg
            INNER JOIN access_graph ag
                ON pg.object_namespace = ag.subject_namespace
                AND pg.object_id = ag.subject_id
            WHERE ag.relation = 'parent'
        ),
        user_access AS (
            SELECT 1
            FROM access_graph
            WHERE subject_namespace = 'user'
              AND subject_id = CAST(:user_id AS UUID)
              AND relation IN ('owner', 'admin', 'editor')
        ),
        item_tree AS (
            SELECT pf.id, pf.s3_object_key
            FROM project_files pf
            CROSS JOIN user_access
            WHERE pf.id = CAST(:item_id AS UUID)

            UNION ALL

            SELECT pf.id, pf.s3_object_key
            FROM project_files pf
            INNER JOIN item_tree it ON it.id = pf.parent_id
        )
        SELECT id, s3_object_key FROM item_tree;
    """)
    result = await db_session.execute(query, {"item_id": item_id, "user_id": user_id})
    return result.mappings().all()


async def delete_items(db_session: AsyncSession, item_ids: list[str]) -> None:
    if not item_ids:
        return
    await db_session.execute(
        text("DELETE FROM project_files WHERE id = ANY(CAST(:ids AS UUID[]))"),
        {"ids": item_ids},
    )
