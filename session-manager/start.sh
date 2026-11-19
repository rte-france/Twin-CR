#!/bin/bash
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Startup command of the session-manager images
unset http_proxy https_proxy ftp_proxy no_proxy HTTP_PROXY HTTPS_PROXY FTP_PROXY NO_PROXY
cd /home/session-manager/
exec fastapi run backend/main.py --port 8090 --host 0.0.0.0
