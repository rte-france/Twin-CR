#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


set -e

KEYCLOAK_URL="http://keycloak:8080" # url inside the container
REALM="twincr"
CLIENT="session-manager-client"
USER_ALICE="alice"
USER_BOB="bob"
TEMPLATE_MANAGER="template_manager"
SESSION_LAUNCHER="session_launcher"
PARTICIPANT_GM="participant_gm"
PARTICIPANT_OP="participant_operator"

# Admin of the master realm, set in .env (see .env-example) and passed by docker-compose.yaml
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
if [ -z "${KEYCLOAK_ADMIN_PASSWORD:-}" ]; then
  echo "KEYCLOAK_ADMIN_PASSWORD is not set, see .env-example" >&2
  exit 1
fi

user_exists() {
  local username="$1"
  local token="$2"
  echo "Checking if user $username exists"

  local count=$(curl --noproxy "*" -s \
    -H "Authorization: Bearer $token" \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$username" | jq length)

  if [ "$count" -gt 0 ]; then
    return 0
  else
    return 1
  fi
}

create_user() {
  local username="$1"
  local token="$2"
  echo "Creating user $username"
  curl --noproxy "*" -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d @- <<EOF 
{
  "username": "$username",
  "enabled": true,
  "email": "$username@example.com",
  "firstName": "$username",
  "lastName": "$username",
  "emailVerified": true,
  "credentials": [
    {
      "type": "password",
      "value": "$username",
      "temporary": false
    }
  ]
}
EOF
}

associate_user_with_roles() {
  local username="$1"
  local client_id="$2"
  local token="$3"
  shift 3

  local roles=("$@")

  user_id=$(curl --noproxy "*" -s \
    -H "Authorization: Bearer $token" \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$username" \
    | jq -r '.[0].id')

  for role_name in "${roles[@]}"; do
    echo "Associating user $username to role $role_name"

    role=$(curl --noproxy "*" -s \
      -H "Authorization: Bearer $token" \
      "$KEYCLOAK_URL/admin/realms/$REALM/clients/$client_id/roles/$role_name")

    curl --noproxy "*" -s -X POST \
      "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id/role-mappings/clients/$client_id" \
      -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" \
      -d "[$role]"
  done
}

create_user_with_roles() {
  local username="$1"
  local token="$2"
  shift 2

  local roles=("$@")

  if ! user_exists "$username" "$token"; then

    create_user "$username" "$token"

    client_id=$(curl --noproxy "*" -s \
      -H "Authorization: Bearer $token" \
      "$KEYCLOAK_URL/admin/realms/$REALM/clients?clientId=$CLIENT" \
      | jq -r '.[0].id')

    associate_user_with_roles \
      "$username" \
      "$client_id" \
      "$token" \
      "${roles[@]}"

  else
    echo "User $username already exists"
  fi
}

until token=$(curl --noproxy "*" -s -f \
    -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "grant_type=password" \
    --data-urlencode "username=$KEYCLOAK_ADMIN" \
    --data-urlencode "password=$KEYCLOAK_ADMIN_PASSWORD" | jq -r .access_token) \
    && [ "$token" != "null" ] && [ -n "$token" ]; do

    echo "Waiting for Keycloak (auth not ready)..."
    sleep 5
done

# Create demo users with their roles
alice_roles=($TEMPLATE_MANAGER $SESSION_LAUNCHER)
bob_roles=($PARTICIPANT_GM)
create_user_with_roles "$USER_ALICE" "$token" "${alice_roles[@]}"
create_user_with_roles "$USER_BOB" "$token" "${bob_roles[@]}"
