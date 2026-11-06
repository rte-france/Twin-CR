"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
import asyncio
import os
from nats.aio.client import Client as NATS
import nats.aio.msg

activated_shedding = False
activated_disconnection = False

async def run():
    nc = NATS()
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    print(f"Connecting to NATS server: {nats_url}")
    await nc.connect(nats_url)

    async def shed_load(t):
        global activated_shedding
        msg = {
            "command": "command_injection",
            "t_start": t,
            "command_id": "LoadReduction",
            "value": -0.35,  # 35MW
            "source": "Load_2",
            "destination": "Load_2"
        }
        await nc.publish("HMIControl.load_shedding_automaton", json.dumps(msg).encode())
        activated_shedding = True

    async def disconnect(t):
        global activated_disconnection
        msg = {
            "command": "command_injection",
            "t_start": t,
            "command_id": "L2_state",
            "value": 1,
            "source": "Load_2",
            "destination": "Load_2"
        }
        await nc.publish("HMIControl.load_shedding_automaton", json.dumps(msg).encode())
        activated_disconnection = True

    async def frequency_measurement(msg: nats.aio.msg.Msg):
        global activated_disconnection, activated_shedding
        if activated_disconnection:
            return
        message = json.loads(msg.data.decode())
        print("Frequency", float(message["value"]) * 50)
        if message["id"] == "OMEGA":
            if message["value"] < (48 / 50) or message["value"] > (52/50):
                t = message["time_received"]
                print(f"At time {t}, disconnection due to unacceptable frequency {message['value']}")
                await disconnect(t)

            if message["value"] < (49.5 / 50) and not activated_shedding:
                t = message["time_received"]
                print(f"At time {t}, load reduction due to low frequency {message['value']}")
                await shed_load(t)
                activated_shedding = True

    await nc.subscribe("HMI.Load_2.substation_2", cb=frequency_measurement)

    while not activated_disconnection:
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Load reduction automaton...")
