#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

FROM alpine:3.20
LABEL org.opencontainers.image.licenses="MPL-2.0"

RUN apk add --no-cache bash curl jq

COPY seed.sh /seed.sh

ENTRYPOINT ["/bin/bash", "/seed.sh"]
