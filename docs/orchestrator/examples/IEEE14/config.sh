#! /bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Stop on the first failing command, so that cfg.sh fails too
set -eo pipefail

BASE_PATH=$(realpath $(dirname config.sh)/../../../..)
export DYNAWO_HOME=$BASE_PATH/simulators/dynawo
export PYTHONPATH=$BASE_PATH
if [ ! -d $PYTHONPATH/tools/dynawo_toolbox/venv ]; then
	(cd $PYTHONPATH/tools/dynawo_toolbox && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt) \
		|| { echo "Virtual environment creation failed"; exit 1; }
fi
PVERSION=$($PYTHONPATH/tools/dynawo_toolbox/venv/bin/python3 --version)
PVERSIONC=${PVERSION:7}
PMAJOR=$(echo $PVERSIONC | cut -d. -f1)
PMINOR=$(echo $PVERSIONC | cut -d. -f2)
PPATCH=$(echo $PVERSIONC | cut -d. -f3)
if [[ $PMAJOR -eq 3 ]] && [[ $PMINOR -lt 11 ]]; then
	echo "Twin-CR requires a python version >= 3.11"
	exit 1
fi

# Get the jobs file and the master period from the config
CONFIG=${CONFIG:-config.toml}
VENV_PY=$PYTHONPATH/tools/dynawo_toolbox/venv/bin/python3
READ_CONFIG=$PYTHONPATH/tools/dynawo_toolbox/src/read_config.py

DERIVED=()
if [ -f "$CONFIG" ]; then
	DERIVED+=(--jobs "$($VENV_PY $READ_CONFIG "$CONFIG" input_files.job_file)")
	DERIVED+=(--period "$($VENV_PY $READ_CONFIG "$CONFIG" master.period)")
	EXTRA_IO=$($VENV_PY $READ_CONFIG "$CONFIG" input_files.extra_io_file --optional)
	if [ -n "$EXTRA_IO" ]; then
		DERIVED+=(--extra_io_file "$EXTRA_IO")
	fi
fi

$VENV_PY $PYTHONPATH/tools/dynawo_toolbox/src/main_configure.py "${DERIVED[@]}" "$@"
