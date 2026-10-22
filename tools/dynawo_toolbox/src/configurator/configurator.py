"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
from collections import Counter
from pathlib import Path
from enum import Enum
import re
import copy
import fnmatch
from typing import Any

import yaml
import pandas as pd
import pypowsybl as pp
from lxml import etree

from handlers.dyd_handler import DydHandler
from handlers.iidm_handler import IIDMHandler
from handlers.par_handler import ParHandlerLoader, ParHandler
from mapping.iidm_id_to_physical_type import get_iidm_id_to_physical_type_map
from handlers.timapped_handler import TiMapper

INPUT_RULES_PATH = Path(__file__).parent / "input_rules.yaml"
OUTPUT_RULES_PATH = Path(__file__).parent / "output_rules.yaml"
DYNAWO_MODELS_DATA_PATH = Path(__file__).parent / "dynawo_models_data.json"
DYNAWO_NSMAP = {None: "http://www.rte-france.com/dynawo"}
ROOT_CYBER_NODE_NAME = "SCADA"
MOCK_CYBER_CONFIG_NAME = "cyber_config_fake.json"
LIB_PATTERN_CHARS = ("*", "?", "[")  # A rule model library key containing one of these is a glob pattern (fnmatch)

def alphabetic_side_to_numeric(side : str) -> str:
    if side is None:
        return ""
    if side == "ONE":
        return "1"
    if side == "TWO":
        return "2"
    if side == "THREE":
        return "3"
    raise ValueError()

class InOrOut(Enum):
    IN = 1
    OUT = 2


class ModelLibrary:
    def __init__(self, models_path: Path | str):
        if isinstance(models_path, str):
            models_path = Path(models_path)
        if not models_path.is_dir():
            raise ValueError(f"Dynawo models directory {models_path} does not exist")
        self._models_path = models_path
        self._lib_to_extvars = {}
        self._lib_to_desc = {}

    def get_model_extvars(self, lib):
        if lib not in self._lib_to_extvars:
            self._extract_model_extvar(lib)
        return self._lib_to_extvars[lib]

    def get_model_variables(self, lib):
        if lib not in self._lib_to_desc:
            self._extract_model_desc(lib)
        return self._lib_to_desc[lib]["variables"]

    def get_model_parameters(self, lib):
        if lib not in self._lib_to_desc:
            self._extract_model_desc(lib)
        return self._lib_to_desc[lib]["parameters"]

    def _extract_model_extvar(self, lib):
        extvar_file = self._models_path / (lib + ".extvar")
        if not extvar_file.is_file():
            # A library controlled only through its parameters has no external variables, and so no extvar file
            self._lib_to_extvars[lib] = []
            return
        tree = etree.parse(extvar_file)
        root = tree.getroot()
        extvars = [dict(extvar.attrib) for extvar in root.findall('variable', namespaces=root.nsmap)]
        for extvar in extvars:
            # Extvars don't have a "name" field, so add it based on id
            extvar["name"] = extvar["id"].replace('.', '_')
        self._lib_to_extvars[lib] = extvars

    def _extract_model_desc(self, lib):
        desc_file = self._models_path / (lib + ".desc.xml")
        if not desc_file.is_file():
            raise ValueError(f"No desc.xml file found for library {lib}")
        tree = etree.parse(desc_file)
        root = tree.getroot()
        variables = [dict(var.attrib) for var in root.findall('elements/variables/variable', namespaces=root.nsmap)]
        parameters = [dict(par.attrib) for par in root.findall('elements/parameters/parameter', namespaces=root.nsmap)]
        self._lib_to_desc[lib] = {"variables": variables, "parameters": parameters}

