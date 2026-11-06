#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

FROM quay.io/keycloak/keycloak:26.6.1

USER root

RUN mkdir -p /opt/keycloak/conf/tls

# The keystore password is random, generated with the keystore at build time and only
# stored in the image next to it (conf/keycloak.conf), so it never appears in the repository.
RUN password="$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32)" \
    && keytool \
    -genkeypair \
    -alias keycloak \
    -keyalg RSA \
    -keysize 2048 \
    -validity 3650 \
    -storetype PKCS12 \
    -keystore /opt/keycloak/conf/tls/server.p12 \
    -storepass "$password" \
    -keypass "$password" \
    -dname "CN=localhost, OU=Dev, O=Dev, L=Dev, S=Dev, C=FR" \
    -ext SAN=dns:localhost,ip:127.0.0.1 \
    && echo "https-key-store-password=$password" >> /opt/keycloak/conf/keycloak.conf

USER keycloak