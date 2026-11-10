"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.dependencies.get_config import get_settings
from app.temporal.activities import deploy_nomad_job, destroy_nomad_job
from app.temporal.workflows import LobbySessionWorkflow


async def main():
    settings = get_settings()

    print(f"Connecting to Temporal server at {settings.temporal_address}...")

    client = await Client.connect(
        settings.temporal_address, namespace=settings.temporal_namespace
    )

    worker = Worker(
        client,
        task_queue="twineu-task-queue",
        workflows=[LobbySessionWorkflow],
        activities=[deploy_nomad_job, destroy_nomad_job],
    )

    print("Temporal Worker started. Waiting for tasks...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
