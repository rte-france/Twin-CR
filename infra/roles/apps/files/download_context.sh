#!/bin/sh
#
# Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the Twin-CR project.
#

set -e

echo "Downloading context ${CONTEXT_ID} from Garage S3..."
mkdir -p /local/context

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="garage"

aws --endpoint-url "${S3_ENDPOINT}" s3 sync "s3://${BUCKET}/CONTEXTS/${CONTEXT_ID}/DATA" /local/context

echo "Context files downloaded successfully:"
ls -la /local/context