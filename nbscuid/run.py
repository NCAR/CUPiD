#!/usr/bin/env python

import os
from glob import glob
import papermill as pm
import intake
import nbscuid.util
import sys
from dask.distributed import Client
import dask
import time
import ploomber

def run():
    """
    Main engine to set up running all the notebooks. Called by `nbscuid-run`.
    
    Args:
        none
    Returns:
        None
    
    """
    
    # Get control structure
    config_path = str(sys.argv[1])
    control = nbscuid.util.get_control_dict(config_path)    
    nbscuid.util.setup_book(config_path)
            
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
    
    dag = ploomber.DAG(executor=ploomber.executors.Parallel())
    
     
    #####################################################################
    # Organizing notebooks - holdover from manually managing dependencies before

    all_nbs = dict()

    for nb, info in control['compute_notebooks'].items():
        
        all_nbs[nb] = info

    # Setting up notebook tasks
    
    for nb, info in all_nbs.items():
        
        if "dependency" in info:
            nbscuid.util.create_ploomber_nb_task(nb, info, cat_path, nb_path_root, output_dir, global_params, dag, dependency = info["dependency"])
        
        else: 
            nbscuid.util.create_ploomber_nb_task(nb, info, cat_path, nb_path_root, output_dir, global_params, dag)
    
    #####################################################################
    # Organizing scripts
    
    if 'compute_scripts' in control:
    
        all_scripts = dict()

        for script, info in control['compute_scripts'].items():

            all_scripts[script] = info

        # Setting up script tasks

        for script, info in all_scripts.items():

            if "dependency" in info:
                nbscuid.util.create_ploomber_script_task(script, info, cat_path, nb_path_root, global_params, dag, dependency = info["dependency"])

            else:     
                nbscuid.util.create_ploomber_script_task(script, info, cat_path, nb_path_root, global_params, dag)
    
    # Run the full DAG
    
    dag.build()
        
    return None
    