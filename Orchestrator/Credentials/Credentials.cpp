/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Credentials.h"
#include "../utils/EnvironmentVariable.h"

#include "spdlog/spdlog.h"

#include <stdexcept>


bool Credentials::loaded_ = false;
static Credentials inst;

Credentials& Credentials::get() {
    if (!loaded_) {
        throw std::logic_error("Credentials should be loaded first");
    }
    return inst;
}

void Credentials::load_credentials() {
    inst.load_nats_credentials();
    inst.load_clickhouse_credentials();
    inst.load_dsl_server_credentials();

    loaded_ = true;
}

void Credentials::load_nats_credentials() {
    nats_url_ = getEnvironmentVariableOrDefault("NATS_URL", "nats://localhost:4222");

    spdlog::debug("Will connect to NATS server on {}", nats_url_);
}

void Credentials::load_clickhouse_credentials() {
    std::string clickhouse_host = getEnvironmentVariableOrDefault("CLICKHOUSE_HOST", "localhost");
    std::string clickhouse_port = getEnvironmentVariableOrDefault("CLICKHOUSE_PORT", "8123");
    clickhouse_url_ = "http://" + clickhouse_host + ":" + clickhouse_port + "/";

    spdlog::debug("Will connect to Clickhouse server on {}", clickhouse_url_);

    std::string clickhouse_username = getEnvironmentVariableOrDefault("CLICKHOUSE_USERNAME", "");
    std::string clickhouse_password = getEnvironmentVariableOrDefault("CLICKHOUSE_PASSWORD", "");

    if (!clickhouse_username.empty() && !clickhouse_password.empty()) {
        clickhouse_credentials_ = clickhouse_username + ":" + clickhouse_password;
    } else {
        clickhouse_credentials_ = "";
    }

    if (clickhouse_credentials_.empty()) {
        spdlog::debug("Will connect to Clickhouse server without credentials");
    } else {
        spdlog::debug("Will connect to Clickhouse server with credentials: {}", clickhouse_credentials_);
    }
}

void Credentials::load_dsl_server_credentials() {
    dsl_server_port_ = std::stoi(getEnvironmentVariableOrDefault("DSL_SERVER_PORT", "8000"));

    spdlog::debug("DSL web interface will bind to port {}", dsl_server_port_);
}
