#!/usr/bin/env python
"""
Main script for running all notebooks and scripts specified in the configuration file.

This script sets up and runs all the specified notebooks and scripts according to the configurations
provided in the specified YAML configuration file.

Usage: cupid-run [OPTIONS]

  Main engine to set up running all the notebooks.

Options:
  -s, --serial        Do not use LocalCluster objects
  -ts, --time-series  Run time series generation scripts prior to diagnostics
  -atm, --atmosphere  Run atmosphere component diagnostics
  -ocn, --ocean       Run ocean component diagnostics
  -lnd, --land        Run land component diagnostics
  -ice, --seaice      Run sea ice component diagnostics
  -glc, --landice     Run land ice component diagnostics
  -config_path        Path to the YAML configuration file containing specifications for notebooks (default: config.yml)
  -h, --help          Show this message and exit.
"""
from __future__ import annotations

import os
import warnings

import click
import intake
import ploomber

import cupid.timeseries
import cupid.util

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# fmt: off
# pylint: disable=line-too-long


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--serial", "-s", is_flag=True, help="Do not use LocalCluster objects")
@click.option("--time-series", "-ts", is_flag=True, help="Run time series generation scripts prior to diagnostics")
# Options to turn components on or off
@click.option("--atmosphere", "-atm", is_flag=True, help="Run atmosphere component diagnostics")
@click.option("--ocean", "-ocn", is_flag=True, help="Run ocean component diagnostics")
@click.option("--land", "-lnd", is_flag=True, help="Run land component diagnostics")
@click.option("--seaice", "-ice", is_flag=True, help="Run sea ice component diagnostics")
@click.option("--landice", "-glc", is_flag=True, help="Run land ice component diagnostics")
@click.argument("config_path", default="config.yml")
def run(
    config_path,
    serial=False,
    time_series=False,
    all=False,
    atmosphere=False,
    ocean=False,
    land=False,
    seaice=False,
    landice=False,
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

    component_options = {
        "atm": atmosphere,
        "ocn": ocean,
        "lnd": land,
        "ice": seaice,
        "glc": landice,
    }

    # Automatically run all if no components specified

    if True not in [atmosphere, ocean, land, seaice, landice]:
        all = True
        for key in component_options.keys():
            component_options[key] = True

    #####################################################################
    # Managing global parameters

    global_params = dict()

    if "global_params" in control:
        global_params = control["global_params"]

    global_params["serial"] = serial

    ####################################################################

    if time_series:
        timeseries_params = control["timeseries"]

        # general timeseries arguments for all components
        num_procs = timeseries_params["num_procs"]

        for component, comp_bool in component_options.items():
            if comp_bool:

                # set time series output directory:
                #-----
                ts_output_dir = [os.path.join(global_params["CESM_output_dir"],
                                              timeseries_params["case_name"],
                                              f"/{component}/proc/tseries/")]

                if "ts_output_dir" in timeseries_params:
                    ts_output_dir = [os.path.join(timeseries_params["ts_output_dir"],
                                                  f"{component}/proc/tseries/")]
                #-----

                # fmt: off
                # pylint: disable=line-too-long
                cupid.timeseries.create_time_series(
                    component,
                    timeseries_params[component]["vars"],
                    timeseries_params[component]["derive_vars"],
                    [timeseries_params["case_name"]],
                    timeseries_params[component]["hist_str"],
                    [global_params["CESM_output_dir"]+"/"+timeseries_params["case_name"]+f"/{component}/hist/"],
                    ts_output_dir,
                    # Note that timeseries output will eventually go in
                    #   /glade/derecho/scratch/${USER}/archive/${CASE}/${component}/proc/tseries/
                    timeseries_params["ts_done"],
                    timeseries_params["overwrite_ts"],
                    timeseries_params[component]["start_years"],
                    timeseries_params[component]["end_years"],
                    timeseries_params[component]["level"],
                    num_procs,
                    serial,
                )
                # fmt: on
                # pylint: enable=line-too-long

    # Grab paths

    run_dir = os.path.realpath(os.path.expanduser(control["data_sources"]["run_dir"]))
    output_dir = run_dir + "/computed_notebooks/" + control["data_sources"]["sname"]
    temp_data_path = run_dir + "/temp_data"
    nb_path_root = os.path.realpath(
        os.path.expanduser(control["data_sources"]["nb_path_root"]),
    )

    #####################################################################
    # Managing catalog-related stuff

    # Access catalog if it exists

    cat_path = None

    if "path_to_cat_json" in control["data_sources"]:
        full_cat_path = os.path.realpath(
            os.path.expanduser(control["data_sources"]["path_to_cat_json"]),
        )
        full_cat = intake.open_esm_datastore(full_cat_path)

        # Doing initial subsetting on full catalog, e.g. to only use certain cases

        if "subset" in control["data_sources"]:
            first_subset_kwargs = control["data_sources"]["subset"]
            cat_subset = full_cat.search(**first_subset_kwargs)
            # This pulls out the name of the catalog from the path
            cat_subset_name = full_cat_path.split("/")[-1].split(".")[0] + "_subset"
            cat_subset.serialize(
                directory=temp_data_path, name=cat_subset_name, catalog_type="file",
            )
            cat_path = temp_data_path + "/" + cat_subset_name + ".json"
        else:
            cat_path = full_cat_path

    #####################################################################
    # Ploomber - making a DAG

    dag = ploomber.DAG(executor=ploomber.executors.Serial())

    #####################################################################
    # Organizing notebooks to run

    if "compute_notebooks" in control:

        all_nbs = dict()

        # pylint: disable=invalid-name
        for nb, info in control["compute_notebooks"]["infrastructure"].items():
            all_nbs[nb] = info
            all_nbs[nb]["nb_path_root"] = nb_path_root + "/infrastructure"
            all_nbs[nb]["output_dir"] = output_dir + "/infrastructure"

        for comp_name, comp_bool in component_options.items():
            if comp_name in control["compute_notebooks"] and comp_bool:
                for nb, info in control["compute_notebooks"][comp_name].items():
                    all_nbs[nb] = info
                    all_nbs[nb]["nb_path_root"] = nb_path_root + "/" + comp_name
                    all_nbs[nb]["output_dir"] = output_dir + "/" + comp_name
            elif comp_bool and not all:
                warnings.warn(
                    f"No notebooks for {comp_name} component specified in config file.",
                )

        # Checking for existence of environments

        for nb, info in all_nbs.copy().items():
            if not control["env_check"][info["kernel_name"]]:
                bad_env = info["kernel_name"]
                warnings.warn(
                    f"Environment {bad_env} specified for {nb}.ipynb could not be found;" +
                    f" {nb}.ipynb will not be run." +
                    "See README.md for environment installation instructions.",
                )
                all_nbs.pop(nb)

        # Setting up notebook tasks

        for nb, info in all_nbs.items():
            cupid.util.create_ploomber_nb_task(
                nb,
                info,
                cat_path,
                info["nb_path_root"],
                info["output_dir"],
                global_params,
                dag,
                dependency=info.get("dependency"),
            )

    #####################################################################
    # Organizing scripts

    if "compute_scripts" in control:

        all_scripts = dict()

        for comp_name, comp_bool in component_options.items():
            if comp_name in control["compute_scripts"] and comp_bool:
                for script, info in control["compute_scripts"][comp_name].items():
                    all_scripts[script] = info
                    all_scripts[script]["nb_path_root"] = nb_path_root + "/" + comp_name
            elif comp_bool and not all:
                warnings.warn(
                    f"No scripts for {comp_name} component specified in config file.",
                )

        # Checking for existence of environments

        for script, info in all_scripts.copy().items():
            if not control["env_check"][info["kernel_name"]]:
                bad_env = info["kernel_name"]
                warnings.warn(
                    f"Environment {bad_env} specified for {script}.py could not be found;" +
                    f"{script}.py will not be run.",
                )
                all_scripts.pop(script)

        # Setting up script tasks

        for script, info in all_scripts.items():
            cupid.util.create_ploomber_script_task(
                script,
                info,
                cat_path,
                info["nb_path_root"],
                global_params,
                dag,
                dependency=info.get("dependency"),
            )

    # Run the full DAG

    dag.build()

    return None
