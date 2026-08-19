#!/usr/bin/env python
"""
Main script for running timeseries specified in the configuration file.

This script sets up and runs timeseries according to the configurations
provided in the specified YAML configuration file.

Usage: run_timeseries.py [OPTIONS] [CONFIG_PATH]

  Main engine to set up running all the notebooks.

  Args:     CONFIG_PATH: str, path to configuration file (default config.yml)

  Returns:     None

Options:
  -s, --serial          Do not use multiprocessing to run ncrcat in parallel
  -atm, --atmosphere    Run atmosphere component timeseries
  -ocn, --ocean         Run ocean component timeseries
  -lnd, --land          Run land component timeseries
  -ice, --seaice        Run sea ice component timeseries
  -glc, --landice       Run land ice component timeseries
  -rof, --river-runoff  Run river runoff component timeseries
  -h, --help            Show this message and exit.
"""
from __future__ import annotations

import logging

import click
from gents.hfcollection import HFCollection
from gents.timeseries import TSCollection
from gents.utils import enable_logging

try:
    import util
except ModuleNotFoundError:
    import cupid.util as util

logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# fmt: off
# pylint: disable=line-too-long


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--serial", "-s", is_flag=True, help="Do not use multiprocessing to run ncrcat in parallel")
# Options to turn components on or off
@click.option("--atmosphere", "-atm", is_flag=True, help="Run atmosphere component timeseries")
@click.option("--ocean", "-ocn", is_flag=True, help="Run ocean component timeseries")
@click.option("--land", "-lnd", is_flag=True, help="Run land component timeseries")
@click.option("--seaice", "-ice", is_flag=True, help="Run sea ice component timeseries")
@click.option("--landice", "-glc", is_flag=True, help="Run land ice component timeseries")
@click.option("--river-runoff", "-rof", is_flag=True, help="Run river runoff component timeseries")
@click.argument("config_path", default="config.yml")
def run_timeseries(
    config_path,
    serial=False,
    atmosphere=False,
    ocean=False,
    land=False,
    seaice=False,
    landice=False,
    river_runoff=False,
):
    """
    Main engine to set up running all the notebooks.

    Args:
        CONFIG_PATH: str, path to configuration file (default config.yml)

    Returns:
        None

    """
    # fmt: on
    # pylint: enable=line-too-long
    # Get control structure
    control = util.get_control_dict(config_path)
    util.setup_book(config_path)
    logger = util.setup_logging(config_path)

    #####################################################################
    # Managing global parameters

    global_params = dict()

    if "global_params" in control:
        global_params = control["global_params"]

    global_params["serial"] = serial

    ####################################################################

    enable_logging(verbose=True)
    timeseries_params = control["timeseries"]

    inclusive_path_filters = []
    inclusive_variable_filters = {}

    component_run_flags = {
        "atm": atmosphere,
        "ocn": ocean,
        "lnd": land,
        "ice": seaice,
        "glc": landice,
        "rof": river_runoff,
    }
    for comp_name in component_run_flags.keys():
        if component_run_flags[comp_name]:
            path_glob = f"*/{comp_name}/hist*{timeseries_params[comp_name]['hist_str']}*"
            inclusive_path_filters.append(path_glob)
            inclusive_variable_filters[path_glob] = timeseries_params[comp_name]['vars']

    # Force serial for now (we can update this later to plug into Dask or use
    #    Python's standard library multiprocessing)
    serial = True

    if serial:
        num_processes = 1
    else:
        num_processes = timeseries_params["num_procs"]

    if global_params["ts_dir"] is None:
        ts_output_dir = global_params["CESM_output_dir"]
    else:
        ts_output_dir = global_params["ts_dir"]

    for case_index, case_name in enumerate(timeseries_params["case_name"]):
        case_hfc = HFCollection(global_params["CESM_output_dir"] + "/" + case_name, num_processes=num_processes)
        case_hfc = case_hfc.include(inclusive_path_filters).exclude("*/proc/*")

        for comp_name in component_run_flags.keys():
            if not component_run_flags[comp_name]:
                continue
            comp_config = timeseries_params[comp_name]

            if "start_years" in comp_config and "end_years" in comp_config:
                case_hfc = case_hfc.include_years(
                    start_year=comp_config["start_years"][case_index],
                    end_year=comp_config["end_years"][case_index],
                    glob_patterns=f"*{comp_config["hist_str"]}*",
                )

        case_hfc = case_hfc.slice_groups(slice_size_years=5)
        case_tsc = TSCollection(case_hfc, ts_output_dir, num_processes=num_processes)

        if timeseries_params["overwrite_ts"][case_index]:
            case_tsc = case_tsc.apply_overwrite("*")

        for path_glob in inclusive_variable_filters:
            for variable_name in inclusive_variable_filters[path_glob]:
                target_tsc = case_tsc.include(path_glob, variable_name)
                # This is definitely less clean than I would like it to be, but GenTS currently doesn't support
                # filtering by a *list* of target variables, so for now we will execute one at a time.
                # This may introduce some latency and prevents parallelism (okay for now).
                if len(target_tsc) == 0:
                    head_dir = global_params["CESM_output_dir"] + "/" + case_name
                    logger.warning(
                        f"No history files found for '{variable_name}' in '{head_dir}' matching '{path_glob}'",
                    )
                else:
                    target_tsc.execute()  # Generate time series for this target variable.

    return None


if __name__ == "__main__":
    run_timeseries()
