#!/bin/sh
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


# Auto-unseal Vault using locally saved unseal key if sealed
if [ ! -f /etc/vault.d/vault.creds ]; then
    exit 0
fi

UNSEAL_KEY=$(grep '^VAULT_UNSEAL_KEY=' /etc/vault.d/vault.creds | cut -d'"' -f2)
if [ -z "$UNSEAL_KEY" ]; then
    exit 0
fi

# Wait for Vault port 8200 to respond
RETRIES=15
while ! curl -s -o /dev/null http://127.0.0.1:8200/v1/sys/seal-status; do
    RETRIES=$((RETRIES - 1))
    [ "$RETRIES" -le 0 ] && exit 0
    sleep 1
done

IS_SEALED=$(curl -s http://127.0.0.1:8200/v1/sys/seal-status | jq -r '.sealed // false')
if [ "$IS_SEALED" = "true" ]; then
    curl -s -X POST -H "Content-Type: application/json" -d "{\"key\":\"$UNSEAL_KEY\"}" http://127.0.0.1:8200/v1/sys/unseal >/dev/null 2>&1 || true
fi
exit 0
