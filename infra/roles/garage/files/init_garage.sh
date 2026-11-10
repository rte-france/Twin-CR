#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the Twin-CR project.
#

set -e

echo "=========================================="
echo "      TwinEu Infrastructure Setup         "
echo "=========================================="

S3_USER="TwinEU"
BUCKET="twineu-templates"
CAPACITY="1G"

# ==========================================
# 1. SETUP GARAGE (S3)
# ==========================================
echo -e "\n=== Garage Setup ==="
echo "--- Waiting for Garage Nomad allocation to become 'running' ---"
GARAGE_ALLOC_ID=""
while [ -z "$GARAGE_ALLOC_ID" ]; do
    GARAGE_ALLOC_ID=$(nomad job allocs garage | awk '/running/ {print $1}' | head -n 1)
    if [ -z "$GARAGE_ALLOC_ID" ]; then sleep 2; fi
done
echo "Found Garage Allocation ID: $GARAGE_ALLOC_ID"

echo "--- Waiting for Garage daemon to be ready ---"
while ! nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage status > /dev/null 2>&1; do
    sleep 2
done
echo "Garage daemon is ready!"

RAW_ID=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage node id | head -n 1)
NODE_ID=$(echo "$RAW_ID" | head -c 10)

LAYOUT_CHECK=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage layout show)
if ! echo "$LAYOUT_CHECK" | grep -q "$NODE_ID"; then
    echo "--- Assigning and applying layout ---"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage layout assign -z default -c "$CAPACITY" "$NODE_ID"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage layout apply --version 1
fi

KEY_LIST=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key list)
if ! echo "$KEY_LIST" | grep -q "$S3_USER"; then
    echo "--- Creating S3 user key ---"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key create "$S3_USER" > /dev/null
fi

ACCESS_KEY=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key list | grep "$S3_USER" | awk '{print $1}' | head -n 1)
SECRET_KEY=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key info "$ACCESS_KEY" | grep "Secret key" | awk '{print $4}')

BUCKET_LIST=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket list)
if ! echo "$BUCKET_LIST" | grep -q "$BUCKET"; then
    echo "--- Creating bucket '$BUCKET' ---"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket create "$BUCKET"
fi

echo "--- Setting bucket permissions ---"
nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket allow "$BUCKET" --read --write --key "$ACCESS_KEY"


# ==========================================
# 2. SETUP POSTGRES (Database)
# ==========================================
echo -e "\n=== Postgres Setup ==="
echo "--- Waiting for Database Nomad allocation to become 'running' ---"
DB_ALLOC_ID=""
while [ -z "$DB_ALLOC_ID" ]; do
    DB_ALLOC_ID=$(nomad job allocs postgres | awk '/running/ {print $1}' | head -n 1)
    if [ -z "$DB_ALLOC_ID" ]; then sleep 2; fi
done
echo "Found DB Allocation ID: $DB_ALLOC_ID"

echo "--- Waiting for Postgres to be ready to accept connections ---"
while ! nomad alloc exec -task postgres "$DB_ALLOC_ID" pg_isready -U twineu_api -d twineu > /dev/null 2>&1; do
    sleep 2
done
echo "Postgres is ready and database 'twineu' is accessible!"


# ==========================================
# 3. PRINT .ENV
# ==========================================
echo -e "\n=========================================="
echo "    SETUP COMPLETE ! Update your .env :   "
echo "=========================================="
cat <<EOF
# ==========================================
# DATABASE (Postgres)
# ==========================================
DATABASE_URL=postgresql+asyncpg://twineu_api:twineu_password@127.0.0.1:5433/twineu

# ==========================================
# FILE SYSTEM (Garage S3)
# ==========================================
S3_ENDPOINT_URL=http://s3.localhost
S3_ACCESS_KEY_ID=$ACCESS_KEY
S3_SECRET_ACCESS_KEY=$SECRET_KEY
S3_BUCKET_NAME=$BUCKET
EOF
echo "=========================================="