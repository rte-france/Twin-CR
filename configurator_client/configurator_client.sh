#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


cd /home/orchestrator/configurator_client
if [ "$MODE" = "CLICKHOUSE" ]; then
    python -u -m fastapi run src/main.py --host 0.0.0.0 --port 8080
else
    echo "MODE=$MODE, configurator is thus not used";
    tail -f /dev/null
fi