class Configurator:
    def __init__(self, iidm_file, dyd_files: str | Path | list[str | Path], models_path: Path | str,
                 extra_rules_dir: Path | str | None = None):
        """
        `dyd_files` is every input dyd the job declares, excluding the connectors
        file this class generates: models, parameter references and existing
        connections are all read across the whole set.
        `extra_rules_dir` optionally holds input_rules.yaml and/or output_rules.yaml files merged over the default
        rules (e.g. the rules of a private model library, see _load_rules).
        """
        if isinstance(dyd_files, (str, Path)):
            dyd_files = [dyd_files]
        self._iidm_file = iidm_file
        self._network = pp.network.load(iidm_file)
        self._iidm_handler = IIDMHandler(iidm_file)
        self._dyd_handlers = [DydHandler(dyd_file) for dyd_file in dyd_files]
        self.models: pd.DataFrame = self._build_models_list()
        if extra_rules_dir and not Path(extra_rules_dir).is_dir():
            raise FileNotFoundError(f"Extra rules directory {extra_rules_dir} not found")
        extra_rules_path = lambda rules_path: Path(extra_rules_dir) / rules_path.name if extra_rules_dir else None
        self._input_rules = self._load_rules(INPUT_RULES_PATH, extra_rules_path(INPUT_RULES_PATH))
        self._output_rules = self._load_rules(OUTPUT_RULES_PATH, extra_rules_path(OUTPUT_RULES_PATH))
        self._model_library = ModelLibrary(models_path)
        self._outputs_variables = None
        self._par_handler_loader = ParHandlerLoader()
        self._rules_cache = {}

    def get_retained_switches(self):
        sw = self._network.get_switches()
        return sw[sw["retained"] == True]

    def _build_models_list(self):
        models = []
        models_by_static_id = {}
        for dyd_handler in self._dyd_handlers:
            for dm in dyd_handler.get_dynamic_models():
                dyn_id = dm.get("id")
                static_id = dm.get("staticId")  # May be None
                model_lib = dm.get("lib")
                par_file = dm.get("parFile")
                if par_file is not None:
                    par_file = dyd_handler.get_path().parent / par_file  # Par_file is relative to its own dyd file
                par_id = dm.get("parId")
                models.append({"dynamic_id": dyn_id, "static_id": static_id, "model_lib": model_lib, "par_file": par_file, "par_id": par_id})
                if static_id is not None:
                    models_by_static_id[static_id] = models[-1]

        voltage_levels = self._network.get_voltage_levels()
        element_getters = {
            "2_windings_transformer": self._network.get_2_windings_transformers,
            "battery": self._network.get_batteries,
            "bus": self._network.get_bus_breaker_view_buses,
            "busbar_section": self._network.get_busbar_sections,
            "generator": self._network.get_generators,
            "hvdc_line": self._network.get_hvdc_lines,
            "line": self._network.get_lines,
            "load": self._network.get_loads,
            "shunt_compensator": self._network.get_shunt_compensators,
            "static_var_compensator": self._network.get_static_var_compensators,
            "switch": self.get_retained_switches
        }

        for iidm_class, getter in element_getters.items():
            static_elements_df: pd.DataFrame = getter()
            for name, row in static_elements_df.iterrows():
                if name not in models_by_static_id:
                    model = {"iidm_class": iidm_class,
                             "static_id": name}
                    models.append(model)
                else:
                    model = models_by_static_id[name]
                    model["iidm_class"] = iidm_class
                if 'voltage_level1_id' in row:
                    model['voltage_level1'] = row['voltage_level1_id']
                    model['substation1'] = voltage_levels.at[row['voltage_level1_id'], 'substation_id']
                    model['voltage_level2'] = row['voltage_level2_id']
                    model['substation2'] = voltage_levels.at[row['voltage_level2_id'], 'substation_id']
                    if model['substation1'] == model['substation2']:
                        model['substation'] = model['substation1']  # Transformers have both ends in the same substation
                elif 'voltage_level_id' in row:
                    model['voltage_level'] = row['voltage_level_id']
                    model['substation'] = voltage_levels.at[row['voltage_level_id'], 'substation_id']
        models_df = pd.DataFrame(models)
        models_df = models_df.where(pd.notna(models_df), None)
        return models_df

    @staticmethod
    def _load_rules(yaml_path: str | Path, extra_yaml_path: str | Path | None = None):
        """
        Load and resolve the rules of yaml_path. The sections of extra_yaml_path, if it exists, are merged over them
        before the resolution: its keys override the keys of yaml_path and can reference them.
        """
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)
        if extra_yaml_path is not None and Path(extra_yaml_path).exists():
            with open(extra_yaml_path, "r") as f:
                for iidm_class, model_data in (yaml.safe_load(f) or {}).items():
                    config[iidm_class] = {**(config.get(iidm_class) or {}), **(model_data or {})}

        rules = {}
        for iidm_class, model_data in config.items():
            for model_lib in model_data:
                rules[(iidm_class, model_lib)] = Configurator._resolve_lib_rules(config, iidm_class, model_lib, [])
        return rules

    @staticmethod
    def _parse_rules_reference(reference: str, iidm_class):
        """
        A reference is "key" (key of the same section) or "section:key" (key of another section), where "null" stands
        for the null section or the null key. The key is matched exactly, even if it is a glob pattern key.
        """
        if ":" in reference:
            section, key = reference.split(":", 1)
            null_to_none = lambda name: None if name == "null" else name
            return null_to_none(section), null_to_none(key)
        return iidm_class, reference

    @staticmethod
    def _resolve_lib_rules(config: dict, iidm_class, model_lib, visited: list) -> dict:
        """
        Resolve the rules of a (section, model library key), following references to other keys (see the rule files
        header). A key value can be:
          - a dictionary {kind: rule} (or [] for no rule),
          - a string: alias of another key,
          - a dictionary with an "extends" entry referencing another key: the rules of the referenced key, where the
            other entries add or override rules by kind, a null entry removing the kind.
        References can be chained, a cycle or an unknown key raises a ValueError.
        """
        key = (iidm_class, model_lib)
        name = lambda k: ":".join("null" if part is None else str(part) for part in k)
        if key in visited:
            raise ValueError("Cycle in the rules references: " + " -> ".join(name(k) for k in visited + [key]))
        if iidm_class not in config or model_lib not in (config[iidm_class] or {}):
            raise ValueError(f"Unknown rules reference {name(key)}" + (f" (from {name(visited[-1])})" if visited else ""))
        value = config[iidm_class][model_lib]
        visited = visited + [key]
        if isinstance(value, str):  # Alias
            return Configurator._resolve_lib_rules(config, *Configurator._parse_rules_reference(value, iidm_class), visited)
        value = dict(value) if value else {}
        if "extends" in value:
            base = Configurator._resolve_lib_rules(
                config, *Configurator._parse_rules_reference(value.pop("extends"), iidm_class), visited)
            for kind, rule in value.items():
                if rule is None:
                    base.pop(kind, None)
                else:
                    base[kind] = rule
            value = base
        return value

    def write_dynawo_inputs(self, output_file: str | Path, pretty_print: bool=True):
        if self._outputs_variables is None:
            self._generate_variables()

        keep_keys = ["equipmentId", "model_lib", "kind", "side", "id", "factor"]
        filtered_inputs = []
        for item in self._inputs_variables:
            dynawo_input = {k: v for k, v in item.items() if k in keep_keys}
            dynawo_input["simulator"] = "dynawo"
            if item.get("is_parameter", False):
                dynawo_input["model"] = item["model"]
                dynawo_input["variable"] = item["variable"]
            elif item.get("equipmentId") is None and "model_lib" in item:
                # Purely dynamic model: no equipmentId to be keyed on, so name its model
                dynawo_input["model"] = item["model"]
            filtered_inputs.append(dynawo_input)
        with open(output_file, "w") as f:
            json.dump(filtered_inputs, f, indent=4 if pretty_print else None)

    def write_dynawo_outputs(self, output_file: str | Path, pretty_print: bool=True):
        if self._outputs_variables is None:
            self._generate_variables()

        keep_keys = ["equipmentId", "model_lib", "kind", "side", "id", "dynawo_id", "topic", "factor", "substation", "voltage_level"]
        filtered_outputs = []
        for item in self._outputs_variables:
            dynawo_output = {k: v for k, v in item.items() if k in keep_keys}
            dynawo_output["simulator"] = "dynawo"
            if "model_lib" in item:  # Purely dynamic model: no equipmentId to be keyed on, so name its model
                dynawo_output["model"] = item["model"]
            filtered_outputs.append(dynawo_output)
        with open(output_file, "w") as f:
            json.dump(filtered_outputs, f, indent=4 if pretty_print else None)

    def write_scada_io(self, inputs_file: str | Path, outputs_file: str | Path, communication_file: str | Path | None, cyber_mapping_file: str | Path | None, pretty_print: bool=True) -> Path | None:
        """
        Write the SCADA I/O files.

        Returns the mock cyber config path when one was generated.
        """
        mock_cyber_config = None
        if communication_file is None or cyber_mapping_file is None:
            mock_cyber_config = Path(inputs_file).parent / MOCK_CYBER_CONFIG_NAME
            self._generate_mock_scada_variables(mock_cyber_config, pretty_print=pretty_print)
        else:
            self._generate_scada_variables_from_config(communication_file, cyber_mapping_file)

        keep_keys = ["id", "destination", "tase2", "equipmentId", "kind"]
        filtered_inputs = [
            {**{k: v for k, v in item.items() if k in keep_keys}, "simulator": "dynawo"}
            for item in self._scada_inputs
        ]

        keep_keys = ["equipmentId", "kind", "side", "id", "dynawo_id", "topic", "factor",
                     "source", "destination", "tase2", "publish_on_change", "fast_return", "last_value", "period", "period_offset"]
        filtered_outputs = [
            {**{k: v for k, v in item.items() if k in keep_keys}, "simulator": "dynawo"}
            for item in self._scada_outputs
        ]
        with open(inputs_file, "w") as f:
            json.dump(filtered_inputs, f, indent=4 if pretty_print else None)
        with open(outputs_file, "w") as f:
            json.dump(filtered_outputs, f, indent=4 if pretty_print else None)
        return mock_cyber_config


    def write_dynawo_curves(self, output_file: str | Path, pretty_print: bool=True):
        if self._outputs_variables is None:
            self._generate_variables()

        root = etree.Element("curvesInput", nsmap=DYNAWO_NSMAP)
        for v in self._outputs_variables:
            curve_elem = etree.SubElement(root, "curve", nsmap=DYNAWO_NSMAP)
            curve_elem.attrib["model"] = v["model"]
            curve_elem.attrib["variable"] = v["variable"]

        curves_tree = etree.ElementTree(root)
        curves_tree.write(output_file, pretty_print=pretty_print, xml_declaration=True, encoding='UTF-8')

    def write_dynawo_connectors(self, output_file: str | Path, pretty_print: bool=True):
        if self._outputs_variables is None:
            self._generate_variables()

        connector_tree = etree.ElementTree(self._dynawo_inputs_root)
        connector_tree.write(output_file, pretty_print=pretty_print, xml_declaration=True, encoding='UTF-8')

    @staticmethod
    def _is_lib_pattern(model_lib) -> bool:
        return isinstance(model_lib, str) and any(c in model_lib for c in LIB_PATTERN_CHARS)

    @staticmethod
    def find_rules(rule_set, iidm_class, model_lib):
        """
        Find the rules of a model in a rule set, in order:
          1. exact (null, model_lib) key: dynawo model config
          2. exact (iidm_class, model_lib) key: model defined in relation with iidm_class
          3. (null, pattern) then (iidm_class, pattern) keys, where pattern is a glob pattern (fnmatch, case sensitive,
             e.g. "HvdcVsc*") matching model_lib. Among the matching patterns, the most specific (longest) one wins,
             the first one in the file in case of a tie
          4. (iidm_class, "default") key: default Model Network component
        Returns None if no rule applies.
        """
        for key in [(None, model_lib), (iidm_class, model_lib)]:
            if key in rule_set:
                return rule_set[key]
        if model_lib is not None:
            for owner in [None, iidm_class]:
                patterns = [lib for (cls, lib) in rule_set
                            if cls == owner and Configurator._is_lib_pattern(lib) and fnmatch.fnmatchcase(model_lib, lib)]
                if len(patterns) > 0:
                    return rule_set[(owner, max(patterns, key=len))]
        return rule_set.get((iidm_class, "default"))

    def _generate_variables(self):
        self._inputs_variables = []
        self._outputs_variables = []
        for rule_set, in_or_out in zip([self._input_rules, self._output_rules], [InOrOut.IN, InOrOut.OUT]):
            for model_id, model in self.models.iterrows():
                cache_key = (in_or_out, model['iidm_class'], model['model_lib'])
                if cache_key not in self._rules_cache:  # Pattern matching is costly, and many models share their library
                    self._rules_cache[cache_key] = Configurator.find_rules(rule_set, model['iidm_class'], model['model_lib'])
                rules = self._rules_cache[cache_key]
                if rules is None:
                    print(f"MISSING {in_or_out} RULE FOR:  {(model['iidm_class'], model['model_lib'])}")
                    continue

                if in_or_out == InOrOut.IN:
                    self._inputs_variables.extend(self._generate_model_variables(rules, model, in_or_out))
                else:
                    self._outputs_variables.extend(self._generate_model_variables(rules, model, in_or_out))

        # Generate Dynawo inputs for input variables. Note that this will remove input variables for which Dynawo inputs cannot be added.
        self._generate_dynawo_inputs()

    @staticmethod
    def find_parameter_value(set_id: str, par_id: str, iidm_handler: IIDMHandler, dyd_handlers: list[DydHandler], par_handler: ParHandler) -> str:
        par_dict = par_handler.get_values(set_id)
        if par_id in par_dict:
            return par_dict[par_id]

        # Value not found, search a reference instead
        reference = par_handler.get_reference(set_id, par_id)
        if reference.attrib["origData"] != "IIDM":
            raise NotImplementedError(f"Parameter {par_id} in set {set_id} has unknown origin type {reference.attrib['origData']}")

        # The set may be referenced from any of the input dyd files.
        static_id = None
        for dyd_handler in dyd_handlers:
            for dyn_model in dyd_handler.get_dynamic_models_with_par_id(set_id):
                if dyn_model.get("staticId"):
                    static_id = dyn_model.attrib["staticId"]
                    break
            if static_id is not None:
                break

        if static_id is None:
            raise ValueError(f"Could not static id of references in parameter set {set_id}")

        return iidm_handler.resolve_reference(reference.attrib["origName"], static_id)

    def _generate_model_variables(self, rules, model, in_or_out: InOrOut, add_vl=True):
        model_variables = []
        for kindside, rule in rules.items():
            factor_possibilities = rule["factor"]
            mapping = rule["mapping"]
            variable = None

            # Resolve factor, factor can be either a single value or a list of references, keeping the first valid one
            if not isinstance(factor_possibilities, list):
                factor_possibilities = [factor_possibilities]
            factor = None

            for factor_possibility in factor_possibilities:
                try:
                    factor = float(factor_possibility)
                    break
                except ValueError:
                    parameter = str(factor_possibility)  # Factor not given as a constant float but by as a parameter or reference (typically PNom or SNom)
                    if parameter.startswith("iidm:"):
                        reference = parameter[len("iidm:"):]
                        static_id = model.get("static_id")
                        if static_id is None:
                            print(f"Warning model {model['dynamic_id']} of type {model['model_lib']} has factor as an IIDM reference, but no IIDM id")
                            continue
                        side = rule.get("side")
                        factor = self._iidm_handler.resolve_reference(reference, static_id, side)
                        break
                    else:
                        if model["model_lib"] is None:  # Pure IIDM model
                            raise ValueError("Factor must be float or iidm reference (start with iidm:)")
                        else:  # Dynamic model
                            par_file = model["par_file"]
                            par_id = model["par_id"]
                            try:
                                factor = Configurator.find_parameter_value(par_id, parameter, self._iidm_handler, self._dyd_handlers, self._par_handler_loader.get_handler(par_file))
                                factor = float(factor)
                                break
                            except ValueError:
                                continue

            if factor is None:
                raise RuntimeError(f"Could not resolve factor for {model} using rule {rule}")

            if model["model_lib"] is None:  # Pure IIDM model
                variable = {"model": "NETWORK",
                            "variable": mapping.replace("@ID@", model["static_id"])}
                if in_or_out == InOrOut.IN:
                    if kindside == "state":
                        variable["type"] = "integer"
                    else:
                        variable["type"] = "continuous"
                    if "type" in rule:
                        variable["type"] = rule["type"]
            else:  # Dynamic model
                is_parameter = False
                if in_or_out == InOrOut.IN:
                    model_data_variables = self._model_library.get_model_extvars(model["model_lib"])  # ExtVar control
                    var_name_type = self._find_entry_from_keywork(mapping, model_data_variables)
                    if var_name_type is None:
                        model_data_variables = self._model_library.get_model_parameters(model["model_lib"])  # Parameter control
                        var_name_type = self._find_entry_from_keywork(mapping, model_data_variables)
                        is_parameter = True
                else:
                    # Note: In classic dynawo simulation, curves of parameters are only updated when the simulation
                    #   terminates. A development in Dynawo is necessary to output the correct value for a parameter
                    #   during a simulation. No parameter output should be set before that.
                    model_data_variables = self._model_library.get_model_variables(model["model_lib"])
                    var_name_type = self._find_entry_from_keywork(mapping, model_data_variables)

                if var_name_type is not None:
                    var_name, var_type = var_name_type
                    variable = {"model": model["dynamic_id"],
                                "variable": var_name,
                                "model_lib": model["model_lib"],
                                "is_parameter": is_parameter}
                    if var_type is not None:  # Type only included for extvars, not all variables
                        variable["type"] = var_type

            # Inference of kind and side
            if variable is not None:
                variable["equipmentId"] = model["static_id"]
                if kindside[-1].isdigit():
                    variable["kind"] = kindside[:-1]
                    if kindside[-1] == "1":
                        if add_vl and model['voltage_level1'] is not None: variable['voltage_level'] = model['voltage_level1']
                        if add_vl and model['substation1'] is not None: variable['substation'] = model['substation1']
                        variable["side"] = "ONE"
                    elif kindside[-1] == "2":
                        if add_vl and model['voltage_level2'] is not None: variable['voltage_level'] = model['voltage_level2']
                        if add_vl and model['substation2'] is not None: variable['substation'] = model['substation2']
                        variable["side"] = "TWO"
                else:
                    variable["kind"] = kindside
                    if add_vl and model['voltage_level'] is not None: variable['voltage_level'] = model['voltage_level']
                    if add_vl and model['substation'] is not None: variable['substation'] = model['substation']

                # Add id, dynawo_id and topic
                if "substation" in variable:
                    topic = variable["substation"]
                elif model["model_lib"] is not None:
                    topic = model["model_lib"]
                else:
                    topic = model["static_id"]
                if model["iidm_class"] is not None: variable["iidm_class"] = model["iidm_class"]
                if in_or_out == InOrOut.OUT:
                    variable["topic"] = topic
                variable["dynawo_id"] = f"{variable['model']}_{variable['variable']}"
                variable["id"] = variable["dynawo_id"]
                variable["factor"] = factor
                model_variables.append(variable)
        # Check duplication errors
        non_uniques = [k for (k, v) in Counter([v["id"] for v in model_variables]).items() if v > 1]
        if len(non_uniques) > 0:
            raise RuntimeError(f"Error: found duplicated keys in model variables, check rules! \n {non_uniques}")
        return model_variables

    def _find_entry_from_keywork(self, mapping, model_data_variables) -> tuple[Any, Any] | None:
        if mapping.startswith("contains:"):
            keyword = mapping[len("contains:"):]
            var_name_type = next(
                ((v["name"], v.get("type")) for v in model_data_variables if keyword in v["name"].lower()), None)
        elif mapping.startswith("regex:"):
            pattern = mapping[len("regex:"):]
            var_name_type = next(
                ((v["name"], v.get("type")) for v in model_data_variables if re.match(pattern, v["name"])), None)
        else:
            var_name_type = next(
                ((v["name"], v.get("type")) for v in model_data_variables if v["name"] == mapping), None)
        return var_name_type

    def _generate_dynawo_inputs(self):
        existing_connections = [
            connection
            for dyd_handler in self._dyd_handlers
            for connection in dyd_handler.get_all_resolved_connections()
        ]
        used_connections = set()
        for connection in existing_connections:
            for side in [1, 2]:
                connection_name : str = connection.attrib[f"id{side}"] + "_" + connection.attrib[f"var{side}"]
                if connection_name.endswith("_value"):
                    # Can only have one connection to a given variable regardless whether it ends with _value or not
                    connection_name = connection_name[:-6]
                used_connections.add(connection_name)

        self._dynawo_inputs_root = etree.Element("dynamicModelsArchitecture", nsmap=DYNAWO_NSMAP)
        for v in self._inputs_variables.copy():
            if v.get("is_parameter", False):
                continue
            connector_elem = etree.Element("blackBoxModel", nsmap=DYNAWO_NSMAP)
            connector_elem.attrib["id"] = v["id"]
            connector_elem.attrib["lib"] = "DYNModelUpdatable" + v["type"].capitalize()

            connection_elem = etree.Element("connect", nsmap=DYNAWO_NSMAP)
            connection_elem.attrib["id1"] = v["id"]
            connection_elem.attrib["var1"] = "input_variable"
            connection_elem.attrib["id2"] = v["model"]
            connection_elem.attrib["var2"] = v["variable"]

            connection_name = v["model"] + "_" + v["variable"]
            if connection_name.endswith("_value"):
                connection_name = connection_name[:-6]

            if connection_name in used_connections:
                print(f"Warning: cannot add connection {connection_name} for input {v['id']}, conflicts with existing connection")
                self._inputs_variables.remove(v)
            else:
                self._dynawo_inputs_root.append(connector_elem)
                self._dynawo_inputs_root.append(connection_elem)
                used_connections.add(connection_name)

    def _generate_mock_scada_variables(self, cyber_config_file: str | Path, pretty_print: bool=True):
        """
        Generate mock SCADA inputs and outputs without any information about the SCADA infrastructure
        This is done by copying the dynawo I/O and setting their source as their substation (or topic
        if the substation is not defined) and destination as ROOT_CYBER_NODE_NAME (for outputs,
        reverse for inputs)
        """
        if self._outputs_variables is None:
            self._generate_variables()

        self._scada_inputs = copy.deepcopy(self._inputs_variables)
        self._scada_outputs = copy.deepcopy(self._outputs_variables)
        for input in self._scada_inputs:
            input["source"] = ROOT_CYBER_NODE_NAME
            input["destination"] = input.get("substation", ROOT_CYBER_NODE_NAME)
        for output in self._scada_outputs:
            output["source"] = output.get("substation", ROOT_CYBER_NODE_NAME)
            output["destination"] = ROOT_CYBER_NODE_NAME
            output["period"] = 1

        # Generate associated mock communications file
        network_json = {}
        network_json["links_characteristics_by_link_type"] = []
        network_json["links_characteristics_by_link_type"].append({
            "fromtype": "FAKE",
            "totype": "FAKE",
            "delay_function": {
                "type": "fixed",
                "delay": 0.1
            }
        })
        network_json["links"] = []
        substations = self._network.get_substations()
        for substation_id in substations.index:
            sender = substation_id
            receiver = ROOT_CYBER_NODE_NAME
            network_json["links"].append({"from": sender, "fromtype": "FAKE", "to": receiver, "totype": "FAKE"})
            # network_json["links"].append({"from": sender, "fromtype": "FAKE", "to": sender + "_1", "totype": "FAKE"})  # Multiple lines for performance testing
            # network_json["links"].append({"from": sender + "_1", "fromtype": "FAKE", "to": sender + "_2", "totype": "FAKE"})
            # network_json["links"].append({"from": sender + "_2", "fromtype": "FAKE", "to": sender + "_3", "totype": "FAKE"})
            # network_json["links"].append({"from": sender + "_3", "fromtype": "FAKE", "to": sender + "_4", "totype": "FAKE"})
            # network_json["links"].append({"from": sender + "_4", "fromtype": "FAKE", "to": receiver, "totype": "FAKE"})
        with open(cyber_config_file, "w") as f:
            json.dump(network_json, f, indent=4 if pretty_print else None)

    def get_inputs_by_iidm_key_map(self):
        if self._outputs_variables is None:
            self._generate_variables()

        input_variables_by_iidm_key = {}
        for input in self._inputs_variables:
            iidm_id = input.get("equipmentId")
            attribute = input.get("kind")
            side = alphabetic_side_to_numeric(input.get("side"))
            if iidm_id is not None and attribute is not None:
                iidm_key = iidm_id + ":" + attribute + side
                input_variables_by_iidm_key[iidm_key] = input
        return input_variables_by_iidm_key

    def get_outputs_by_iidm_key_map(self):
        if self._outputs_variables is None:
            self._generate_variables()
        output_variables_by_iidm_key = {}
        for output in self._outputs_variables:
            iidm_id = output.get("equipmentId")
            attribute = output.get("kind")
            side = alphabetic_side_to_numeric(output.get("side"))
            if iidm_id is not None and attribute is not None:
                iidm_key = iidm_id + ":" + attribute + side
                output_variables_by_iidm_key[iidm_key] = output
        return output_variables_by_iidm_key

    def _generate_scada_variables_from_config(self, communication_file, cyber_mapping_file):
        if self._outputs_variables is None:
            self._generate_variables()

        self._scada_inputs = []
        self._scada_outputs = []
        iidm_id_to_physical_type = get_iidm_id_to_physical_type_map(self._iidm_file)

        # Generate a mapping to find inputs/outputs from an iidm key (iidm_id:attribute, e.g. "line1:P2")
        input_variables_by_iidm_key = self.get_inputs_by_iidm_key_map()
        output_variables_by_iidm_key = self.get_outputs_by_iidm_key_map()

        communications = json.load(open(communication_file))
        links = communications["links"]

        rtus = set()
        for link in links:
            from_ = link["from"]
            to = link["to"]
            rtus.add(from_)
            rtus.add(to)

        ti_mapper = TiMapper(self._iidm_file, cyber_mapping_file)
        missing_rtus = set()
        # IIDM switch kind (BREAKER, DISCONNECTOR, LOAD_BREAK_SWITCH) decides which positions the
        # orchestrator anticipates on command (fast_return): breakers answer within a fraction of a
        # second in the real grid, disconnectors and tap changers are slow and follow the simulator.
        switch_kind_by_iidm_id = self._network.get_switches()["kind"].to_dict()

        total = {"TS": 0, "TC": 0, "TM": 0, "TVC": 0, "OM": 0}
        rtu_found = {"TS": 0, "TC": 0, "TM": 0, "TVC": 0, "OM": 0}
        iidm_found = {"TS": 0, "TC": 0, "TM": 0, "TVC": 0, "OM": 0}
        dynawo_found = {"TS": 0, "TC": 0, "TM": 0, "TVC": 0, "OM": 0}

        for telecontrol in ti_mapper.timappeds:
            type_ = telecontrol.get_type()
            total[type_] += 1

            rtu = telecontrol.get_rtu()
            if rtu is None:
                continue

            # Skip telecontrols with RTU not found in cyber config
            if rtu not in rtus:
                if rtu not in missing_rtus:
                    print(rtu, "not in known RTUs")
                    missing_rtus.add(rtu)
                continue
            rtu_found[type_] += 1

            iidm_id = telecontrol.get_iidm_id()
            if iidm_id is None:
                continue

            attribute = telecontrol.get_attribute()
            if attribute is None:
                continue

            physical_type = iidm_id_to_physical_type.get(iidm_id)
            if physical_type is None:
                continue
            iidm_found[type_] += 1

            iidm_key = telecontrol.get_iidm_key()
            if iidm_key is None:
                continue

            if type_ in ["TM", "TS"]:  # Output
                variables_by_iidm_key = output_variables_by_iidm_key
                scada_variables = self._scada_outputs
            elif type_ in ["TC", "TVC"]:  # Input
                variables_by_iidm_key = input_variables_by_iidm_key
                scada_variables = self._scada_inputs
            else:
                continue

            if iidm_key not in variables_by_iidm_key:
                if attribute == "state" and physical_type == "switch":
                    dynawo_found[type_] += 1  # Count non-retained breakers as found
                else:
                    # Don't print warning for non-retained breaker
                    if type_ in ["TM", "TS"]:  # Output
                        print(iidm_key, "not found in Dynawo outputs")
                    else:
                        print(iidm_key, "not found in Dynawo inputs")
                continue
            dynawo_found[type_] += 1

            element = copy.deepcopy(variables_by_iidm_key[iidm_key])
            if type_ in ["TM", "TS"]:  # Output
                element["source"] = rtu
                element["destination"] = ROOT_CYBER_NODE_NAME
            elif type_ in ["TC", "TVC"]:  # Input
                element["source"] = ROOT_CYBER_NODE_NAME
                element["destination"] = rtu

            if type_ == "TS":
                element["publish_on_change"] = True
                if attribute == "state" and physical_type == "switch":
                    element["fast_return"] = switch_kind_by_iidm_id.get(iidm_id) == "BREAKER"
            if type_ == "TM":
                element["period"] = 5

            tase2 = telecontrol.get_tase2()
            if tase2 is None:
                continue

            element["tase2"] = tase2

            scada_variables.append(element)

        print()
        print("Dynawo found: ", dynawo_found)
        print("IIDM found:   ", iidm_found)
        print("RTU found:    ", rtu_found)
        print("Total:        ", total)


    def get_unique_values(self,  col):
        return self.models[col].unique()

    def get_pure_dynamic_lib_list(self):
        return self.models[self.models["iidm_class"].isnull()]["model_lib"].unique()


    # @property
    # def models(self):
    #     return self._models
