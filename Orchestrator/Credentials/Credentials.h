/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef CREDENTIALS_H
#define CREDENTIALS_H

#include <string>

class Credentials {
    public:
        // Singleton accessor
        static Credentials& get();

        static void load_credentials();

        const char* getNatsURL() { return nats_url_.c_str(); }
        const char* getClickhouseURL() { return clickhouse_url_.c_str(); }
        const std::string& getClickhouseCredentials() { return clickhouse_credentials_; }
        int getDslServerPort() { return dsl_server_port_; }

    private:
        void load_nats_credentials();
        void load_clickhouse_credentials();
        void load_dsl_server_credentials();

        static bool loaded_;

        std::string nats_url_;
        std::string clickhouse_url_;
        std::string clickhouse_credentials_;
        int dsl_server_port_ = 0;
};

#endif // CREDENTIALS_H
