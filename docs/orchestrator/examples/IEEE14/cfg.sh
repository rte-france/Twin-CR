#! /bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

set -e

DATE=$(date +%Y%m%d.%H%M)

./config.sh  # 2>&1 | tee cfg.$DATE.log
