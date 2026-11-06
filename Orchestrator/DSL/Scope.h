/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef SCOPE_H
#define SCOPE_H

#include "SerialisationHelper.h"

#include <ser20/types/variant.hpp>

#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

/**
 * A resolved binding for a function parameter ($var), or an argument to
 * a function call: a single element id, a number, a boolean, or a list of
 * element ids (for a list/cluster target argument).
 */
using ParamValue = std::variant<std::string, double, bool>;

/**
 * A regex-based cluster definition (`regex "..." on <gridElementType>`), resolved and cached to a
 * plain id list on first use (see DSLProgramVisitor::resolveTarget).
 */
struct ClusterRegexDef {
    std::string element_type;  // A pypowsybl element type, or a model library when is_dynamic_model
    std::string pattern;
    bool is_dynamic_model = false;

    template<class Archive>
    void serialize(Archive& ar) { ar(element_type, pattern, is_dynamic_model); }
};
CHECK_SERIALIZABLE(ClusterRegexDef);

/**
 * A cluster's definition: a static id list, or a not-yet-resolved regex spec (ClusterRegexDef).
 */
struct ClusterDef {
    std::string element_type;  // A pypowsybl element type, or a model library when is_dynamic_model
    std::variant<std::vector<std::string>, ClusterRegexDef> definition;
    bool is_dynamic_model = false;

    template<class Archive>
    void serialize(Archive& ar) { ar(element_type, definition, is_dynamic_model); }
};
CHECK_SERIALIZABLE(ClusterDef);

/**
 * Scope chain: tags, clusters, and $var bindings visible at a given point in the DSL.
 * Creating a new local scope is done via newFrame() which create a new empty scope object
 * with a read-only reference to its parent scope.
 * Tags/clusters are resolved by first looking for a local value, then parent, then grandparent, etc.
 */
class Scope : public std::enable_shared_from_this<Scope> {
    public:
        Scope() = default;  // Root/global frame, also required default constructor for deserialization

        static std::shared_ptr<Scope> newFrame(std::shared_ptr<const Scope> parent, std::string invocation_id);

        void defineCluster(const std::string& cluster_id, ClusterDef def);
        void defineTag(const std::string& bare_tag_name);
        void bindParam(const std::string& param_name, ParamValue value);

        std::optional<ClusterDef> resolveCluster(const std::string& cluster_id) const;
        /**
         * Every cluster name visible from this frame, this one and its ancestors. For autocompletion.
         */
        std::vector<std::string> clusterNames() const;
        /**
         * Returns true if this Scope (not a parent) contains a cluster definition
         */
        bool definesCluster(const std::string& cluster_id) const;
        /**
         * Returns the fully-qualified tag key ("<invocation_id>/<bare_tag_name>"), walking the
         * parent chain so the qualified key is found regardless of which ancestor frame declared it.
         */
        std::optional<std::string> resolveTag(const std::string& bare_tag_name) const;
        /**
         * $var resolution is deliberately NOT delegated to parent_: a function's parameters are
         * its own explicit interface, so a callee never transparently observes a caller's $var
         * of the same name.
         */
        std::optional<ParamValue> resolveParamLocalOnly(const std::string& param_name) const;

        const std::string& invocationId() const { return invocation_id_; }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(invocation_id_, clusters_, tags_, params_, parent_);
        }

    private:
        std::string invocation_id_;
        std::unordered_map<std::string, ClusterDef> clusters_;
        std::unordered_map<std::string, std::string> tags_;   // bare tag -> invocation_id_ + "/" + bare tag
        std::unordered_map<std::string, ParamValue> params_;
        std::shared_ptr<const Scope> parent_;
};
CHECK_SERIALIZABLE(Scope);

#endif // SCOPE_H
