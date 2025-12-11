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
import shutil

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
    file_mode = timeseries_params["file_mode"]
    dir_mode = timeseries_params["dir_mode"]
    file_group = timeseries_params["file_group"]
    dir_group = timeseries_params["dir_group"]

    # Get GID from group name
    file_gid = shutil._get_gid(file_group)
    if file_gid is None:
        file_gid = 1017
        # Or raise an exception because file_group is not defined on this machine
    dir_gid = shutil._get_gid(dir_group)
    if dir_gid is None:
        dir_gid = 1017
        # Or raise an exception because dir_group is not defined on this machine

    # Make file and dir modes octal
    fmode = int(str(file_mode), base=8)
    dmode = int(str(dir_mode), base=8)

    for component, comp_bool in component_options.items():
        if comp_bool:
            # set time series input and output directory or directories:
            # INPUT ts dir:
            #    if timeseries params contain a list of cases, make a list of input directories
            #        if not, make one input ts directory
            # OUTPUT ts dir:
            #    if ts_dir is specified and there is a list of cases, make a list of output dirs;
            #        if not, make one output ts dir
            #    if ts_dir is not specified, default to CESM_output_dir for either a list or a single value

            # if there is a list of case names, create a list of ts input directories
            if isinstance(timeseries_params["case_name"], list):
                ts_input_dirs = []
                for cname in timeseries_params["case_name"]:
                    # use base_case_output_dir for the base case if it exists
                    if cname == global_params["base_case_name"] and "base_case_output_dir" in global_params:
                        ts_input_dirs.append(global_params["base_case_output_dir"]+"/"+cname+f"/{component}/hist/")
                    # otherwise use the CESM_output_dir as a default
                    else:
                        ts_input_dirs.append(global_params["CESM_output_dir"]+"/"+cname+f"/{component}/hist/")
            # if there is not a list of case names, just use a single CESM_output_dir to find all of the ts_input_dirs
            else:
                ts_input_dirs = [
                    global_params["CESM_output_dir"] + "/" +
                    timeseries_params["case_name"] + f"/{component}/hist/",
                ]

            # if ts_dir is specified, use it to determine where the timeseries files should be written
            if "ts_dir" in global_params and global_params["ts_dir"] is not None:
                # if there is a list of cases, create a list of timeseries output dirs
                if isinstance(timeseries_params["case_name"], list):
                    ts_output_dirs = []
                    for cname in timeseries_params["case_name"]:
                        ts_output_dirs.append(
                            os.path.join(
                                    global_params["ts_dir"],
                                    cname,
                                    f"{component}", "proc", "tseries",
                            ),
                        )
                # if there is a single case, just create one output directory using ts_dir
                else:
                    ts_output_dirs = [
                        os.path.join(
                                global_params["ts_dir"],
                                timeseries_params["case_name"],
                                f"{component}", "proc", "tseries",
                        ),
                    ]
            # if ts_dir is not specified or is null, use CESM_output_dir to determine where to write timeseries files
            else:
                # for a list of cases, use the CESM_output_dir to write a list of output ts directories
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
                # for a single case, use the CESM_output_dir to write a list of one ts output dir
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
                timeseries_params["ts_done"],
                timeseries_params["overwrite_ts"],
                timeseries_params[component]["start_years"],
                timeseries_params[component]["end_years"],
                timeseries_params[component]["level"],
                num_procs,
                serial,
                logger,
                fmode,
                dmode,
                file_gid,
                dir_gid,
            )
            # fmt: on
            # pylint: enable=line-too-long

    return None


if __name__ == "__main__":
    run_timeseries()
