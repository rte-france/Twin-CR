/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef XML_HANDLER_H
#define XML_HANDLER_H

#include "DynawoEvents.h"

#include "pugixml.hpp"

#include <filesystem>
#include <optional>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

class XMLHandler {
    public:
        XMLHandler(const std::filesystem::path& xml_file);
        std::filesystem::path getPath() { return path_; }
        std::filesystem::path getWorkingDir() { return path_.parent_path(); }
    protected:
        pugi::xml_document doc_;
    private:
        std::filesystem::path path_;
};

class DydHandler: XMLHandler {
    public:
        DydHandler(const std::filesystem::path& xml_file) : XMLHandler(xml_file) {};

        std::unordered_map<std::string, std::unique_ptr<DynawoEvent>> getEvents();

        /**
         * Get the list of all par files that are referenced by this dyd file
         */
        std::unordered_set<std::filesystem::path> getReferencedParFiles();
};

class JobHandler: XMLHandler {
    public:
        JobHandler(const std::filesystem::path& xml_file) : XMLHandler(xml_file) {};

        std::filesystem::path getIidm();

        std::optional<std::filesystem::path> getOutputDir();
        std::vector<std::filesystem::path> getLogPaths();
        std::optional<std::filesystem::path> getOutputIidmPath();
        std::optional<std::filesystem::path> getOutputFinalStateValuesPath();

        /**
         * Get the path of all the files needed to run the simulation (i.e. all the path directly or indirectly referenced by the jobs file)
         */
        std::unordered_set<std::filesystem::path> getAllInputPaths();

        double getStartTime();

        double getStopTime();

        bool hasTimeline();

        bool hasConstraints();
};

class IIDMHandler: XMLHandler {
    public:
        IIDMHandler(const std::filesystem::path& xml_file);

        /**
         * Returns the ids of every IIDM element of the given pypowsybl type (e.g. 2_windings_transformer)
         */
        std::vector<std::string> getIds(const std::string& pypowysbl_type) const;

    private:
        std::unordered_map<std::string, std::vector<std::string>> ids_by_type_;
};

#endif // XML_HANDLER_H
