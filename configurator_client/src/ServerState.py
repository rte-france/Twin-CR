"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from typing import Optional

import nats


class ServerState:
    def __init__(self):
        self.status: str = "NOT READY"
        self.current_simulation_id: Optional[str] = None
        self.config_path: Optional[str] = None
        self.context_id: Optional[str] = None
        self.scenario_id: Optional[str] = None
        self.nats_client: Optional[nats.NATS] = None

    def reset(self):
        self.status = "NOT READY"
        self.current_simulation_id = None
        self.config_path = None
        self.context_id = None
        self.scenario_id = None
