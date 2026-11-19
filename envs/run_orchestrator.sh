#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


# Startup command of the twincr-core image (envs/Dockerfile.orchestrator)

set -e

cd /home/orchestrator/
# Extracts the simulators if there is no simulators folder yet; before unsetting the proxies since it may download them
bash "$(dirname "$0")/fetch_simulators.sh"
unset http_proxy https_proxy ftp_proxy no_proxy HTTP_PROXY HTTPS_PROXY FTP_PROXY NO_PROXY
if [ "$MODE" = "CLICKHOUSE" ]; then
    exec orchestrator_exec --from-clickhouse
else
    exec orchestrator_exec --from-nats
fi
