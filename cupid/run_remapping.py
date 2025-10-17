#!/usr/bin/env python
"""
Main script for remapping timeseries as specified in the configuration file.

This script sets up and runs the remapping of  timeseries according to the
configurations provided in the specified YAML configuration file.

Usage: run_remapping.py [OPTIONS] [CONFIG_PATH]

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

import os

import click

try:
    import remapping
    import util
except ModuleNotFoundError:
    import cupid.remapping as remapping
    import cupid.util as util

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# fmt: off
# pylint: disable=line-too-long


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--serial", "-s", is_flag=True, help="Do not use multiprocessing to run ncremap in parallel")
# Options to turn components on or off
@click.option("--atmosphere", "-atm", is_flag=True, help="Remap atmosphere component timeseries")
@click.option("--ocean", "-ocn", is_flag=True, help="Remap ocean component timeseries")
@click.option("--land", "-lnd", is_flag=True, help="Remap land component timeseries")
@click.option("--seaice", "-ice", is_flag=True, help="Remap sea ice component timeseries")
@click.option("--landice", "-glc", is_flag=True, help="Remap land ice component timeseries")
@click.option("--river-runoff", "-rof", is_flag=True, help="Remap river runoff component timeseries")
@click.argument("config_path", default="config.yml")
def run_remapping(
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

    component_options = {
        "atm": atmosphere,
        "ocn": ocean,
        "lnd": land,
        "ice": seaice,
        "glc": landice,
        "rof": river_runoff,
    }

    # Automatically run all if no components specified

    if True not in [atmosphere, ocean, land, seaice, landice, river_runoff]:
        for key in component_options.keys():
            component_options[key] = True

    run_any = False
    for key in component_options:
        if component_options[key]:
            run_any = run_any or 'mapping_file' in control["timeseries"][key]
    if not run_any:
        print("Note: none of the requested components have mapping_file defined")
        print("      this means no time series files will be remapped")

    #####################################################################
    # Managing global parameters

    global_params = dict()

    if "global_params" in control:
        global_params = control["global_params"]

    global_params["serial"] = serial

    ####################################################################

    timeseries_params = control["timeseries"]

    # general timeseries arguments for all components
    num_procs = timeseries_params["num_procs"]

    for component, comp_bool in component_options.items():
        if comp_bool and "mapping_file" in timeseries_params[component]:

            if "ts_output_dir" in timeseries_params:
                if isinstance(timeseries_params["ts_output_dir"], list):
                    ts_output_dirs = []
                    for ts_outdir in timeseries_params["ts_output_dir"]:
                        ts_output_dirs.append([
                            os.path.join(
                                    ts_outdir,
                                    f"{component}", "proc", "tseries",
                            ),
                        ])
                else:
                    ts_output_dirs = [
                        os.path.join(
                                timeseries_params["ts_output_dir"],
                                f"{component}", "proc", "tseries",
                        ),
                    ]
            else:
                if isinstance(timeseries_params["case_name"], list):
                    ts_output_dirs = []
                    for cname in timeseries_params["case_name"]:
                        ts_output_dirs.append(
                            os.path.join(
                                    global_params["CESM_output_dir"],
                                    cname,
                                    f"{component}", "proc", "tseries",
                            ),
                        )
                else:
                    ts_output_dirs = [
                        os.path.join(
                                global_params["CESM_output_dir"],
                                timeseries_params["case_name"],
                                f"{component}", "proc", "tseries",
                        ),
                    ]
            # -----

            # fmt: off
            # pylint: disable=line-too-long
            remapping.remap_time_series(
                component,
                timeseries_params[component]["vars"],
                timeseries_params["case_name"],
                timeseries_params[component]["hist_str"], # TODO: maybe we just call this twice-- once for base case & once for case?
                ts_output_dirs,
                timeseries_params[component]["mapping_file"],
                num_procs,
                serial,
                logger,
            )
            # fmt: on
            # pylint: enable=line-too-long

    return None


if __name__ == "__main__":
    run_remapping()
