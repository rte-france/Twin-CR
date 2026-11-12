"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Defaults to a file in the working directory for local `uv run`; the compose
# service points it at a mounted volume so the catalogue outlives the container.
DB_URL = os.environ.get("DB_URL", "sqlite:///database.db")

KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")  # Reached container-to-container over plain HTTP
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "twincr")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "session-manager-client")
JWKS_URL = f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

# Off by default: echoing prints bound parameters, so an accesskey insert puts
# the generated passwords in the log in clear. It is also ~80% of the output,
# which buries everything else.
DB_ECHO = os.getenv("DB_ECHO", "").strip().lower() in ("1", "true", "yes", "on")

BUCKET = os.getenv("BUCKET", "")
S3_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
S3_PRIVATE_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
GARAGE_HOST = os.getenv("GARAGE_HOST", "")
GARAGE_PORT = os.getenv("GARAGE_PORT", "")
DYNAWO_HOME = os.getenv("DYNAWO_HOME", "")
CONFIGURATOR_HOST = os.getenv("CONFIGURATOR_HOST", "")
CONFIGURATOR_EXPOSED_PORT = os.getenv("CONFIGURATOR_EXPOSED_PORT", "")
CONFIGURATOR_CLIENT_ENDPOINT = os.getenv("CONFIGURATOR_CLIENT_ENDPOINT", f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_EXPOSED_PORT}")
S3_ENDPOINT = f"http://{GARAGE_HOST}:{GARAGE_PORT}"

UPDATE_SESSION_STATE_TIMEOUT = 5

KEYCLOAK_VERIFY_TLS = os.getenv("KEYCLOAK_VERIFY_TLS", "FALSE").casefold() == "true"
SIMULATORS_PATH = os.getenv("SIMULATORS_PATH", "/home/session-manager/simulators")
EXTRA_RULES_PATH = os.getenv("EXTRA_RULES_PATH", "/home/session-manager/dynawo_rules")