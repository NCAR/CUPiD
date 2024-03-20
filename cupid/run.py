#!/usr/bin/env python

import click
import os
from glob import glob
import papermill as pm
import intake
import cupid.util
import cupid.timeseries
from dask.distributed import Client
import dask
import time
import ploomber
import yaml

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--serial", "-s", is_flag=True, help="Do not use LocalCluster objects")
@click.option(
    "--time-series",
    "-ts",
    is_flag=True,
    help="Run time series generation scripts prior to diagnostics",
)
@click.argument("config_path")
def run(config_path, serial=False, time_series=False):
    """
    Main engine to set up running all the notebooks.
    """

    # Get control structure
    control = cupid.util.get_dict(config_path)
    cupid.util.setup_book(config_path)

   #####################################################################
    # Managing global parameters

    global_params = dict()

    if "global_params" in control:
        global_params = control["global_params"]
    ####################################################################

    if time_series:
        timeseries_params = control["timeseries"]

        # general timeseries arguments for all components
        num_procs = timeseries_params["num_procs"]

        print("calling atm timeseries generation")
        # atm timeseries generation
        cupid.timeseries.create_time_series(
            "cam",
            timeseries_params["atm_vars"],
            timeseries_params["derive_vars_cam"],
            [timeseries_params["case_name"]],  # could also grab from compute_notebooks section of config file
            timeseries_params["atm_hist_str"],
            [global_params["CESM_output_dir"] + "/" + timeseries_params["case_name"] + "/atm/hist/"],  # could also grab from compute_notebooks section of config file
            [global_params["CESM_output_dir"]+'/'+timeseries_params['case_name']+'/atm/proc/tseries/'],
            # Note that timeseries output will eventually go in /glade/derecho/scratch/${USER}/archive/${CASE}/${component}/proc/tseries/
            timeseries_params["ts_done"],
            timeseries_params["overwrite_ts"],
            timeseries_params["atm_start_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.start_date
            timeseries_params["atm_end_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.end_date
            "lev",
            num_procs,
            serial,
        )

        print("calling lnd timeseries generation")
        # lnd timeseries generation
        cupid.timeseries.create_time_series(
            "lnd",
            timeseries_params["lnd_vars"],
            timeseries_params["derive_vars_lnd"],
            [timeseries_params["case_name"]],  # could also grab from compute_notebooks section of config file
            timeseries_params["lnd_hist_str"],
            [global_params["CESM_output_dir"] + "/" + timeseries_params["case_name"] + "/lnd/hist/"],  # could also grab from compute_notebooks section of config file
            [global_params["CESM_output_dir"]+'/'+timeseries_params['case_name']+'/lnd/proc/tseries/'],
            # Note that timeseries output will eventually go in /glade/derecho/scratch/${USER}/archive/${CASE}/${component}/proc/tseries/
            timeseries_params["ts_done"],
            timeseries_params["overwrite_ts"],
            timeseries_params["lnd_start_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.start_date
            timeseries_params["lnd_end_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.end_date
            "lev", # TODO: land group will need to change this!
            num_procs,
            serial,
        )

        print("calling ocn timeseries generation")
        # ocn timeseries generation
        cupid.timeseries.create_time_series(
            "ocn",
            timeseries_params["ocn_vars"],
            timeseries_params["derive_vars_ocn"],
            [timeseries_params["case_name"]],  # could also grab from compute_notebooks section of config file
            timeseries_params["ocn_hist_str"],
            [global_params["CESM_output_dir"] + "/" + timeseries_params["case_name"] + "/ocn/hist/"],  # could also grab from compute_notebooks section of config file
            [global_params["CESM_output_dir"]+'/'+timeseries_params['case_name']+'/ocn/proc/tseries/'],
            # Note that timeseries output will eventually go in /glade/derecho/scratch/${USER}/archive/${CASE}/${component}/proc/tseries/
            timeseries_params["ts_done"],
            timeseries_params["overwrite_ts"],
            timeseries_params["ocn_start_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.start_date
            timeseries_params["ocn_end_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.end_date
            "lev", # TODO: ocean group will need to change this!
            num_procs,
            serial,
        )

        print("calling ice timeseries generation")
        # ice timeseries generation
        cupid.timeseries.create_time_series(
            "ice",
            timeseries_params["ice_vars"],
            timeseries_params["derive_vars_ice"],
            [timeseries_params["case_name"]],  # could also grab from compute_notebooks section of config file
            timeseries_params["ice_hist_str"],
            [global_params["CESM_output_dir"] + "/" + timeseries_params["case_name"] + "/ice/hist/"],  # could also grab from compute_notebooks section of config file
            [global_params["CESM_output_dir"]+'/'+timeseries_params['case_name']+'/ice/proc/tseries/'],
            # Note that timeseries output will eventually go in /glade/derecho/scratch/${USER}/archive/${CASE}/${component}/proc/tseries/
            timeseries_params["ts_done"],
            timeseries_params["overwrite_ts"],
            timeseries_params["ice_start_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.start_date
            timeseries_params["ice_end_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.end_date
            "lev", # TODO: ice group will need to change this!
            num_procs,
            serial,
        )

        print("calling glc timeseries generation")
        # glc timeseries generation
        cupid.timeseries.create_time_series(
            "glc",
            timeseries_params["glc_vars"],
            timeseries_params["derive_vars_glc"],
            [timeseries_params["case_name"]],  # could also grab from compute_notebooks section of config file
            timeseries_params["glc_hist_str"],
            [global_params["CESM_output_dir"] + "/" + timeseries_params["case_name"] + "/glc/hist/"],  # could also grab from compute_notebooks section of config file
            [global_params["CESM_output_dir"]+'/'+timeseries_params['case_name']+'/glc/proc/tseries/'],
            # Note that timeseries output will eventually go in /glade/derecho/scratch/${USER}/archive/${CASE}/${component}/proc/tseries/
            timeseries_params["ts_done"],
            timeseries_params["overwrite_ts"],
            timeseries_params["glc_start_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.start_date
            timeseries_params["glc_end_years"],  # could get from yaml file in adf_quick_run.parameter_groups.none.config_fil_str, or for other notebooks config files, eg ocean_surface.parameter_gropus.none.mom6_tools_config.end_date
            "lev", # TODO: glc group will need to change this!
            num_procs,
            serial,
        )

    # Grab paths

    run_dir = os.path.realpath(os.path.expanduser(control["data_sources"]["run_dir"]))
    output_dir = run_dir + "/computed_notebooks/" + control["data_sources"]["sname"]
    temp_data_path = run_dir + "/temp_data"
    nb_path_root = os.path.realpath(
        os.path.expanduser(control["data_sources"]["nb_path_root"])
    )

    #####################################################################
    # Managing catalog-related stuff

    # Access catalog if it exists

    cat_path = None

    if "path_to_cat_json" in control["data_sources"]:
        use_catalog = True
        full_cat_path = os.path.realpath(
            os.path.expanduser(control["data_sources"]["path_to_cat_json"])
        )
        full_cat = intake.open_esm_datastore(full_cat_path)

        # Doing initial subsetting on full catalog, e.g. to only use certain cases

        if "subset" in control["data_sources"]:
            first_subset_kwargs = control["data_sources"]["subset"]
            cat_subset = full_cat.search(**first_subset_kwargs)
            # This pulls out the name of the catalog from the path
            cat_subset_name = full_cat_path.split("/")[-1].split(".")[0] + "_subset"
            cat_subset.serialize(
                directory=temp_data_path, name=cat_subset_name, catalog_type="file"
            )
            cat_path = temp_data_path + "/" + cat_subset_name + ".json"
        else:
            cat_path = full_cat_path

    #####################################################################
    # Ploomber - making a DAG

    dag = ploomber.DAG(executor=ploomber.executors.Serial())

    #####################################################################
    # Organizing notebooks - holdover from manually managing dependencies before

    all_nbs = dict()

    for nb, info in control["compute_notebooks"].items():

        all_nbs[nb] = info

    # Setting up notebook tasks

    for nb, info in all_nbs.items():

        global_params["serial"] = serial
        if "dependency" in info:
            cupid.util.create_ploomber_nb_task(
                nb,
                info,
                cat_path,
                nb_path_root,
                output_dir,
                global_params,
                dag,
                dependency=info["dependency"],
            )

        else:
            cupid.util.create_ploomber_nb_task(
                nb, info, cat_path, nb_path_root, output_dir, global_params, dag
            )

    #####################################################################
    # Organizing scripts

    if "compute_scripts" in control:

        all_scripts = dict()

        for script, info in control["compute_scripts"].items():

            all_scripts[script] = info

        # Setting up script tasks

        for script, info in all_scripts.items():

            if "dependency" in info:
                cupid.util.create_ploomber_script_task(
                    script,
                    info,
                    cat_path,
                    nb_path_root,
                    global_params,
                    dag,
                    dependency=info["dependency"],
                )

            else:
                cupid.util.create_ploomber_script_task(
                    script, info, cat_path, nb_path_root, global_params, dag
                )

    # Run the full DAG

    dag.build()

    return None
