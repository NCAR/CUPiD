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


class manage_conda_kernel(object):
    """
    Manage conda kernels so they can be seen by `papermill`
    """

    def __init__(self, kernel_name: str):
        self.kernel_name = kernel_name

    def getcwd(self):
        """get the directory of a conda kernel by name"""
        command = ["conda", "env", "list", "--json"]
        output = subprocess.check_output(command).decode("ascii")
        envs = json.loads(output)["envs"]

        for env in envs:
            env = pathlib.Path(env)
            if self.kernel_name == env.stem:
                return env
        else:
            return None

    def isinstalled(self):
        return self.kernel_name in jupyter_client.kernelspec.find_kernel_specs()

    def ensure_installed(self):
        """install a conda kernel in a location findable by `nbconvert` etc."""

        if self.isinstalled():
            return

        path = self.getcwd()
        print(path)
        if path is None:
            raise ValueError(f'conda kernel "{self.kernel_name}" not found')
        path = path / pathlib.Path("share/jupyter/kernels")

        kernels_in_conda_env = jupyter_client.kernelspec._list_kernels_in(path)
        py_kernel_key = [k for k in kernels_in_conda_env.keys() if "python" in k][0]
        kernel_path = kernels_in_conda_env[py_kernel_key]

        jupyter_client.kernelspec.install_kernel_spec(
            kernel_path, kernel_name=self.kernel_name, user=True, replace=True
        )
        assert self.isinstalled()


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

    # theoretically ploomber should manage this kernel checking by itself, but this seems to add
    # the default kernel to info where necessary. currently a bit messy with copy pasting in 
    # script stuff.
    
    default_kernel_name = control["computation_config"].pop("default_kernel_name", None)

    if default_kernel_name is not None:
        
        for d in control["compute_notebooks"].values():
            if "kernel_name" not in d:
                d["kernel_name"] = default_kernel_name
        
        if "compute_scripts" in control:
            for d in control["compute_scripts"].values():
                if "kernel_name" not in d:
                    d["kernel_name"] = default_kernel_name
        
    else:
        for nb, d in control["compute_notebooks"].items():
            assert "kernel_name" in d, f"kernel information missing for {nb}.ipynb"
        
        for script, d in control["compute_scripts"].items():
            assert "kernel_name" in d, f"kernel information missing for {script}.py"

    for nb, d in control["compute_notebooks"].items():
        manage_conda_kernel(d["kernel_name"]).ensure_installed()

    if "compute_scripts" in control:
        for script, d in control["compute_scripts"].items():
            manage_conda_kernel(d["kernel_name"]).ensure_installed()
        
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
    
    nb_path_root = os.path.expanduser(control['data_sources']['nb_path_root'])
    
    compute_notebooks = [f"{nb_path_root}/{f}.ipynb" for f in control["compute_notebooks"].keys()]

    # get toc files; ignore glob expressions
    toc_files = get_toc_files(nb_path_root, toc, include_glob=False)
    copy_files = list(set(toc_files) - set(compute_notebooks))
    

    for src in copy_files:
        shutil.copyfile(src, f"{output_dir}/{src}")
        
        
def get_toc_files(nb_path_root, toc_dict, include_glob=True):
    """return a list of files in the _toc.yml"""

    def _toc_files(toc_dict, file_list=[]):
        for key, value in toc_dict.items():
            
            if key in ["root", "file", "glob"]:
                if not include_glob and key == "glob":
                    continue
                file = (
                    glob(f"{nb_path_root}/{value}")
                    if key == "glob"
                    else [
                        f"{nb_path_root}/{value}.{ext}"
                        for ext in ["ipynb", "md"]
                        if os.path.exists(f"{nb_path_root}/{value}.{ext}")
                    ]
                )

                assert len(file), f"no files found: {value}"
                assert len(file) == 1, f"multiple files found: {value}"
                file_list.append(file[0])

            elif key in ["chapters", "sections", "parts"]:
                file_list_ext = []
                for sub in value:
                    file_list_ext = _toc_files(sub, file_list_ext)
                file_list.extend(file_list_ext)

        return file_list

    return _toc_files(toc_dict)


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
        
        print(output_name)
        
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
