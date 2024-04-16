import os
import shutil
from glob import glob
import pathlib
import subprocess
import json
import yaml
import jupyter_client
import papermill as pm
import ploomber
from papermill.engines import NBClientEngine
from jinja2 import Template
import dask
from pathlib import Path
import warnings


class md_jinja_engine(NBClientEngine):
    @classmethod
    def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
        jinja_data = {} if "jinja_data" not in kwargs else kwargs["jinja_data"]

        # call the papermill execution engine:
        super().execute_managed_notebook(nb_man, kernel_name, **kwargs)

        for cell in nb_man.nb.cells:
            if cell.cell_type == "markdown":
                cell["source"] = Template(cell["source"]).render(**jinja_data)


def get_control_dict(config_path):
    with open(config_path, "r") as fid:
        control = yaml.safe_load(fid)

    default_kernel_name = control["computation_config"].pop("default_kernel_name", None)

    control["env_check"] = dict()
    
    if "compute_notebooks" in control:
        for nb_category in control["compute_notebooks"].values():
            for nb, info in nb_category.items():
                info["kernel_name"] = info.get("kernel_name", default_kernel_name)
                if info["kernel_name"] is None:
                    info["kernel_name"] = "cupid-analysis"
                    warnings.warn(f"No conda environment specified for {nb}.ipynb and no default kernel set, will use cupid-analysis environment.")
                if info["kernel_name"] not in control["env_check"]:
                    control["env_check"][info["kernel_name"]] = info["kernel_name"] in jupyter_client.kernelspec.find_kernel_specs()
                    
    if "compute_scripts" in control:
        for script_category in control["compute_scripts"].values():
            for script, info in script_category.items():
                info["kernel_name"] = info.get("kernel_name", default_kernel_name)
                if info["kernel_name"] is None:
                    info["kernel_name"] = "cupid-analysis"
                    warnings.warn(f"No environment specified for {script}.py and no default kernel set, will use cupid-analysis environment.")
                if info["kernel_name"] not in control["env_check"]:
                    control["env_check"][info["kernel_name"]] = info["kernel_name"] in jupyter_client.kernelspec.find_kernel_specs()
    
    return control


def setup_book(config_path):
    """Setup run directory and output jupyter book"""

    control = get_control_dict(config_path)

    # ensure directory
    run_dir = os.path.expanduser(control['data_sources']["run_dir"])
    output_root = run_dir + "/computed_notebooks"
    
    os.makedirs(output_root, exist_ok=True)
    
    output_dir = f'{output_root}/{control["data_sources"]["sname"]}'
    
    os.makedirs(output_dir, exist_ok=True)
    
    # create temp catalog directory
    temp_data_path = run_dir + "/temp_data"
    
    os.makedirs(temp_data_path, exist_ok=True)
    

    # write table of contents file
    toc = control["book_toc"]
    with open(f"{output_dir}/_toc.yml", "w+") as fid:
        yaml.dump(toc, fid, sort_keys=False)

    # read config defaults
    
    path_to_here = os.path.dirname(os.path.realpath(__file__))
    
    with open(f"{path_to_here}/_jupyter-book-config-defaults.yml", "r") as fid:
        config = yaml.safe_load(fid)

    # update defaults
    config.update(control["book_config_keys"])

    # write config file
    with open(f"{output_dir}/_config.yml", "w") as fid:
        yaml.dump(config, fid, sort_keys=False)

    # get list of computational notebooks
    
    # if 'compute_notebooks' in control:

    #     nb_path_root = os.path.realpath(os.path.expanduser(control['data_sources']['nb_path_root']))
    #     # the below won't work for index, unless we put it in an infrastructure folder and change that elsewhere
    #     compute_notebooks = [f"{nb_path_root}/{ok}/{ik}.ipynb" for ok, ov in control["compute_notebooks"].items() for ik, iv in ov.items()]
    
    #     # get toc files; ignore glob expressions
    #     toc_files = get_toc_files(nb_path_root, toc, include_glob=False)
    #     copy_files = list(set(toc_files) - set(compute_notebooks))
        
    #     for src in copy_files:
    #         #shutil.copyfile(src, f"{output_dir}/{src}")
    #         pass
        
        
# def get_toc_files(nb_path_root, toc_dict, include_glob=True):
#     """return a list of files in the _toc.yml"""

#     def _toc_files(toc_dict, file_list=[]):
#         for key, value in toc_dict.items():
            
