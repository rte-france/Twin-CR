"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import json
from pathlib import Path

from configurator.configurator import Configurator
import configurator.asset_simulator_config_generator as AssetSimulatorConfigGenerator
from jobs_editor import JobsFile
from json_io import load_json

# Written by write_dynawo_connectors, and referenced from the jobs file so
# Dynawo loads it alongside the hand-written dyds.
CONNECTORS_DYD = "RTConnectors.dyd"

# Written by AssetSimulatorConfigGenerator when asked to generate one, next to the other outputs.
ASSET_SIMULATOR_CONFIG_NAME = "asset_simulator_config.json"

# Keys of an extra io file, i.e. the generated io files its entries are added to
EXTRA_IO_KINDS = ("game_master_inputs", "game_master_outputs", "scada_inputs", "scada_outputs")


def main(
        iidm_file, dyd_file, communication_file: str | Path | None,
        cyber_mapping_file: str | Path | None,
        pt_fige_file: str | Path | None,
        generate_asset_simulator_config: bool,
        substations_include_list: list[str],
        models_path: Path | str | None,
        pretty_print: bool=True,
        output_dir: str | Path = None,
        extra_rules_dir: str | Path | None = None,
        extra_io_file: str | Path | None = None
        ):
    if output_dir is None:
        output_dir = Path(iidm_file).parent
    configurator = Configurator(iidm_file, dyd_file, models_path, extra_rules_dir)
    suffix_mini = ""
    if len(substations_include_list) > 0:  # Mini outputs file for argus performance ==> add substations if needed
        configurator.models = configurator.models[configurator.models["substation"].isin(substations_include_list) |
                                                configurator.models["substation1"].isin(substations_include_list) |
                                                configurator.models["substation2"].isin(substations_include_list) |
                                                # Always include models without substation defined (e.g. OMEGA_REF)
                                                (configurator.models["substation"].isnull() & configurator.models["substation1"].isnull() & configurator.models["substation2"].isnull())]
        suffix_mini = "_mini"

    suffix_mapped = ""
    if communication_file is None or cyber_mapping_file is None:
        suffix_mapped = "_no_map"

    configurator.write_dynawo_inputs(output_dir / f"game_master_inputs{suffix_mini}.json", pretty_print)
    configurator.write_dynawo_outputs(output_dir / f"game_master_outputs{suffix_mini}.json", pretty_print)
    configurator.write_dynawo_curves(output_dir / f"curves{suffix_mini}.xml", pretty_print)
    configurator.write_dynawo_connectors(output_dir / f"RTConnectors{suffix_mini}.dyd", pretty_print)
    mock_cyber_config = configurator.write_scada_io(output_dir / f"scada_inputs{suffix_mini}{suffix_mapped}.json", output_dir / f"scada_outputs{suffix_mini}{suffix_mapped}.json", communication_file, cyber_mapping_file, pretty_print)

    if pt_fige_file is None:  # Use PtFigé iidm instead of the Dynawo iidm if specified as it has more accurate current limits (esp. for 3-windings tfos)
        pt_fige_file = iidm_file

    if generate_asset_simulator_config:
        generate_asset_simulator(output_dir, communication_file, cyber_mapping_file, pt_fige_file, suffix_mini, suffix_mapped)

    if extra_io_file is not None:
        add_extra_io(extra_io_file, output_dir, suffix_mini, suffix_mapped, pretty_print)

    return mock_cyber_config


