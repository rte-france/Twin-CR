"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    environment: str = Field(default="development")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # Nomad
    nomad_url: str = Field(default="http://127.0.0.1:4646")
    nomad_token: str = Field(default="")

    # Consul
    consul_url: str = Field(default="http://consul.twin.eu")

    # Temporal
    temporal_address: str = Field(default="temporal-grpc.localhost:80")
    temporal_namespace: str = Field(default="default")

    # Keycloak
    keycloak_url: str = Field(default="https://keycloak.localhost")
    keycloak_realm: str = Field(default="twineu")
    keycloak_client_id: str = Field(default="session-manager-client")
    keycloak_client_secret: str = Field(default="")

    # Traefik / Network
    base_domain: str = Field(default="localhost")

    # Database (Postgres)
    database_url: str = Field(
        default="postgresql+asyncpg://twineu_api:twineu_password@127.0.0.1:5433/twineu"
    )

    # File System (Garage S3)
    s3_endpoint_url: str = Field(default="http://s3.localhost")
    s3_access_key_id: str = Field(default="")
    s3_secret_access_key: str = Field(default="")
    s3_bucket_name: str = Field(default="twineu-templates")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
