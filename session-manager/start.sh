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
# Keep-alive longer than the idle connections kept by the HTTP clients (Argus: 90 s): otherwise a client may reuse a
# connection the server is closing (uvicorn default: 5 s), and the request fails without response.
exec uvicorn backend.main:app --host 0.0.0.0 --port 8090 --timeout-keep-alive 120
