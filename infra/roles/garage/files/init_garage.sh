#!/bin/bash
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


set -e

echo "=========================================="
echo "      Twin-CR Infrastructure Setup        "
echo "=========================================="

S3_USER="TwinCR"
BUCKET="twincr-templates"
CAPACITY="1G"

# ==========================================
# 1. SETUP GARAGE (S3)
# ==========================================
export no_proxy="${no_proxy:-},127.0.0.1,localhost,172.28.0.0/16,172.17.0.0/16"
export NO_PROXY="${NO_PROXY:-},127.0.0.1,localhost,172.28.0.0/16,172.17.0.0/16"
if [ -f /etc/nomad.d/nomad.token ]; then
    export NOMAD_TOKEN="${NOMAD_TOKEN:-$(cat /etc/nomad.d/nomad.token | tr -d '\r\n')}"
fi

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

KEY_LIST=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key list 2>/dev/null || true)
if ! echo "$KEY_LIST" | grep -q "$S3_USER"; then
    RAW_ID=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage node id | head -n 1)
    NODE_ID=$(echo "$RAW_ID" | head -c 10)
    echo "--- Assigning and applying layout ---"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage layout assign -z default -c "$CAPACITY" "$NODE_ID"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage layout apply --version 1 || true
    echo "--- Creating S3 user key ---"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key create "$S3_USER" > /dev/null
fi

ACCESS_KEY=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key list | grep "$S3_USER" | awk '{print $1}' | head -n 1)
SECRET_KEY=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage key info --show-secret "$ACCESS_KEY" | grep "Secret key:" | awk '{print $3}')

BUCKET_LIST=$(nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket list)
if ! echo "$BUCKET_LIST" | grep -q "$BUCKET"; then
    echo "--- Creating bucket '$BUCKET' ---"
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket create "$BUCKET"
fi

echo "--- Setting bucket permissions ---"
nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket allow "$BUCKET" --read --write --key "$ACCESS_KEY"

# Ensure required Twin-CR buckets exist
for b in context-library archive; do
    if ! echo "$BUCKET_LIST" | grep -q "$b"; then
        echo "--- Creating bucket '$b' ---"
        nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket create "$b"
    fi
    nomad alloc exec -task garage-daemon "$GARAGE_ALLOC_ID" /garage bucket allow "$b" --read --write --key "$ACCESS_KEY"
done

# Seed credentials into Vault KV for workloads (twincr-apps, sessions)
if command -v vault >/dev/null 2>&1; then
    echo "--- Storing Garage credentials in Vault KV (secret/garage) ---"
    export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
    if [ -f /etc/vault.d/vault.creds ]; then
        VAULT_TOKEN=$(grep -E '^VAULT_ROOT_TOKEN=' /etc/vault.d/vault.creds | cut -d '"' -f2)
        export VAULT_TOKEN
    fi
    vault kv put secret/garage access_key="$ACCESS_KEY" secret_key="$SECRET_KEY" || true
fi

echo "=== Garage initialization completed successfully! ==="
