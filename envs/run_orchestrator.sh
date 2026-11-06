#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


set -e

cd /home/orchestrator/
if [ "$MODE" = "CLICKHOUSE" ]; then
    orchestrator_exec --from-clickhouse
else
    orchestrator_exec --from-nats
fi