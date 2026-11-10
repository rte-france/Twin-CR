#!/usr/bin/env bash
#
# Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the Twin-CR project.
#

#
# Wrapper script delegating to mise tasks
#

set -euo pipefail

cd "$(dirname "$0")"

# If mise is installed, run via mise
if command -v mise >/dev/null 2>&1; then
    exec mise run setup "$@"
fi

# Fallback: prompt or install mise
echo "mise is required to run setup tasks. Please install mise: https://mise.jdx.dev" >&2
exit 1