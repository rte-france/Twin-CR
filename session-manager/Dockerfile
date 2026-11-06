#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Extract simulators archive
FROM alpine:latest AS extractor

RUN apk add --no-cache unzip
WORKDIR /extracted
COPY simulators.zip .
RUN unzip simulators.zip

# Force amd64 for pypowsybl, pulled in via dynawo_toolbox (no linux/arm64 wheels are published)
FROM --platform=linux/amd64 python:3.14-slim
LABEL org.opencontainers.image.licenses="MPL-2.0"

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /home/session-manager/
COPY ./session-manager/pyproject.toml ./session-manager/uv.lock ./

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/home/tools/dynawo_toolbox/src
RUN mkdir -p $UV_PROJECT_ENVIRONMENT
RUN uv sync --frozen --no-cache --no-install-project --no-install-local

# Simulators are baked in: session-manager may run on another host than Twin-CR
COPY --from=extractor /extracted/simulators /home/session-manager/simulators

# Copy the source code
COPY ./session-manager/backend /home/session-manager/backend
COPY ./tools/dynawo_toolbox/src /home/tools/dynawo_toolbox/src

CMD ["fastapi", "run", "backend/main.py", "--port", "8090", "--host", "0.0.0.0"]