def main_from_jobs(jobs_file: str | Path, models_path: Path | str | None = None,
                   communication_file: str | Path | None = None,
                   cyber_mapping_file: str | Path | None = None,
                   substations_include_list: list[str] | None = None,
                   pretty_print: bool = True, output_dir: str | Path | None = None,
                   period: float | str | None = None,
                   generate_asset_simulator_config: bool = False,
                   pt_fige_file: str | Path | None = None,
                   extra_rules_dir: str | Path | None = None,
                   extra_io_file: str | Path | None = None) -> tuple[str, str | None, str | None]:
    """
    Configure a context from its jobs file alone.

    The iidm and the input dyd files are read from the jobs file rather than
    passed in, so any valid jobs file works. The connectors file this generates
    is excluded from the inputs (it is an output, and is regenerated here) and
    is added to the jobs file if it is not referenced yet.

    Returns the generated connectors dyd, the generated mock cyber config when
    no real one was supplied, and the generated asset simulator config when one
    was asked for and could be built.
    """
    jobs_file = Path(jobs_file)
    working_dir = jobs_file.parent
    output_dir = Path(output_dir) if output_dir is not None else working_dir

    jobs = JobsFile(jobs_file)

    iidm_name = jobs.iidm_file()
    if not iidm_name:
        raise ValueError(f"{jobs_file.name} declares no iidmFile")

    suffix_mini = "_mini" if substations_include_list else ""
    generated_dyd = f"RTConnectors{suffix_mini}.dyd"
    input_dyds = [working_dir / name for name in jobs.dyd_files() if name != generated_dyd]
    if not input_dyds:
        raise ValueError(f"{jobs_file.name} declares no input dyd files")

    configurator = Configurator(working_dir / iidm_name, input_dyds, models_path, extra_rules_dir)
    if substations_include_list:
        configurator.models = configurator.models[
            configurator.models["substation"].isin(substations_include_list)
            | configurator.models["substation1"].isin(substations_include_list)
            | configurator.models["substation2"].isin(substations_include_list)
            # Always include models without substation defined (e.g. OMEGA_REF)
            | (configurator.models["substation"].isnull()
               & configurator.models["substation1"].isnull()
               & configurator.models["substation2"].isnull())
        ]

    suffix_mapped = "" if (communication_file and cyber_mapping_file) else "_no_map"

    configurator.write_dynawo_inputs(output_dir / f"game_master_inputs{suffix_mini}.json", pretty_print)
    configurator.write_dynawo_outputs(output_dir / f"game_master_outputs{suffix_mini}.json", pretty_print)
    configurator.write_dynawo_curves(output_dir / f"curves{suffix_mini}.xml", pretty_print)
    configurator.write_dynawo_connectors(output_dir / generated_dyd, pretty_print)
    mock_cyber_config = configurator.write_scada_io(
        output_dir / f"scada_inputs{suffix_mini}{suffix_mapped}.json",
        output_dir / f"scada_outputs{suffix_mini}{suffix_mapped}.json",
        communication_file, cyber_mapping_file, pretty_print,
    )

    if pt_fige_file is None:  # Use PtFigé iidm instead of the Dynawo iidm if specified as it has more accurate current limits (esp. for 3-windings tfos)
        pt_fige_file = working_dir / iidm_name

    asset_simulator_config = None
    if generate_asset_simulator_config:
        asset_simulator_config = generate_asset_simulator(
            output_dir, communication_file, cyber_mapping_file, pt_fige_file, suffix_mini, suffix_mapped)

    if extra_io_file is not None:
        add_extra_io(extra_io_file, output_dir, suffix_mini, suffix_mapped, pretty_print)

    changed = jobs.ensure_dyd(generated_dyd)
    if period is not None:
        changed |= jobs.ensure_interactive_settings(period)
    if changed:
        jobs.save()

    return (generated_dyd,
            mock_cyber_config.name if mock_cyber_config else None,
            asset_simulator_config.name if asset_simulator_config else None)


def generate_asset_simulator(output_dir: Path, communication_file: str | Path | None,
                             cyber_mapping_file: str | Path | None, pt_fige_file: str | Path,
                             suffix_mini: str, suffix_mapped: str) -> Path | None:
    """
    Write the asset simulator configuration, and add what it needs to the SCADA inputs and to the
    game master inputs.

    Returns the file written, or None when the cyber network and its mapping,
    which the telesignals to simulate are read from, are missing.
    """
    if communication_file is None or cyber_mapping_file is None:
        print("No asset simulator configuration generated: it needs both a cyber network and its mapping")
        return None

    asset_simulator_config = output_dir / ASSET_SIMULATOR_CONFIG_NAME
    AssetSimulatorConfigGenerator.generate(
        pt_fige_file,
        output_dir / f"game_master_outputs{suffix_mini}.json",
        communication_file, cyber_mapping_file,
        output_dir / f"scada_inputs{suffix_mini}{suffix_mapped}.json",
        asset_simulator_config,
        output_dir / f"game_master_inputs{suffix_mini}.json",
        output_dir / f"game_master_outputs{suffix_mini}.json",
        output_dir / f"scada_outputs{suffix_mini}{suffix_mapped}.json",
    )
    return asset_simulator_config


