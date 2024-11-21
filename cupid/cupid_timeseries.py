#!/usr/bin/env python
"""
Main script for running timeseries specified in the configuration file.

This script sets up and runs timeseries according to the configurations
provided in the specified YAML configuration file.

Usage: cupid-timeseries [OPTIONS]

  Main engine to set up running timeseries.

Options:
  -s, --serial        Do not use LocalCluster objects
  -ts, --time-series  Run time series generation scripts prior to diagnostics
  -atm, --atmosphere  Run atmosphere component diagnostics  #TODO: should we set this up to run timeseries for just atm?
  -ocn, --ocean       Run ocean component diagnostics
  -lnd, --land        Run land component diagnostics
  -ice, --seaice      Run sea ice component diagnostics
  -glc, --landice     Run land ice component diagnostics
  -rof, --river-runoff Run river runoff component diagnostics
  -config_path        Path to the YAML configuration file containing specifications for notebooks (default: config.yml)
  -h, --help          Show this message and exit.
"""
from __future__ import annotations

import os

import click

import cupid.timeseries
import cupid.util

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# fmt: off
# pylint: disable=line-too-long


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--serial", "-s", is_flag=True, help="Do not use LocalCluster objects")
# Options to turn components on or off
@click.option("--atmosphere", "-atm", is_flag=True, help="Run atmosphere component diagnostics")
@click.option("--ocean", "-ocn", is_flag=True, help="Run ocean component diagnostics")
@click.option("--land", "-lnd", is_flag=True, help="Run land component diagnostics")
@click.option("--seaice", "-ice", is_flag=True, help="Run sea ice component diagnostics")
@click.option("--landice", "-glc", is_flag=True, help="Run land ice component diagnostics")
@click.option("--river-runoff", "-rof", is_flag=True, help="Run river runoff component diagnostics")
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
    control = cupid.util.get_control_dict(config_path)
    cupid.util.setup_book(config_path)
    logger = cupid.util.setup_logging(config_path)

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
        # all = True
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
            # -----
            if isinstance(timeseries_params["case_name"], list):
                ts_input_dirs = []
                for cname in timeseries_params["case_name"]:
                    ts_input_dirs.append(global_params["CESM_output_dir"]+"/"+cname+f"/{component}/hist/")
            else:
                ts_input_dirs = [
                    global_params["CESM_output_dir"] + "/" +
                    timeseries_params["case_name"] + f"/{component}/hist/",
                ]

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
            cupid.timeseries.create_time_series(
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
