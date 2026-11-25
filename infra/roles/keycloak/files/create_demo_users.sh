#!/bin/bash
#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#


set -e

KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}" # gitleaks:allow

user_exists() {
  local username="$1"
  local token="$2"
  echo "Checking if user $username exists..."

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
  echo "Creating user $username..."
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

associate_user_with_role() {
  local username="$1"
  local role_name="$2"
  local client_id="$3"
  local token="$4"
  echo "Associating user $username to role $role_name..."

  user_id=$(curl --noproxy "*" -s \
    -H "Authorization: Bearer $token" \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$username" \
    | jq -r '.[0].id')

  role=$(curl --noproxy "*" -s -H "Authorization: Bearer $token" \
    "$KEYCLOAK_URL/admin/realms/$REALM/clients/$client_id/roles/$role_name")

  curl --noproxy "*" -s -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id/role-mappings/clients/$client_id" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "[$role]"
}

create_user_with_role() {
  local username="$1"
  local role_name="$2"
  local token="$3"

  if ! user_exists "$username" "$token"; then
    create_user "$username" "$token"

    client_id=$(curl --noproxy "*" -s \
      -H "Authorization: Bearer $token" \
      "$KEYCLOAK_URL/admin/realms/$REALM/clients?clientId=$CLIENT" \
      | jq -r '.[0].id')

    associate_user_with_role "$username" "$role_name" "$client_id" "$token"
  else
    echo "User $username already exists"
  fi
}

echo "Waiting for Keycloak to become ready..."

until token=$(curl --noproxy "*" -s -f \
    -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "grant_type=password" \
    -d "username=$KEYCLOAK_ADMIN" \
    --data-urlencode "password=$KEYCLOAK_ADMIN_PASSWORD" | jq -r .access_token 2>/dev/null) \
    && [ "$token" != "null" ] && [ -n "$token" ]; do
    echo "Keycloak auth not ready yet. Retrying in 5 seconds..."
    sleep 5
done
echo "Keycloak is ready! Token acquired."

create_user_with_role "$GAMEMASTER" "$GAMEMASTER_ROLE" "$token"
create_user_with_role "$SCADA" "$SCADA_ROLE" "$token"

echo "Demo users setup complete."
