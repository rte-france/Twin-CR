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

activated = False
armed = False
t_armed = 999999

async def run():
    nc = NATS()
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    print(f"Connecting to NATS server: {nats_url}")
    await nc.connect(nats_url)

    async def activate(t):
        global activated
        msg = {
            "id": "TCB_lock",
            "value": 1,
            "time_sent": t,
            "time_received": t
        }

        # Tell the HMI that the automaton has activated
        await nc.publish("HMI.SCADA.Automata", json.dumps(msg).encode())
        # Also tell the game master (should be removed in the future, as the game master should also monitor the HMI inputs)
        await nc.publish("GameMaster.Automata", json.dumps(msg).encode())

        # Send signals to the tap changers to block them
        for tap_changer in [
            "NETWORK_Tr11-1011_TAP_CHANGER_locked_value",
            "NETWORK_Tr12-1012_TAP_CHANGER_locked_value",
            "NETWORK_Tr13-1013_TAP_CHANGER_locked_value",
            "NETWORK_Tr22-1022_TAP_CHANGER_locked_value",
            "NETWORK_Tr1-1041_TAP_CHANGER_locked_value",
            "NETWORK_Tr2-1042_TAP_CHANGER_locked_value",
            "NETWORK_Tr3-1043_TAP_CHANGER_locked_value",
            "NETWORK_Tr4-1044_TAP_CHANGER_locked_value",
            "NETWORK_Tr5-1045_TAP_CHANGER_locked_value",
            "NETWORK_Tr31-2031_TAP_CHANGER_locked_value",
            "NETWORK_Tr32-2032_TAP_CHANGER_locked_value",
            "NETWORK_Tr41-4041_TAP_CHANGER_locked_value",
            "NETWORK_Tr42-4042_TAP_CHANGER_locked_value",
            "NETWORK_Tr43-4043_TAP_CHANGER_locked_value",
            "NETWORK_Tr46-4046_TAP_CHANGER_locked_value",
            "NETWORK_Tr47-4047_TAP_CHANGER_locked_value",
            "NETWORK_Tr51-4051_TAP_CHANGER_locked_value",
            "NETWORK_Tr61-4061_TAP_CHANGER_locked_value",
            "NETWORK_Tr62-4062_TAP_CHANGER_locked_value",
            "NETWORK_Tr63-4063_TAP_CHANGER_locked_value",
            "NETWORK_Tr71-4071_TAP_CHANGER_locked_value",
            "NETWORK_Tr72-4072_TAP_CHANGER_locked_value"
        ]:
            msg = {"id": tap_changer, "value": 1}
            await nc.publish("HMIControl.tcp_blocker", json.dumps(msg).encode())
        activated = True

    async def voltage_measurement(msg: nats.aio.msg.Msg):
        global activated
        global armed
        global t_armed

        if activated:
            return
        message = json.loads(msg.data.decode())
        if message["id"] == "NETWORK_1042_131_U_value":
            if message["value"] < 120:
                t = message["time_received"]

                if not armed:
                    print("TCB armed due to low voltage at time", t)
                    armed = True
                    t_armed = t
                else:
                    if t >= t_armed + 1:
                        print("TCB activated due to low voltage at time", t)
                        await activate(t)
            else:
                if armed:
                    t = message["time_received"]
                    print("TCB disarmed at time", t)
                    armed = False
                    t_armed = 999999

    async def external_activation(msg: nats.aio.msg.Msg):
        global activated
        if activated:
            return
        message = json.loads(msg.data.decode())
        id = message.get("id", "")
        value = message.get("value", 0)
        if id == "TCB_lock":
            if value > 0:
                print("TCB activated from external signal")
                await activate(t = -1)

    await nc.subscribe("HMI.SCADA.S_1042", cb=voltage_measurement)
    await nc.subscribe("HMIControl.>", cb=external_activation)
    await nc.subscribe("GameMasterControl.>", cb=external_activation)

    while not activated:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Shutting down TCP blocker...")
