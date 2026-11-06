#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Usage (from Twin-CR root): fetch_simulators.sh [--force]
# simulators.zip (top-level simulators/ with dynawo and, for RTE, dynawo-rte) is the simulators source: the
# session-manager image is built from it, and simulators/ is its extraction for the orchestrator and the configurator.
# If simulators.zip is missing and FETCH_PUBLIC_DYNAWO=true, it is downloaded from the public release.
# Without --force, only runs when there is no simulators folder (container startup).
# With --force (setup.sh, CI), also runs when it exists: entries already in simulators/ are kept.

set -e

. "$(dirname "$0")/dynawo.version"

ARCHIVE=simulators.zip

# extract ARCHIVE: move its top-level entries to simulators/ (unless they already exist)
extract() {
    echo "Extracting $1";
    local extract_dir src entry
    extract_dir=$(mktemp -d);
    unzip -q "$1" -d "$extract_dir"
    src="$extract_dir"
    if [ -d "$extract_dir/simulators" ]; then
        # Avoid double-nesting (simulators/simulators) if the archive has a simulators top-level
        src="$extract_dir/simulators"
    fi
    for entry in "$src"/*; do
        if [ -e "simulators/$(basename "$entry")" ]; then
            echo "Keeping existing simulators/$(basename "$entry")";
        else
            mv "$entry" simulators/;
        fi
    done
    rm -rf "$extract_dir";
}

# download_public: download the public simulators.zip of the release to $ARCHIVE
download_public() {
    echo "Downloading the public Dynawo ($DYNAWO_RELEASE_TAG)";
    local auth=() asset_url
    if [ -n "$GITHUB_TOKEN" ]; then
        # Private repository with authentication
        auth=(-H "Authorization: token $GITHUB_TOKEN")
    fi
    asset_url=$(curl -fsSL "${auth[@]}" \
        https://api.github.com/repos/rte-france/Twin-CR/releases/tags/$DYNAWO_RELEASE_TAG \
        | jq -r '.assets[] | select(.name=="simulators.zip") | .url') || true
    if [ -z "$asset_url" ]; then
        echo "simulators.zip not found in release $DYNAWO_RELEASE_TAG (if the repository is private, set GITHUB_TOKEN)";
        exit 1;
    fi
    # Download next to it then rename, so that an interrupted download does not leave a truncated $ARCHIVE
    curl -fL "${auth[@]}" -H "Accept: application/octet-stream" "$asset_url" -o "$ARCHIVE.part"
    mv "$ARCHIVE.part" "$ARCHIVE"
}

if [ ! -d simulators ] || [ "$1" = "--force" ]; then
    if [ ! -r "$ARCHIVE" ] && [ "$FETCH_PUBLIC_DYNAWO" = "true" ]; then
        download_public
    fi

    mkdir -p simulators
    if [ -r "$ARCHIVE" ]; then
        extract "$ARCHIVE"
    fi

    if [ ! -x simulators/dynawo/dynawo.sh ] && [ ! -x simulators/dynawo-rte/dynawo.sh ]; then
        echo "No simulators available: compile Dynawo or put a simulators.zip archive in current dir";
    fi
fi