#             if key in ["root", "file", "glob"]:
#                 if not include_glob and key == "glob":
#                     continue
#                 if key == "glob":    
#                     file = glob(f"{nb_path_root}/{value}")
#                 else:
#                     file = [f"{nb_path_root}/{value}.{ext}" for ext in ["ipynb", "md"] if os.path.exists(f"{nb_path_root}/{value}.{ext}")]
    
#                 assert len(file), f"no files found: {value}"
#                 assert len(file) == 1, f"multiple files found: {value}"
#                 file_list.append(file[0])

#             elif key in ["chapters", "sections", "parts"]:
#                 file_list_ext = []
#                 for sub in value:
#                     file_list_ext = _toc_files(sub, file_list_ext)
#                 file_list.extend(file_list_ext)

#         return file_list

#     return _toc_files(toc_dict)


def create_ploomber_nb_task(nb, info, cat_path, nb_path_root, output_dir, global_params, dag, dependency=None):
    """
    Creates a ploomber task for running a notebook, including necessary parameters.
    
    Args:
        nb: key from dict of notebooks
        info: various specifications for the notebook, originally from config.yml
        use_catalog: bool specified earlier, specifying if whole collection uses a catalog or not
        nb_path_root: from config.yml, path to folder containing template notebooks
        output_dir: set directory where computed notebooks get put
        global_params: global parameters from config.yml
        dag: ploomber DAG to add the task to
        dependency: what the upstream task is
    
    Returns:
        task: ploomber task object
    """

    parameter_groups = info['parameter_groups']

    ### passing in subset kwargs if they're provided
    if 'subset' in info:
        subset_kwargs = info['subset']
    else:
        subset_kwargs = {}

    default_params = {}
    if 'default_params' in info:
        default_params = info['default_params']

    for key, parms in parameter_groups.items():

        input_path = f'{nb_path_root}/{nb}.ipynb'
        output_name = (
            f'{nb}-{key}'
            if key != 'none' else f'{nb}'
        )

        output_path = f'{output_dir}/{output_name}'
        
        ### all of these things should be optional
        parms_in = dict(**default_params)
        parms_in.update(**global_params)
        parms_in.update(dict(**parms))
                            
        parms_in['subset_kwargs'] = subset_kwargs            
            
        if cat_path != None:
            parms_in['path_to_cat'] = cat_path
        
        
        pm_params = {
                     'engine_name': 'md_jinja',
                     'jinja_data': parms,
                     'cwd': nb_path_root}
        
        pm.engines.papermill_engines._engines["md_jinja"] = md_jinja_engine
        
        task = ploomber.tasks.NotebookRunner(Path(input_path), ploomber.products.File(output_path + '.ipynb'), dag, params=parms_in, papermill_params=pm_params, kernelspec_name=info['kernel_name'], name=output_name)
        
        if dependency != None:
            raise NotImplementedError
            # set DAG dependency here 
            # something with task.set_upstream(other_task?)
        
    return task

def create_ploomber_script_task(script, info, cat_path, nb_path_root, global_params, dag, dependency=None):
    """
    Creates a ploomber task for running a script, including necessary parameters.
    
    UPDATE THIS DOCSTRING
    
    Args:
        script: key from dict of scripts
        info: various specifications for the notebook, originally from config.yml
        use_catalog: bool specified earlier, specifying if whole collection uses a catalog or not
        nb_path_root: from config.yml, path to folder containing template notebooks
        global_params: global parameters from config.yml
        dag: ploomber DAG to add the task to
        dependency: what the upstream task is
    
    Returns:
        task: ploomber task object
    """

    parameter_groups = info['parameter_groups']

    ### passing in subset kwargs if they're provided
    if 'subset' in info:
        subset_kwargs = info['subset']
    else:
        subset_kwargs = {}

    default_params = {}
    if 'default_params' in info:
        default_params = info['default_params']

    for key, parms in parameter_groups.items():

        input_path = f'{nb_path_root}/{script}.py'
        output_name = (
            f'{script}-{key}'
            if key != 'none' else f'{script}'
        )

        #output_path = f'{output_dir}/{output_name}'
        
        ### all of these things should be optional
        parms_in = dict(**default_params)
        parms_in.update(**global_params)
        parms_in.update(dict(**parms))
                            
        parms_in['subset_kwargs'] = subset_kwargs            
            
        if cat_path != None:
            parms_in['path_to_cat'] = cat_path
        
        
        
        task = ploomber.tasks.ScriptRunner(Path(input_path), ploomber.products.File(info['product']), dag, params=parms_in, name=output_name)
        
        if dependency != None:
            raise NotImplementedError
            # set DAG dependency here 
            # something with task.set_upstream(other_task?)
        
    return task