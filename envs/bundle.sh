#! /bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


LOG=bundle.log.$(date +%Y%m%d.%H%M)

# Download necessary binaries for bundling AppIMage
export TAURI_CACHE=$HOME/.cache/tauri
mkdir -p $TAURI_CACHE
wget -O $TAURI_CACHE/AppRun-x86_64 https://github.com/AppImage/AppImageKit/releases/download/continuous/AppRun-x86_64
wget -O $TAURI_CACHE/linuxdeploy-x86_64.AppImage https://github.com/tauri-apps/binary-releases/releases/download/linuxdeploy/linuxdeploy-x86_64.AppImage
wget -O $TAURI_CACHE/linuxdeploy-plugin-gtk.sh https://raw.githubusercontent.com/tauri-apps/linuxdeploy-plugin-gtk/master/linuxdeploy-plugin-gtk.sh
wget -O $TAURI_CACHE/linuxdeploy-plugin-gstreamer.sh https://raw.githubusercontent.com/tauri-apps/linuxdeploy-plugin-gstreamer/master/linuxdeploy-plugin-gstreamer.sh
chmod a+x $TAURI_CACHE/*

bs()
{
    # $1 == true -> debug
    # $2 archive name
    echo "= build = $(date) ="  | tee -a $LOG
    if  [ "$1" == "true" ]; then
        OPTIONS=-d
        VERSION=debug
    else
        OPTIONS=
        VERSION=release
    fi
    pnpm tauri build $OPTIONS --no-bundle 2>&1 | tee -a $LOG
    echo "= bundle $VERSION = $(date) ="  | tee -a $LOG
    NO_STRIP=true pnpm tauri bundle $OPTIONS -v --bundles appimage 2>&1 | tee -a $LOG
    ls -la src-tauri/target/$VERSION/bundle/appimage 2>&1 | tee -a $LOG
    (cd src-tauri/target/$VERSION/bundle/appimage && cp -p *.AppImage ../../../../../$2-$VERSION.AppImage) 2>&1 | tee -a $LOG
}

echo "=== start bundle = $(date) ===" | tee -a $LOG
rm -r src-tauri/target
echo "= pnpm install = $(date) =" | tee -a $LOG
pnpm install
# Debug version
echo "= bs true argus = $(date) =" | tee -a $LOG
bs true argus
# Release version
echo "= bs false argus = $(date) =" | tee -a $LOG
bs false argus
# Clean
rm -r src-tauri/target
echo "=== end bundle = $(date) =" | tee -a $LOG