/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DYNAWO_INTERFACE_H
#define DYNAWO_INTERFACE_H

#include "ClickHouseLogger.h"
#include "DynawoHandlers/DynawoEvents.h"
#include "DynawoHandlers/XmlHandler.h"
#include "../utils/DynawoInterfaceInterface.h"
#include "DynawoSender.h"
#include "DynawoReceiver.h"
#include "InformationFlowModel.h"
#include "ProcessLauncher.h"

#include <atomic>
#include <graaflib/types.h>
#include <memory>
#include <toml++/toml.h>
#include <filesystem>


struct DynawoInput {
    DynawoInput(const std::string& id_, double factor_) :
        id(id_), factor(factor_) {}

    std::string id;
    double factor;
};

struct GameMaster_output {
    GameMaster_output(const std::string& id_, const std::string& topic_, double factor_) :
        id(id_), topic(topic_), factor(factor_) {}

    std::string id;
    std::string topic;
    double factor;
};

struct SCADA_output {
    SCADA_output(const std::string& id_, const std::string& destination_, std::vector<graaf::vertex_id_t> routing_, const std::string& topic_,
                const std::optional<std::string>& tase2_id_, double factor_, bool publish_on_change_, double last_value_, double period_, double period_offset, double start_time) :
        id(id_), destination(destination_), routing(routing_), topic(topic_), tase2_id(tase2_id_),
        factor(factor_), publish_on_change(publish_on_change_), last_value(last_value_), period(period_) {
            last_publication_time = (start_time + period_offset) - period_;  // Last publication time is initially before start time
        }

    std::string id;
    std::string destination;
    std::vector<graaf::vertex_id_t> routing;
    std::string topic;
    std::optional<std::string> tase2_id;
    double factor;
    bool publish_on_change;
    double last_value;
    double period;
    double last_publication_time;
    std::atomic_bool requested = false;
};

struct IIDM_key {
    IIDM_key(const std::string& iidm_id_, const std::string& attribute_) :
        iidm_id(iidm_id_), attribute(attribute_) {};

    std::string iidm_id;
    std::string attribute;

    bool operator==(const IIDM_key& other) const noexcept {
        return iidm_id == other.iidm_id && attribute == other.attribute;
    }
};

struct IIDM_key_hash {
    std::size_t operator()(const IIDM_key& k) const noexcept {
        std::size_t h1 = std::hash<std::string>{}(k.iidm_id);
        std::size_t h2 = std::hash<std::string>{}(k.attribute);
        return h1 ^ (h2 << 1);
    }
};

/**
 * Identity of a Dynawo input on a purely dynamic model, similar to an IIDM equipement, but
 * equipmentId -> model
 * type -> model_lib
 */
struct DynamicModel_key {
    DynamicModel_key(const std::string& dynamic_model_, const std::string& kind_) :
        dynamic_model(dynamic_model_), kind(kind_) {};

    std::string dynamic_model;
    std::string kind;

    bool operator==(const DynamicModel_key& other) const noexcept {
        return dynamic_model == other.dynamic_model && kind == other.kind;
    }
};

struct DynamicModel_key_hash {
    std::size_t operator()(const DynamicModel_key& k) const noexcept {
        std::size_t h1 = std::hash<std::string>{}(k.dynamic_model);
        std::size_t h2 = std::hash<std::string>{}(k.kind);
        return h1 ^ (h2 << 1);
    }
};

/**
 * Class responsible for handling information exchanges with Dynawo and for keeping Dynawo running in real-time
 * (following the Orchestrator directives). Information exchanges and time keeping are performed through ZMQ.
 * More precisely, the DynawoSender sends control signals to Dynawo and tells it when to go the the next timestep.
 * The DynawoReceiver gets information from Dynawo.
 */
class DynawoInterface : public DynawoInterfaceInterface {
    public:
        DynawoInterface(const InformationFlowModel& information_flow_model, double dynawo_start_time, double actual_start_time, double end_time, ClickHouseLogger& logger, ProcessLauncher& process_launcher, bool save_input_files);
        ~DynawoInterface();

        /**
         * Send a control signal to Dynawo
         */
        void applyControl(const std::string& id, const Value& value);

        /**
         * Scale the multiplier of the Dynawo Updatable (UpdatableDiscrete/UpdatableContinuous)
         * associated with id, if any. Prints a warning and does nothing otherwise (id not in
         * dynawo_events_, or not an UpdatableDiscrete/UpdatableContinuous).
         * In the future, this functionality will be added to all Dynawo connections
         */
        void scaleMultiplierBy(const std::string& id, double multiplier_increase);

        void requestSCADAPublication(std::vector<std::string> scada_ids);

