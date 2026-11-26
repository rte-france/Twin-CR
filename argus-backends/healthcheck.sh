#!/bin/sh
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

case "$1" in
    scada) PORT="${SCADA_BACKEND_PORT:-8082}" ;;
    gm) PORT="${GAMEMASTER_BACKEND_PORT:-8083}" ;;
    *) echo "Usage: $0 scada|gm" >&2; exit 1 ;;
esac
wget -q -O /dev/null "http://localhost:$PORT/health"
