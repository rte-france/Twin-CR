#! /bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Only relevant for Linux platform
if [ `uname` != "Linux" ]; then
	echo "AppImage can only be built on Linux platform, exiting"
	exit 1
fi
DIR=$(dirname $(realpath "$0"))
cd $DIR/..

# Argus AppImage build
echo "=== Argus AppImage build - start = $(date) ==="
/usr/bin/time -v bash -c "docker build --progress=plain -f envs/Dockerfile.argus.AppImage -t argus_ai . 2>&1"
echo "=== Argus AppImage build - end = $(date) ==="

# Copy AppImages to local folder
docker run --rm -u $(id -u):$(id -g) -v $(pwd):$(pwd) argus_ai bash -c "cd $(pwd); mkdir AppImage; cp -fp /app/*.AppImage /app/bundle*.zst AppImage"
