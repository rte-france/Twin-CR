/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_CONTROLLER_H
#define DSL_CONTROLLER_H

#include "oatpp/core/macro/codegen.hpp"
#include "oatpp/core/macro/component.hpp"
#include "oatpp/web/server/api/ApiController.hpp"

#include "DSLEngine.h"
#include "Orchestrator.h"

#include <nlohmann/json.hpp>

#include <fstream>
#include <sstream>
#include <stdexcept>

#include OATPP_CODEGEN_BEGIN(ApiController)

/**
 * HTTP endpoints for DSLEngine.
 * Bodies are plain nlohmann::json (dumped to a string response), consistent with the rest of DSL/ScenarioHandler,
 * rather than oatpp's own DTO macros.
 */
class DSLController : public oatpp::web::server::api::ApiController {
    public:
        DSLController(DSLEngine& dsl_engine, const std::shared_ptr<ObjectMapper>& object_mapper)
            : oatpp::web::server::api::ApiController(object_mapper), dsl_engine_(dsl_engine) {}

        static std::shared_ptr<DSLController> createShared(
            DSLEngine& dsl_engine,
            OATPP_COMPONENT(std::shared_ptr<ObjectMapper>, object_mapper)) {
            return std::make_shared<DSLController>(dsl_engine, object_mapper);
        }

        ENDPOINT_INFO(getStatus) {
            info->summary = "Current DSL engine status";
            info->addResponse<String>(Status::CODE_200, "application/json");
        }
        ENDPOINT("GET", "/status", getStatus) {
            nlohmann::json counts = {{"ready", 0}, {"ongoing", 0}, {"completed", 0}, {"interrupted", 0}};
            for (auto& event : dsl_engine_.listEvents()) {
                counts[event.at("status").get<std::string>()] = counts.at(event.at("status").get<std::string>()).get<int>() + 1;
            }
            nlohmann::json body = {
                {"status", "OK"},
                {"current_time", Orchestrator::get().getCurrentTime()},
                {"simulation_name", Orchestrator::get().getSimulationName()},
                {"event_counts", counts},
            };
            return jsonResponse(Status::CODE_200, body);
        }

        ENDPOINT_INFO(postDslCommand) {
            info->summary = "Send a DSL command (parsed and committed immediately)";
            info->description = "'after 10 seconds' is ten seconds from now, 'at 10 seconds' is ten seconds into "
                                "the run. A command submitted mid-run with an 'at' time already past is rejected.";
            info->addConsumes<String>("application/json");
            info->body.addExample("Example", oatpp::Fields<oatpp::String>({
                {"dsl_command", "after 10 seconds, increase generator \"G1\" input \"P\" by 10%;"},
                {"source", "user_name"},
            }));
            info->addResponse<String>(Status::CODE_200, "application/json");
            info->addResponse<String>(Status::CODE_400, "application/json");
        }
        ENDPOINT("POST", "/trainer/dsl_command", postDslCommand, BODY_STRING(String, body)) {
            try {
                nlohmann::json parsed = nlohmann::json::parse(*body);
                std::string dsl_command = parsed.at("dsl_command").get<std::string>();
                std::string source = parsed.at("source").get<std::string>();
                dsl_engine_.loadScript(dsl_command, source);
            } catch (const std::invalid_argument& e) {
                return jsonResponse(Status::CODE_400, {{"status", e.what()}});
            } catch (const nlohmann::json::exception& e) {
                return jsonResponse(Status::CODE_400, {{"status", std::string("Invalid request body: ") + e.what()}});
            }
            return jsonResponse(Status::CODE_200, {{"status", "OK"}});
        }

        ENDPOINT_INFO(getDsl) {
            info->summary = "Current replay log (what actually executed, not the original input dsl_file)";
            info->addResponse<String>(Status::CODE_200, "text/plain");
        }
        ENDPOINT("GET", "/trainer/dsl", getDsl) {
            std::ifstream stream(dsl_engine_.getReplayLogPath());
            std::ostringstream content;
            content << stream.rdbuf();
            auto response = createResponse(Status::CODE_200, content.str());
            response->putHeader(Header::CONTENT_TYPE, "text/plain");
            return response;
        }

        ENDPOINT_INFO(getInitialDsl) {
            info->summary = "The DSL script originally loaded at engine construction (never updated afterwards)";
            info->addResponse<String>(Status::CODE_200, "text/plain");
        }
        ENDPOINT("GET", "/trainer/dsl/initial", getInitialDsl) {
            auto response = createResponse(Status::CODE_200, dsl_engine_.getInitialScript());
            response->putHeader(Header::CONTENT_TYPE, "text/plain");
            return response;
        }

