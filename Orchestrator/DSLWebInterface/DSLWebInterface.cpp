/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLWebInterface.h"
#include "AppComponent.h"
#include "DSLController.h"
#include "Credentials.h"

#include "oatpp/core/base/Environment.hpp"
#include "oatpp/network/Server.hpp"
#include "oatpp/web/server/interceptor/AllowCorsGlobal.hpp"
#include "oatpp-swagger/Controller.hpp"

#include <spdlog/spdlog.h>

DSLWebInterface::DSLWebInterface(DSLEngine& dsl_engine) {
    oatpp::base::Environment::init();

    app_component_ = std::make_unique<AppComponent>(static_cast<v_uint16>(Credentials::get().getDslServerPort()));

    OATPP_COMPONENT(std::shared_ptr<oatpp::web::server::HttpRouter>, router);
    OATPP_COMPONENT(std::shared_ptr<oatpp::data::mapping::ObjectMapper>, object_mapper);
    OATPP_COMPONENT(std::shared_ptr<oatpp::network::ServerConnectionProvider>, connection_provider);
    OATPP_COMPONENT(std::shared_ptr<oatpp::web::server::HttpConnectionHandler>, connection_handler);

    auto dsl_controller = std::make_shared<DSLController>(dsl_engine, object_mapper);
    router->addController(dsl_controller);

    oatpp::web::server::api::Endpoints doc_endpoints;
    doc_endpoints.append(dsl_controller->getEndpoints());
    router->addController(oatpp::swagger::Controller::createShared(doc_endpoints));

    connection_handler->addRequestInterceptor(std::make_shared<oatpp::web::server::interceptor::AllowOptionsGlobal>());
    connection_handler->addResponseInterceptor(std::make_shared<oatpp::web::server::interceptor::AllowCorsGlobal>());

    server_ = std::make_shared<oatpp::network::Server>(connection_provider, connection_handler);
    auto server = server_;
    server_thread_ = std::thread([server] { server->run(); });

    spdlog::info("DSL web interface listening on port {}", Credentials::get().getDslServerPort());
}

DSLWebInterface::~DSLWebInterface() {
    server_->stop();
    if (server_thread_.joinable()) server_thread_.join();
    // Reset oatpp components in dependency order before calling destroy()
    server_.reset();
    app_component_.reset();
    oatpp::base::Environment::destroy();
}
