/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_WEB_INTERFACE_H
#define DSL_WEB_INTERFACE_H

#include <memory>
#include <thread>

class DSLEngine;
class AppComponent;

namespace oatpp { namespace network { class Server; } }

/**
 * HTTP/REST API for DSLEngine (oatpp + oatpp-swagger), bound to DSL_SERVER_PORT (see Credentials).
 * DSL_SERVER_HOST (a docker-compose-level concept, not read here) is a network alias for other containers;
 * Swagger UI itself always advertises localhost, since it's only ever browsed by a human on their own machine.
 * The blocking oatpp server run() loop lives on its own thread, stopped/joined in the destructor.
 */
class DSLWebInterface {
    public:
        explicit DSLWebInterface(DSLEngine& dsl_engine);
        ~DSLWebInterface();

        DSLWebInterface(const DSLWebInterface&) = delete;
        DSLWebInterface& operator=(const DSLWebInterface&) = delete;

    private:
        std::unique_ptr<AppComponent> app_component_;
        std::shared_ptr<oatpp::network::Server> server_;
        std::thread server_thread_;
};

#endif // DSL_WEB_INTERFACE_H
