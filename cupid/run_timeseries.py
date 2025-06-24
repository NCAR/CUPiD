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

import os

import click

try:
    import timeseries
    import util
except ModuleNotFoundError:
    import cupid.timeseries as timeseries
    import cupid.util as util

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
        if comp_bool:

            # set time series input and output directory:
            # if timeseries params contain a list make a list of input directories, or make  one input directory
            # if ts_dir is specified and contains a list make a list of output dirs; or make just one output dir
            # if ts_dir is not specified, default to CESM_output_dir for either a list or a single value
            # -----
            if isinstance(timeseries_params["case_name"], list):
                ts_input_dirs = []
                for cname in timeseries_params["case_name"]:
                    if cname == global_params["base_case_name"] and "base_case_output_dir" in global_params:
                        ts_input_dirs.append(global_params["base_case_output_dir"]+"/"+cname+f"/{component}/hist/")
                    else:
                        ts_input_dirs.append(global_params["CESM_output_dir"]+"/"+cname+f"/{component}/hist/")
            else:
                ts_input_dirs = [
                    global_params["CESM_output_dir"] + "/" +
                    timeseries_params["case_name"] + f"/{component}/hist/",
                ]


            if "ts_dir" in global_params and global_params["ts_dir"] is None:
                if isinstance(global_params["ts_dir"], list):
                    ts_output_dirs = []
                    for cname in timeseries_params["case_name"]:
                        ts_output_dirs.append([
                            os.path.join(
                                    global_params["ts_dir"],
                                    cname,
                                    f"{component}", "proc", "tseries",
                            ),
                        ])
                else:
                    ts_output_dirs = [
                        os.path.join(
                                global_params["ts_dir"],
                                timeseries_params["case_name"],
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
            timeseries.create_time_series(
                component,
                timeseries_params[component]["vars"],
                timeseries_params[component]["derive_vars"],
                timeseries_params["case_name"],
                timeseries_params[component]["hist_str"],
                ts_input_dirs,
                ts_output_dirs,
                # Note that timeseries output will eventually go in
                #   /glade/derecho/scratch/${USER}/archive/${CASE}/${component}/proc/tseries/
                timeseries_params["ts_done"],
                timeseries_params["overwrite_ts"],
                timeseries_params[component]["start_years"],
                timeseries_params[component]["end_years"],
                timeseries_params[component]["level"],
                num_procs,
                serial,
                logger,
            )
            # fmt: on
            # pylint: enable=line-too-long

    return None


if __name__ == "__main__":
    run_timeseries()
