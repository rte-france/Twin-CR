"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from abc import ABC, abstractmethod


class Context_Client(ABC):
    """
    Archives the data stored in clickhouse in the given storage
    """

    @abstractmethod
    def archive(self, clickhouse_client, context_id, simulation_id):
        pass

    """
    Stores necessary files inside of the clickhouse database
    """
    @abstractmethod
    def init_context_and_scenario_files(self, clickhouse_client, context_id, scenario_id, simulation_id, config_path):
        pass

    @abstractmethod
    def init_dynawo_file(self, clickhouse_client, context_id, scenario_id, simulation_id, config_path):
        pass

    @abstractmethod
    def init_game_master(self, config_path, context_id, scenario_id, simulation_id):
        pass
