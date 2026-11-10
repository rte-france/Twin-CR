#
# Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the Twin-CR project.
#

FROM node:22-slim AS builder
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@latest-10 --activate

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build

FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html

COPY --from=builder /app/dist ./
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY config.json.template /etc/nginx/templates/config.json.template

ENV NGINX_ENVSUBST_OUTPUT_DIR=/usr/share/nginx/html

EXPOSE 80
