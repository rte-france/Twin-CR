#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


# Startup command of the twincr-core image (envs/Dockerfile.orchestrator)

set -e

cd /home/orchestrator/
# Extracts the simulators if there is no simulators folder yet; before unsetting the proxies since it may download them
bash "$(dirname "$0")/fetch_simulators.sh"
unset http_proxy https_proxy ftp_proxy no_proxy HTTP_PROXY HTTPS_PROXY FTP_PROXY NO_PROXY

# The orchestrator runs in the background so that this script can act once it has exited: the stop signals of the
# container (compose down, Nomad job stop) are forwarded to it, and such a stop ends the script right away.
STOPPING=false
ORCHESTRATOR_PID=""
on_stop() {
    STOPPING=true
    if [ -n "$ORCHESTRATOR_PID" ]; then
        kill -TERM "$ORCHESTRATOR_PID" 2>/dev/null || true
    fi
}
trap on_stop TERM INT

if [ "$MODE" = "CLICKHOUSE" ]; then
    orchestrator_exec --from-clickhouse &
else
    orchestrator_exec --from-nats &
fi
ORCHESTRATOR_PID=$!
# wait gives the exit code of the orchestrator, even if it already exited. It returns early (>128) when a trapped
# signal arrives: wait again while the orchestrator is still running.
while true; do
    wait "$ORCHESTRATOR_PID" && EXIT_CODE=0 || EXIT_CODE=$?
    if [ "$EXIT_CODE" -gt 128 ] && kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
        continue
    fi
    break
done
echo "Orchestrator exited with code $EXIT_CODE"
rm -f /tmp/orchestrator_healthcheck  # No longer healthy: the end (or crash) of the simulation shows in the healthcheck
# After a crash, kill Dynawo if it is still alive
pkill -TERM -x dynawo && echo "Stopped the remaining Dynawo process" || true
if [ "$STOPPING" = true ]; then
    exit "$EXIT_CODE"
fi

# Archive the simulation in any case (end or crash): the configurator skips it if it was already archived
if [ "$MODE" = "CLICKHOUSE" ]; then
    echo "Requesting the archive of the simulation"
    curl -sS --noproxy '*' --max-time 3600 \
        "http://${CONFIGURATOR_HOST:-localhost}:${CONFIGURATOR_PORT:-8080}/archive" \
        || echo "Archive request failed"
    echo
fi

# For Nomad session: the container stays up after the simulation (the session, its services and logs remain available
# until it is stopped explicitly), otherwise the exit would fail the session and stop all its tasks
if [ "${KEEP_ALIVE_AFTER_EXIT:-false}" = true ] && [ "$STOPPING" = false ]; then
    echo "Simulation over, waiting for the session to be stopped"
    tail -f /dev/null &
    ORCHESTRATOR_PID=$!  # A stop signal ends the wait
    wait "$ORCHESTRATOR_PID" || true
fi
exit "$EXIT_CODE"