        std::string getInputFromIidm(const std::string& iidm_id, const std::string& attribute) const;
        std::string getOutputFromIidm(const std::string& iidm_id, const std::string& attribute) const override;
        std::vector<std::string> listInputAttributes(const std::string& iidm_id) const override;
        std::vector<std::string> listOutputAttributes(const std::string& iidm_id) const override;

        /**
         * Returns the ids of every IIDM element of the given pypowsybl type (e.g. 2_windings_transformer)
         */
        std::vector<std::string> listIidmIds(const std::string& pypowsybl_type) const override;

        std::string getInputFromDynamicModel(const std::string& dynamic_model, const std::string& kind) const;
        std::string getOutputFromDynamicModel(const std::string& dynamic_model, const std::string& kind) const override;
        std::vector<std::string> listDynamicModelLibs(DynamicModelDirection direction) const override;
        std::vector<std::string> listDynamicModelIds(const std::string& model_lib, DynamicModelDirection direction) const override;
        std::vector<std::string> listDynamicModelInputKinds(const std::string& dynamic_model) const override;
        std::vector<std::string> listDynamicModelOutputKinds(const std::string& dynamic_model) const override;

    private:
        void onControlReceived(const ControlReceived& info);
        void onActualControl(const ActualControl& info);

        /**
         * Fast TS return (control flag "with_fast_TS"). Directly return the TS to the control sender without waiting for the next Dynawo timestep.
         * The other modules still receive the TS at the next Dynawo step (scada_output.value unchanged, so the value is still published on change at
         * the next Dynawo time step).
         */
        void sendFastTS(const ControlReceived& info);

        /**
         * Reset the Dynawo event used in applyControl(). Must be called one timestep after applyControl() so that the Dynawo event can be reused in the future.
         */
        void resetControl(const std::string& control_id);

        /**
         * Tell Dynawo to go to its next time step, then read the measurements of the current time step and send them to the cyber layer.
         */
        void goToNextTimeStep();

        /**
         * Launch Dynawo and schedule the next time step event
         */
        void initDynawo(double dynawo_start_time, double actual_start_time);

        /**
         * Get the list of published curve names from Dynawo
         */
        void getDynawoCurveNames();

        /**
         * Send the Dynawo input files (jobs, dyd, par, iidm, etc.) to the logger
         */
        void logInputFiles();

    public:
        /**
         * Send the Dynawo output files to the logger
         * Curves, timeline and constraints are not saved as they generate events that are directly logged instead
         */
        void logOutputFiles();

    private:
        double end_time_;
        double period_;
        std::atomic<double> current_time_;
        double start_time_ = 0.0;
        unsigned long step_index_ = 0;
        double next_dynawo_time_;
        bool has_timeline_;
        bool has_constraints_;
        std::atomic<bool> dynawo_running_;
        std::filesystem::path my_env_dynawo_path_;
        std::filesystem::path job_file_;
        std::filesystem::path game_master_inputs_file_;
        std::filesystem::path game_master_outputs_file_;
        std::unordered_map<std::string, std::unique_ptr<DynawoEvent>> dynawo_events_;
        std::unordered_map<std::string, std::pair<ModelParameters*, std::string>> model_parameters_ids_;
        DynawoSender sender_;
        DynawoReceiver curve_receiver_;
        DynawoReceiver curve_names_receiver_;
        DynawoReceiver timeline_receiver_;
        DynawoReceiver constraints_receiver_;
        ClickHouseLogger& logger_;
        ProcessLauncher& subprocess_;
        const InformationFlowModel& information_flow_model_;
        std::unordered_map<std::string, DynawoInput> dynawo_input_by_id_;
        std::unordered_map<IIDM_key, std::string, IIDM_key_hash> iidm_to_dynawo_input_;
        std::unordered_map<IIDM_key, std::string, IIDM_key_hash> iidm_to_dynawo_output_;
        std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash> dynamic_model_to_dynawo_input_;
        std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash> dynamic_model_to_dynawo_output_;
        std::unordered_map<std::string, std::string> model_lib_by_dynamic_model_;  // Fed by both directions: a model can carry inputs, outputs or both
        std::unique_ptr<IIDMHandler> iidm_handler_;
        std::vector<int> game_master_outputs_per_curve_;
        std::vector<GameMaster_output> game_master_outputs_by_curve_index_;
        std::unordered_map<std::string, std::vector<GameMaster_output>> game_master_outputs_by_curve_name_;
        std::vector<int> scada_outputs_per_curve_;
        std::vector<std::shared_ptr<SCADA_output>> scada_outputs_by_curve_index_;
        std::unordered_map<std::string, std::vector<std::shared_ptr<SCADA_output>>> scada_outputs_by_curve_name_;
        std::unordered_map<std::string, std::vector<std::shared_ptr<SCADA_output>>> scada_outputs_by_scada_id_;
        std::thread std_out_reader_;
};

#endif // DYNAWO_INTERFACE_H