def add_extra_io(extra_io_file: str | Path, output_dir: Path, suffix_mini: str, suffix_mapped: str,
                 pretty_print: bool = True):
    """
    Add the entries of an extra io file to the generated game master and SCADA io files.

    The extra io file is a JSON object whose keys are EXTRA_IO_KINDS, each holding a list of entries in the
    format of the corresponding file, e.g. a SCADA input only used by a python automaton:
        {"scada_inputs": [{"id": "TCB_lock", "destination": "SCADA"}]}
    An unknown key, an entry without id or an id already in the generated file is an error.
    """
    extra_io = load_json(extra_io_file)
    if not isinstance(extra_io, dict):
        raise ValueError(f"{extra_io_file}: expected a JSON object with keys among {', '.join(EXTRA_IO_KINDS)}")
    unknown = sorted(set(extra_io) - set(EXTRA_IO_KINDS))
    if unknown:
        raise ValueError(f"{extra_io_file}: unknown keys {', '.join(unknown)}, expected keys among {', '.join(EXTRA_IO_KINDS)}")

    for kind, entries in extra_io.items():
        suffix = suffix_mini + (suffix_mapped if kind.startswith("scada") else "")
        io_file = Path(output_dir) / f"{kind}{suffix}.json"
        io = load_json(io_file)
        ids = {entry.get("id") for entry in io}
        for entry in entries:
            if "id" not in entry:
                raise ValueError(f"{extra_io_file}: {kind} entry without id: {entry}")
            if entry["id"] in ids:
                raise ValueError(f"{extra_io_file}: {kind} id {entry['id']} is already in {io_file.name}")
            io.append(entry)
            ids.add(entry["id"])
        with open(io_file, "w") as f:
            json.dump(io, f, indent=4 if pretty_print else None)


def parse_args():
    parser = argparse.ArgumentParser(description="Populate Curves file, and dynawo outputs files from iidm")
    parser.add_argument('--jobs', '-j', type=str, help="Path to the jobs file; the iidm and input dyd files are read from it")
    parser.add_argument('--iidm', '-i',  type=str, help=f"Path to the iidm file (ignored when --jobs is given)")
    parser.add_argument('--dyd', '-d',  type=str, help=f"Path to the DYD file (ignored when --jobs is given)")
    parser.add_argument('--models_path', '-m', type=str, default="../../../../simulators/dynawo/ddb", help="Path to dynawo model descriptions directory")
    parser.add_argument('--extra_rules_dir', type=str, help="Directory of input_rules.yaml/output_rules.yaml files merged over the default configurator rules (e.g. rules of the private models of --models_path)")
    parser.add_argument('--communications_file', type=str, help=f"Path to the cyber config file (optional, a fake cyber config will be generated if not specified)")
    parser.add_argument('--cyber_mapping_file', type=str, help=f"Path to the cyber mapping file (optional, a fake cyber config will be generated if not specified)")
    parser.add_argument('--pt_fige_file', type=str, help=f"Optional PtFigé iidm file used instead of the base iidm file in the asset simulator configuration generation")
    parser.add_argument('--generate_asset_simulator_config', action='store_true', help=f"Generate {ASSET_SIMULATOR_CONFIG_NAME} (needs the cyber network and its mapping)")
    parser.add_argument('--extra_io_file', type=str, help=f"Optional JSON file of entries to add to the generated io files (keys: {', '.join(EXTRA_IO_KINDS)})")
    parser.add_argument('--period', type=str, default=None, help="Master period; written to the jobs file's interactiveSettings couplingTimeStep")
    parser.add_argument('--pretty-print', action=argparse.BooleanOptionalAction, default=True, help='pretty_print')
    parser.add_argument('-s', '--substations_include_list', type=str, nargs='*', default=[], help='List of substations to include')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.jobs:
        main_from_jobs(args.jobs, args.models_path, args.communications_file, args.cyber_mapping_file,
                       args.substations_include_list, args.pretty_print,
                       period=args.period,
                       generate_asset_simulator_config=args.generate_asset_simulator_config,
                       pt_fige_file=args.pt_fige_file,
                       extra_rules_dir=args.extra_rules_dir, extra_io_file=args.extra_io_file)
    else:
        main(args.iidm, args.dyd, args.communications_file, args.cyber_mapping_file, args.pt_fige_file,
             args.generate_asset_simulator_config, args.substations_include_list, args.models_path, args.pretty_print,
             extra_rules_dir=args.extra_rules_dir, extra_io_file=args.extra_io_file)
