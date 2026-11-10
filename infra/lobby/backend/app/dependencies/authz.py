"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_permission(
    db: AsyncSession, user_id: str, object_namespace: str, object_id: str, allowed_roles: list[str]
) -> bool:
    """Vérifie si l'utilisateur a un rôle (direct ou hérité via 'parent')."""
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
        SELECT 1 FROM access_graph
        WHERE subject_namespace = 'user'
          AND subject_id = CAST(:user_id AS UUID)
          AND relation = ANY(:roles)
    """)
    result = await db.execute(query, {
        "obj_ns": object_namespace, "obj_id": object_id, "user_id": user_id, "roles": allowed_roles
    })
    return result.scalar() is not None


async def grant_role(
    db: AsyncSession, user_id: str, object_namespace: str, object_id: str, role: str
):
    """Donne un rôle direct à un utilisateur sur un objet."""
    await db.execute(
        text("""
            INSERT INTO permissions_graph (object_namespace, object_id, relation, subject_namespace, subject_id)
            VALUES (:obj_ns, CAST(:obj_id AS UUID), :role, 'user', CAST(:user_id AS UUID))
            ON CONFLICT DO NOTHING
        """),
        {"obj_ns": object_namespace, "obj_id": object_id, "role": role, "user_id": user_id}
    )


async def set_parent(
    db: AsyncSession, child_ns: str, child_id: str, parent_ns: str, parent_id: str
):
    """Lie un objet enfant à son parent (pour l'héritage des permissions)."""
    await db.execute(
        text("""
            INSERT INTO permissions_graph (object_namespace, object_id, relation, subject_namespace, subject_id)
            VALUES (:c_ns, CAST(:c_id AS UUID), 'parent', :p_ns, CAST(:p_id AS UUID))
            ON CONFLICT DO NOTHING
        """),
        {"c_ns": child_ns, "c_id": child_id, "p_ns": parent_ns, "p_id": parent_id}
    )
