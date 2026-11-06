/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Scope.h"

std::shared_ptr<Scope> Scope::newFrame(std::shared_ptr<const Scope> parent, std::string invocation_id) {
    auto scope = std::make_shared<Scope>();
    scope->invocation_id_ = std::move(invocation_id);
    scope->parent_ = std::move(parent);
    return scope;
}

void Scope::defineCluster(const std::string& cluster_id, ClusterDef def) {
    clusters_[cluster_id] = std::move(def);
}

void Scope::defineTag(const std::string& bare_tag_name) {
    tags_[bare_tag_name] = invocation_id_ + "/" + bare_tag_name;
}

void Scope::bindParam(const std::string& param_name, ParamValue value) {
    params_[param_name] = std::move(value);
}

std::vector<std::string> Scope::clusterNames() const {
    std::vector<std::string> names;
    for (auto& [name, def] : clusters_) names.push_back(name);
    if (parent_) {
        auto inherited = parent_->clusterNames();
        names.insert(names.end(), inherited.begin(), inherited.end());
    }
    return names;
}

bool Scope::definesCluster(const std::string& cluster_id) const {
    return clusters_.contains(cluster_id);
}

std::optional<ClusterDef> Scope::resolveCluster(const std::string& cluster_id) const {
    if (clusters_.contains(cluster_id)) return clusters_.at(cluster_id);
    if (parent_) return parent_->resolveCluster(cluster_id);
    return std::nullopt;
}

std::optional<std::string> Scope::resolveTag(const std::string& bare_tag_name) const {
    if (tags_.contains(bare_tag_name)) return tags_.at(bare_tag_name);
    if (parent_) return parent_->resolveTag(bare_tag_name);
    return std::nullopt;
}

std::optional<ParamValue> Scope::resolveParamLocalOnly(const std::string& param_name) const {
    if (params_.contains(param_name)) return params_.at(param_name);
    return std::nullopt;
}
