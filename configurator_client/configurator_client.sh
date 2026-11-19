#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Startup command of the configurator-client images

unset http_proxy https_proxy ftp_proxy no_proxy HTTP_PROXY HTTPS_PROXY FTP_PROXY NO_PROXY
cd /home/orchestrator/configurator_client
if [ "${MODE:-CLICKHOUSE}" = "CLICKHOUSE" ]; then
    exec python -u -m fastapi run src/main.py --host 0.0.0.0 --port "${CONFIGURATOR_PORT:-8080}"
else
    echo "MODE=$MODE, configurator is thus not used";
    tail -f /dev/null
fi