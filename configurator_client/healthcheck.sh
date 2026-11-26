#!/bin/bash
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Outside CLICKHOUSE mode the configurator is not used (see docker-cmd.sh) and always reports healthy.
if [ "${MODE:-CLICKHOUSE}" = "CLICKHOUSE" ]; then
    curl -fsS --noproxy '*' -o /dev/null "http://localhost:${CONFIGURATOR_PORT:-8080}/status"
fi
