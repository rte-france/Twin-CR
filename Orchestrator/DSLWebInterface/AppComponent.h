/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_WEB_APP_COMPONENT_H
#define DSL_WEB_APP_COMPONENT_H

#include "oatpp/core/macro/component.hpp"
#include "oatpp/network/Address.hpp"
#include "oatpp/network/tcp/server/ConnectionProvider.hpp"
#include "oatpp/parser/json/mapping/ObjectMapper.hpp"
#include "oatpp/web/server/HttpConnectionHandler.hpp"
#include "oatpp/web/server/HttpRouter.hpp"

#include "oatpp-swagger/Model.hpp"
#include "oatpp-swagger/Resources.hpp"

#include <filesystem>

// Set via target_compile_definitions in CMakeLists.txt: BUILD is the FetchContent source dir
// (preferred, always fresh), INSTALLED is used only when BUILD doesn't exist (i.e. Docker).
#ifndef OATPP_SWAGGER_RES_PATH_BUILD
#error "OATPP_SWAGGER_RES_PATH_BUILD must be defined by CMake"
#endif
#ifndef OATPP_SWAGGER_RES_PATH_INSTALLED
#error "OATPP_SWAGGER_RES_PATH_INSTALLED must be defined by CMake"
#endif

/**
 * oatpp DI component wiring for the DSL web interface.
 */
class AppComponent {
    public:
        explicit AppComponent(v_uint16 port) : port_(port) {}

    private:  // port_ must be declared before the OATPP_CREATE_COMPONENT members since default member initializers run in declaration order
        v_uint16 port_;

    public:
        OATPP_CREATE_COMPONENT(std::shared_ptr<oatpp::network::ServerConnectionProvider>, serverConnectionProvider)([this] {
            return oatpp::network::tcp::server::ConnectionProvider::createShared({"0.0.0.0", port_, oatpp::network::Address::IP_4});
        }());

        OATPP_CREATE_COMPONENT(std::shared_ptr<oatpp::web::server::HttpRouter>, httpRouter)([] {
            return oatpp::web::server::HttpRouter::createShared();
        }());

        // Concrete (not base ConnectionHandler) type so DSLWebInterface can register CORS interceptors on it.
        OATPP_CREATE_COMPONENT(std::shared_ptr<oatpp::web::server::HttpConnectionHandler>, serverConnectionHandler)([] {
            OATPP_COMPONENT(std::shared_ptr<oatpp::web::server::HttpRouter>, router);
            return oatpp::web::server::HttpConnectionHandler::createShared(router);
        }());

        OATPP_CREATE_COMPONENT(std::shared_ptr<oatpp::data::mapping::ObjectMapper>, apiObjectMapper)([] {
            return oatpp::parser::json::mapping::ObjectMapper::createShared();
        }());

        // addServer() with localhost: the Swagger UI itself is only ever browsed by a human on their own machine (via the Docker port mapping),
        // not from other containers, so its generated curl snippets should always be directly runnable from a local terminal as-is.
        OATPP_CREATE_COMPONENT(std::shared_ptr<oatpp::swagger::DocumentInfo>, swaggerDocumentInfo)([this] {
            oatpp::swagger::DocumentInfo::Builder builder;
            builder.setTitle("DSL Engine API")
                   .setDescription("HTTP interface for the PowerEventDSL engine")
                   .setVersion("1.0")
                   .addServer("http://localhost:" + std::to_string(port_), "DSL Engine");
            return builder.build();
        }());

        // Resources::getResource() only ever looks in its in-memory cache (never falls back to disk on a miss);
        // loadResources() (rather than the plain constructor) is what actually populates that cache upfront.
        OATPP_CREATE_COMPONENT(std::shared_ptr<oatpp::swagger::Resources>, swaggerResources)([] {
            std::string res_path = std::filesystem::exists(OATPP_SWAGGER_RES_PATH_BUILD)
                ? OATPP_SWAGGER_RES_PATH_BUILD
                : OATPP_SWAGGER_RES_PATH_INSTALLED;
            return oatpp::swagger::Resources::loadResources(res_path);
        }());
};

#endif // DSL_WEB_APP_COMPONENT_H
