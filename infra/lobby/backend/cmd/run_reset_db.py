"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import asyncio

from sqlalchemy import text

from app.dependencies.get_db import engine


async def reset_database():
    print("⚠️ Removing tables...")

    drop_queries = """
    DROP TABLE IF EXISTS file_roles CASCADE;
    DROP TABLE IF EXISTS project_files CASCADE;
    DROP TABLE IF EXISTS template_versions CASCADE;
    DROP TABLE IF EXISTS templates CASCADE;
    DROP TABLE IF EXISTS project_roles CASCADE;
    DROP TABLE IF EXISTS group_roles CASCADE;
    DROP TABLE IF EXISTS projects CASCADE;
    DROP TABLE IF EXISTS groups CASCADE;
    """

    async with engine.begin() as conn:
        for query in drop_queries.split(";"):
            clean_query = query.strip()
            if clean_query:
                _ = await conn.execute(text(clean_query))

    print("✅ Database cleaned successfully!")


if __name__ == "__main__":
    asyncio.run(reset_database())