        ENDPOINT_INFO(postCompletion) {
            info->summary = "Autocompletion suggestions for a partially typed statement";
            info->description = "Each suggestion is the text that replaces the last partial string of 'dsl_command' from 'replace_from' onwards.";
            info->addConsumes<String>("application/json");
            info->body.addExample("Example", oatpp::Fields<oatpp::String>({
                {"dsl_command", "after 10 seconds, increase generator \"G1\" input \"P"},
                {"source", "user_name"},
            }));
            info->addResponse<String>(Status::CODE_200, "application/json");
            info->addResponse<String>(Status::CODE_400, "application/json");
        }
        ENDPOINT("POST", "/completion", postCompletion, BODY_STRING(String, body)) {
            std::string partial;
            try {
                partial = nlohmann::json::parse(*body).at("dsl_command").get<std::string>();
            } catch (const nlohmann::json::exception& e) {
                return jsonResponse(Status::CODE_400, {{"status", std::string("Invalid request body: ") + e.what()}});
            }
            auto completions = dsl_engine_.complete(partial);
            return jsonResponse(Status::CODE_200,
                {{"suggestions", completions.suggestions}, {"replace_from", completions.replace_from}});
        }

        ENDPOINT_INFO(getQueueList) {
            info->summary = "List every event currently in the DSL engine's registry";
            info->addResponse<String>(Status::CODE_200, "application/json");
        }
        ENDPOINT("GET", "/queue/list", getQueueList) {
            return jsonResponse(Status::CODE_200, dsl_engine_.listEvents());
        }

        ENDPOINT_INFO(putQueueEvent) {
            info->summary = "Replace a Ready event's DSL text (must resolve to exactly one event)";
            info->description = "The replacement edits an event whose time is already resolved, so write it with "
                                "'at', an absolute simulation time, which is what the event's own text reads as.";
            info->addConsumes<String>("application/json");
            info->body.addExample("Example", oatpp::Fields<oatpp::String>({
                {"dsl_command", "at 10 seconds, increase generator \"G1\" input \"P\" by 10%;"},
                {"source", "user_name"},
            }));
            info->addResponse<String>(Status::CODE_200, "application/json");
            info->addResponse<String>(Status::CODE_400, "application/json");
        }
        ENDPOINT("PUT", "/queue/{id}", putQueueEvent, PATH(UInt64, id), BODY_STRING(String, body)) {
            try {
                nlohmann::json parsed = nlohmann::json::parse(*body);
                std::string dsl_command = parsed.at("dsl_command").get<std::string>();
                std::string source = parsed.at("source").get<std::string>();
                unsigned long new_id = dsl_engine_.replaceEventIfReady(static_cast<unsigned long>(*id), dsl_command, source);
                return jsonResponse(Status::CODE_200, {{"status", "OK"}, {"previous_id", static_cast<unsigned long>(*id)}, {"id", new_id}});
            } catch (const std::invalid_argument& e) {
                return jsonResponse(Status::CODE_400, {{"status", e.what()}});
            } catch (const nlohmann::json::exception& e) {
                return jsonResponse(Status::CODE_400, {{"status", std::string("Invalid request body: ") + e.what()}});
            }
        }

        ENDPOINT_INFO(deleteQueueEvent) {
            info->summary = "Cancel an event: removed if Ready, interrupted (retained) if Ongoing";
            info->addResponse<String>(Status::CODE_200, "application/json");
            info->addResponse<String>(Status::CODE_400, "application/json");
        }
        ENDPOINT("DELETE", "/queue/{id}", deleteQueueEvent, PATH(UInt64, id)) {
            if (!dsl_engine_.cancelEvent(static_cast<unsigned long>(*id))) {
                return jsonResponse(Status::CODE_400, {{"status", "Event is missing or already Completed/Interrupted"}});
            }
            return jsonResponse(Status::CODE_200, {{"status", "OK"}});
        }

    private:
        std::shared_ptr<OutgoingResponse> jsonResponse(const Status& status, const nlohmann::json& body) {
            auto response = createResponse(status, body.dump());
            response->putHeader(Header::CONTENT_TYPE, "application/json");
            return response;
        }

        DSLEngine& dsl_engine_;
};

#include OATPP_CODEGEN_END(ApiController)

#endif // DSL_CONTROLLER_H
