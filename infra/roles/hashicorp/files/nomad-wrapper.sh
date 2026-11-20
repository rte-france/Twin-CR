#!/bin/sh
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Transparent Nomad wrapper that injects management token when running locally
if [ -z "$NOMAD_TOKEN" ] && [ -f /etc/nomad.d/nomad.token ]; then
    export NOMAD_TOKEN="$(cat /etc/nomad.d/nomad.token | tr -d '\r\n')"
fi
exec /usr/bin/nomad.real "$@"
