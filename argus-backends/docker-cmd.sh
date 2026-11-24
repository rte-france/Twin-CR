#!/bin/sh
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# ENTRYPOINT of the argus-backend images (Dockerfile.argus-backends): docker-cmd.sh scada|gm
# Every option comes from the environment (root .env with compose), with defaults for a single-host session.
set -e

case "$1" in
    scada)
        PORT="${SCADA_BACKEND_PORT:-8082}"
        JAVA_OPTS="${JAVA_OPTS:--Xmx2g}"
        EXTRA_ARGS="--estim-period ${ESTIM_PERIOD:-60}"
        ;;
    gm)
        PORT="${GAMEMASTER_BACKEND_PORT:-8083}"
        JAVA_OPTS="${JAVA_OPTS:--Xmx1536m}"
        EXTRA_ARGS=""
        ;;
    *)
        echo "Usage: $0 scada|gm" >&2
        exit 1
        ;;
esac

# JAVA_OPTS and EXTRA_ARGS are intentionally word-split
# shellcheck disable=SC2086
exec java $JAVA_OPTS -XX:+ExitOnOutOfMemoryError -jar "/app/app_$1.jar" \
    --http-port "$PORT" \
    --nats-url "${NATS_URL:-nats://localhost:4222}" \
    --config-path "${CONFIG_PATH:-config.toml}" \
    --clickhouse-host "${CLICKHOUSE_HOST:-localhost}" \
    --clickhouse-port "${CLICKHOUSE_PORT:-8123}" \
    --configurator-host "${CONFIGURATOR_HOST:-localhost}" \
    --configurator-port "${CONFIGURATOR_PORT:-8080}" \
    --mode "${MODE:-CLICKHOUSE}" \
    $EXTRA_ARGS
