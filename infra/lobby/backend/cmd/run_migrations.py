"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import asyncio
from pathlib import Path

from sqlalchemy import text

from app.dependencies.get_db import engine


async def run_migrations():
    migrations_dir = Path("migrations")

    if not migrations_dir.exists() or not migrations_dir.is_dir():
        print(f"❌ The directory '{migrations_dir}' does not exist.")
        return

    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        print(f"⚠️ No .sql files found in the '{migrations_dir}' directory.")
        return

    print("🚀 Starting migrations...")

    async with engine.begin() as conn:
        for sql_file in sql_files:
            print(f"  -> Applying {sql_file.name}...")

            sql = await asyncio.to_thread(sql_file.read_text, encoding="utf-8")

            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    _ = await conn.execute(text(statement))

    print("✅ All migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
