#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

FROM python:3.14-slim
LABEL org.opencontainers.image.licenses="MPL-2.0"

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /home/orchestrator/configurator_client
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN mkdir -p $UV_PROJECT_ENVIRONMENT
RUN uv sync --frozen --no-cache --no-install-project

# Copy the source code
COPY . /home/orchestrator/configurator_client

CMD ["fastapi", "run", "src/main.py", "--port", "8080", "--host", "0.0.0.0"]
