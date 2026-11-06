#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

set -e

# This script will initialize all required commands to have a working node setup in garage

echo "=== Garage Integrated Setup ==="

# Configuration
S3_USER="TwinCR"
BUCKET="TwinCRBucket"


# 3. Wait for instance to be ready
echo "--- Waiting for Garage to start ---"
while ! docker exec garage-twincr /garage status > /dev/null 2>&1; do
    echo "Waiting for garage to be ready..."
    sleep 2
done
echo "Garage is ready!"

# 4. Get node ID
echo "--- Getting Node ID ---"
NODE_ID=$(docker exec garage-twincr /garage node id | head -c 10)
echo "Node ID: $NODE_ID"

# 5. Assign and apply layout
echo "--- Assigning layout ---"
docker exec garage-twincr /garage layout assign -z default -c 1G "$NODE_ID"
echo "--- Applying layout ---"
docker exec garage-twincr /garage layout apply --version 1


# 6. Create user key
echo "--- Creating S3 user key ---"
KEY_INFO=$(docker exec garage-twincr /garage key create "$S3_USER")
echo "AccessKey"
ACCESS_KEY=$(echo "$KEY_INFO" | sed -n -e 's/^.*Key ID: //p')
echo $ACCESS_KEY

# 7. Save credentials to file
echo "--- Saving credentials ---"
cat >credentials.txt <<EOF
# WARNING: This file contains sensitive credentials.
# Do not commit this file to version control.

Garage S3 Credentials
=====================
$KEY_INFO

EOF

echo "Credentials saved to credentials.txt"

echo "--- Creating bucket ---"
docker exec garage-twincr /garage bucket create context-library

docker exec garage-twincr /garage bucket allow  --read --write --owner context-library --key $ACCESS_KEY


# Create archive bucket

docker exec garage-twincr /garage bucket create archive

docker exec garage-twincr /garage bucket allow  --read --write --owner archive --key $ACCESS_KEY

echo ""
echo "=== Garage Integrated Setup Complete! ==="
echo ""
echo "📋 Credentials saved to: credentials.txt"
echo ""