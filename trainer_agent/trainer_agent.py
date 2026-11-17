"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import asyncio
import json
import os
import pypowsybl as ps
import requests
import sys
#sys.path.insert(0, "../Orchestrator/hmi/game_master_starter")

from nats.aio.client import Client as NATS

from add_governor_kgover import read_governor_kgover
from contingency_finder import ContingencyFinder, INCREASE_LOAD_PERCENT


class TrainerAgent:

    def __init__(self, voltage_thresh=300, cyber_mode="NONE", max_difficulty=None, include_pairs=False):
        DSL_SERVER_HOST = "localhost"#os.getenv("DSL_SERVER_HOST", "localhost")
        DSL_SERVER_PORT = int(os.getenv("DSL_SERVER_PORT", "8000"))
        self.GAME_MASTER_URL = f"http://{DSL_SERVER_HOST}:{DSL_SERVER_PORT}"
        self.nats_connection = NATS()
        self.nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        self.dynawo_to_iidm_mapping = {}
        self.finder = ContingencyFinder(mode="opf")
        self.voltage_thresh = voltage_thresh
        self.cyber_mode = cyber_mode     # Can be NONE, RTU or AGGREGATOR
        cyber_file = os.getenv("CYBER_FILE", None)
        if cyber_file is not None:
            with open(cyber_file) as f:
                cyber_links = json.load(f)["links"]
            self.rtu_links = {}
            self.aggregator_links = {}

            for link in cyber_links:
                if link["to"][:9] == "RTU_ICCP_": 
                        self.rtu_links[link["to"][9:]] = link
                elif link["totype"] == "RTU":
                    self.aggregator_links[link["to"]] = link["from"]
        elif cyber_mode is not "NONE":
            raise Exception("Cyber mode activated but no cyber communication file provided !")

        self.max_difficulty = max_difficulty
        self.include_pairs = include_pairs

    def loose_cyber_substations(self, substations):
        command = "change network characteristics"
        for substation in substations:
            if substation in self.rtu_links:
                rtu_link = self.rtu_links[substation]
            else:
                rtu_link = next((s for s in self.rtu_links.keys() if s[:len(substation)] == substation), None)
            
            if rtu_link is not None:
                if self.cyber_mode == "RTU":
                    # Link command is not working for now
                    # command += f" link from \"{rtu_link["from"]}\" to \"{rtu_link["to"]}\","
                    command += f" node \"{rtu_link["to"]}\","
                elif self.cyber_mode == "AGGREGATOR":
                    aggregator = rtu_link["from"]
                    # command += f" link from \"{self.aggregator_links[aggregator]}\" to \"{aggregator}\","
                    command += f" node \"{aggregator}\","
            else:
                print("Warning: no cyber link found for substation:", substation)


        command += " drop fixed true;"
        return command

    def update_iidm(self):
        response = requests.get("http://localhost:8083/iidm")
        net = ps.network.load_from_string("temp.iidm", response.text)
        net.save("temp.iidm")
        par_file = os.getenv("PAR_FILE", None)
        if par_file is not None:
            governor_kgover = read_governor_kgover(net.get_generators().index, par_file)
        else:
            governor_kgover = None
        self.finder.update_network(net, governor_kgover)
    
    def send_dsl_command(self, dsl_command):
        return requests.post(f"{self.GAME_MASTER_URL}/trainer/dsl_command", json={"dsl_command": dsl_command, "source": "Trainer Agent"})

    async def apply_worst_contingency(self):
        self.update_iidm()
        contingencies = self.finder.find_contingency(include_failing=False, voltage_thresh=self.voltage_thresh, mode="opf", include_pairs=self.include_pairs)

        if self.max_difficulty is not None:
            contingencies = contingencies[contingencies["difficulty_10"] <= self.max_difficulty]
        contingency_name = contingencies.iloc[0].name
        print(contingency_name, contingencies.iloc[0].difficulty_10)
        dsl_command = ""
        if "gen" in contingency_name:
            for gen in self.finder.get_generators(contingency_name):
                dsl_command += f"at [now , now + 10 seconds ] with law \"linear\", increase generator \"{gen}\" input \"P\" by {INCREASE_LOAD_PERCENT}%;\n"

        elif "load" in contingency_name:
            for load in self.finder.get_loads(contingency_name):
                if INCREASE_LOAD_PERCENT > 0:
                    dsl_command += f"increase load \"{load}\" input \"P\" by {INCREASE_LOAD_PERCENT}%;\n"
                else:
                    dsl_command += f"at [now , now + 10 seconds ] with law \"linear\", decrease load \"{load}\" input \"P\" by {-INCREASE_LOAD_PERCENT}%;\n"
        elif "_+_" in contingency_name:
            idx = contingency_name.find("_+_")
            dsl_command = f"open {self.finder.get_contingency_type(contingency_name[:idx])} \"{contingency_name[:idx]}\";"
            dsl_command = f"open {self.finder.get_contingency_type(contingency_name[idx+3:])} \"{contingency_name[idx+3:]}\";"
        else:
            dsl_command = f"open {contingencies.iloc[0]['component_type']} \"{contingencies.iloc[0].name}\";"

        print(dsl_command)
        response = self.send_dsl_command(dsl_command)

        self.finder.apply_contingency(contingency_name)
        if self.cyber_mode != "NONE":
            substations, _ = self.finder.get_overloaded_branch_substations()
            dsl_command = self.loose_cyber_substations(substations)
            print(dsl_command)
            response = self.send_dsl_command(dsl_command)
            print(response)
    
    async def run(self):
        await self.nats_connection.connect(self.nats_url)

        while True:
            await self.apply_worst_contingency()
            await asyncio.sleep(30)
            print("=====================================")
            print("Running optimal operator redispatch.")
            print("=====================================")
            # self.update_iidm()
            response = requests.get("http://localhost:8083/iidm")
            net = ps.network.load_from_string("temp.iidm", response.text)
            net.save("temp.iidm")
            redispatch = self.finder.get_solution()
            dsl_command = ""
            for i, row in redispatch.iterrows():
                dsl_command += f"set generator \"{row['name']}\" input \"P\" to {row['p_mw']:.2f};\n"

            print(dsl_command)
            response = self.send_dsl_command(dsl_command)
            await asyncio.sleep(5)


if __name__ == "__main__":
    trainer = TrainerAgent(voltage_thresh=300, cyber_mode="NONE", max_difficulty=None)
    asyncio.run(trainer.run())