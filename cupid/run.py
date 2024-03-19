#!/usr/bin/env python

import click
import os
import sys
from glob import glob
import papermill as pm
import intake
import cupid.util
from dask.distributed import Client
import dask
import time
import ploomber

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--serial", "-s", is_flag=True, help="Do not use LocalCluster objects")
@click.option("--time-series", "-ts", is_flag=True,
              help="Run time series generation scripts prior to diagnostics")
# Options to turn components on or off
@click.option("--all", "-a", is_flag=True, help="Run all component diagnostics")
@click.option("--atmosphere", "-atm", is_flag=True, help="Run atmosphere component diagnostics")
@click.option("--ocean", "-ocn", is_flag=True, help="Run ocean component diagnostics")
@click.option("--land", "-lnd", is_flag=True, help="Run land component diagnostics")
@click.option("--seaice", "-ice", is_flag=True, help="Run sea ice component diagnostics")
@click.option("--landice", "-glc", is_flag=True, help="Run land ice component diagnostics")

@click.argument("config_path")

def run(config_path, serial=False, time_series=False, 
        all=False, atmosphere=False, ocean=False, land=False, seaice=False, landice=False):
    """
    Main engine to set up running all the notebooks.
    """

    # Abort if run with --time-series (until feature is added)
    if time_series:
        sys.tracebacklimit = 0
        raise NotImplementedError("--time-series option not implemented yet")

    # Get control structure
    control = cupid.util.get_control_dict(config_path)
    cupid.util.setup_book(config_path)

    # Grab paths

    run_dir = os.path.realpath(os.path.expanduser(control['data_sources']['run_dir']))
    output_dir = run_dir + "/computed_notebooks/" + control['data_sources']['sname']
    temp_data_path = run_dir + "/temp_data" 
    nb_path_root = os.path.realpath(os.path.expanduser(control['data_sources']['nb_path_root']))

    #####################################################################
    # Managing catalog-related stuff

    # Access catalog if it exists

    cat_path = None

    if 'path_to_cat_json' in control['data_sources']:
        use_catalog = True
        full_cat_path = os.path.realpath(os.path.expanduser(control['data_sources']['path_to_cat_json']))
        full_cat = intake.open_esm_datastore(full_cat_path)

    # Doing initial subsetting on full catalog, e.g. to only use certain cases

        if 'subset' in control['data_sources']:
            first_subset_kwargs = control['data_sources']['subset']
            cat_subset = full_cat.search(**first_subset_kwargs)
            # This pulls out the name of the catalog from the path
            cat_subset_name = full_cat_path.split("/")[-1].split('.')[0] + "_subset"
            cat_subset.serialize(directory=temp_data_path, name=cat_subset_name, catalog_type="file")
            cat_path = temp_data_path + "/" + cat_subset_name + ".json"
        else:
            cat_path = full_cat_path


    #####################################################################
    # Managing global parameters

    global_params = dict()

    if 'global_params' in control:
        global_params = control['global_params']


    #####################################################################
    # Ploomber - making a DAG

    dag = ploomber.DAG(executor=ploomber.executors.Serial())


    #####################################################################
    # Organizing notebooks to run

    component_options = {"atmosphere": atmosphere,
                         "ocean": ocean,
                         "land": land,
                         "seaice": seaice,
                         "landice": landice}
    
    all_nbs = dict()
    for nb, info in control['compute_notebooks']['infrastructure'].items():
        all_nbs[nb] = info
        
    # automatically run all if not specified
    if True not in [atmosphere, ocean, land, seaice, landice]:
        all = True
    
    if all:
        for nb_category in control["compute_notebooks"].values():
            for nb, info in nb_category.items():
                all_nbs[nb] = info

    else:
        for comp_name, comp_bool in component_options.items():
            if comp_bool:
                for nb, info in control['compute_notebooks'][comp_name].items():
                    all_nbs[nb] = info
            

    # Setting up notebook tasks

    for nb, info in all_nbs.items():

        global_params['serial'] = serial
        
        if "dependency" in info:
            cupid.util.create_ploomber_nb_task(nb, info, cat_path, nb_path_root, output_dir, global_params, dag, dependency = info["dependency"])

        else:
            cupid.util.create_ploomber_nb_task(nb, info, cat_path, nb_path_root, output_dir, global_params, dag)

    #####################################################################
    # Organizing scripts

    if 'compute_scripts' in control:

        all_scripts = dict()
            
        if all:
            for script_category in control["compute_scripts"]:
                for script, info in nb_category.items():
                    all_scripts[script] = info
                    
        else:
            for comp_name, comp_bool in component_options.items():
                if comp_bool:
                    for script, info in control['compute_scripts'][comp_name].items():
                        all_scripts[script] = info
                    
        # Setting up script tasks

        for script, info in all_scripts.items():

            if "dependency" in info:
                cupid.util.create_ploomber_script_task(script, info, cat_path, nb_path_root, global_params, dag, dependency = info["dependency"])

            else:
                cupid.util.create_ploomber_script_task(script, info, cat_path, nb_path_root, global_params, dag)

    # Run the full DAG

    dag.build()

    return None

