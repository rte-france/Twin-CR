#! /bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#
# Optional AMS path for the Nordic example. NRT keeps using cfg.sh (no AMS).
# Usage: ./cfg_ams.sh
# Optional: AMS_DEVICE=cpu|cuda|auto|mps (default: auto)
# Optional: --models-dir /path/to/my_models  (add on the ams.sh line below)
#


set -euo pipefail
cd "$(dirname "$0")"

DATE=$(date +%Y%m%d.%H%M)
BASE_PATH="$(cd ../../../.. && pwd)"

# Default: bundled Nordic checkpoints. For your own models, add on the line below:
#   --models-dir /path/to/my_models
# See ams/README.md for AMS usage.
"$BASE_PATH/ams/ams.sh" Nordic.dsl Nordic.xiidm Nordic.dyd \
	--network Nordic --epsilon 5 --device "${AMS_DEVICE:-auto}"

./config.sh --iidm Nordic.xiidm \
	--dyd Nordic.dyd  # 2>&1 | tee cfg.$DATE.log
