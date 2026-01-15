"""
This module provides functions and classes for managing conda kernels,
executing notebooks with custom engines, and creating tasks for Ploomber DAGs.
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

import jupyter_client
import papermill as pm
import ploomber
import yaml
from jinja2 import Template
from papermill.engines import NBClientEngine


class MarkdownJinjaEngine(NBClientEngine):
    """Class for using the Jinja Engine to run notebooks"""

    @classmethod
    def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
        """Execute notebooks with papermill execution engine"""
        jinja_data = {} if "jinja_data" not in kwargs else kwargs["jinja_data"]

        # call the papermill execution engine:
        super().execute_managed_notebook(nb_man, kernel_name, **kwargs)

        for cell in nb_man.nb.cells:
            if cell.cell_type == "markdown":
                cell["source"] = Template(cell["source"]).render(**jinja_data)


def get_control_dict(config_path):
    """Get control dictionary from configuration file"""

    try:
        with open(config_path) as fid:
            control = yaml.safe_load(fid)
    except FileNotFoundError:
        print(f"ERROR: {config_path} not found")
        sys.exit(1)

    default_kernel_name = control["computation_config"].pop("default_kernel_name", None)

    control["env_check"] = dict()

    if "compute_notebooks" in control:
        for nb_category in control["compute_notebooks"].values():
            # pylint: disable=invalid-name
            for nb, info in nb_category.items():
                info["kernel_name"] = info.get("kernel_name", default_kernel_name)
                if info["kernel_name"] is None:
                    info["kernel_name"] = "cupid-analysis"
                    warnings.warn(
                        f"No conda environment specified for {nb}.ipynb and"
                        + " no default kernel set, will use cupid-analysis environment.",
                    )
                if info["kernel_name"] not in control["env_check"]:
                    control["env_check"][info["kernel_name"]] = (
                        info["kernel_name"]
                        in jupyter_client.kernelspec.find_kernel_specs()
                    )

    if "compute_scripts" in control:
        for script_category in control["compute_scripts"].values():
            for script, info in script_category.items():
                info["kernel_name"] = info.get("kernel_name", default_kernel_name)
                if info["kernel_name"] is None:
                    info["kernel_name"] = "cupid-analysis"
                    warnings.warn(
                        f"No environment specified for {script}.py and no default"
                        + " kernel set, will use cupid-analysis environment.",
                    )
                if info["kernel_name"] not in control["env_check"]:
                    control["env_check"][info["kernel_name"]] = (
                        info["kernel_name"]
                        in jupyter_client.kernelspec.find_kernel_specs()
                    )

    return control


def setup_logging(config_path):
    """
    Set up logging based on configuration file log level
    Options for log levels include debug, info, warning, and error.
    Returns logger object
    """
    control = get_control_dict(config_path)
    # default level is info if log level is not set in config
    log_level = control["computation_config"].get("log_level", "info")
    if log_level == "debug" or log_level == "DEBUG":
        logging.basicConfig(
            level=logging.DEBUG,
        )
    elif log_level == "info" or log_level == "INFO":
        logging.basicConfig(
            level=logging.INFO,
        )
    elif log_level == "warning" or log_level == "WARNING":
        logging.basicConfig(
            level=logging.WARNING,
        )
    elif log_level == "error" or log_level == "ERROR":
        logging.basicConfig(
            level=logging.ERROR,
        )
    else:
        print('setting log_level to "info" because invalid log level')
        logging.basicConfig(
            level=logging.INFO,
        )

    return logging.getLogger(__name__)


def setup_book(config_path, run_dir):
    """Setup run directory and output jupyter book"""

    control = get_control_dict(config_path)

    # ensure directory
    output_root = run_dir + "/computed_notebooks"

    os.makedirs(output_root, exist_ok=True)

    output_dir = f"{output_root}"

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

    with open(f"{path_to_here}/_jupyter-book-config-defaults.yml") as fid:
        config = yaml.safe_load(fid)

    # update defaults
    config.update(control["book_config_keys"])

    # write config file
    with open(f"{output_dir}/_config.yml", "w") as fid:
        yaml.dump(config, fid, sort_keys=False)

    return None


def create_ploomber_nb_task(
    nb,
    info,
    cat_path,
    output_dir,
    global_params,
    dag,
    dependency=None,
):
    """
    Creates a ploomber task for running a notebook, including necessary parameters.

    Args:
        nb: key from dict of notebooks
        info: various specifications for the notebook, originally from config.yml
        use_catalog: bool specified earlier, specifying if whole collection uses a catalog or not
        output_dir: set directory where computed notebooks get put
        global_params: global parameters from config.yml
        dag: ploomber DAG to add the task to
        dependency: what the upstream task is

    Returns:
        task: ploomber task object
    """

    parameter_groups = info["parameter_groups"]

    # passing in subset kwargs if they're provided
    if "subset" in info:
        subset_kwargs = info["subset"]
    else:
        subset_kwargs = {}

    default_params = {}
    if "default_params" in info:
        default_params = info["default_params"]

    for key, parms in parameter_groups.items():
        input_path = f"{info["nb_path_root"]}/{nb}.ipynb"
        output_name = f"{nb}-{key}" if key != "none" else f"{nb}"

        output_path = f"{output_dir}/{output_name}"

        # all of these things should be optional
        parms_in = dict(**default_params)
        parms_in.update(**global_params)
        parms_in.update(dict(**parms))

        parms_in["subset_kwargs"] = subset_kwargs

        if cat_path is not None:
            parms_in["path_to_cat"] = cat_path

        pm_params = {
            "engine_name": "md_jinja",
            "jinja_data": parms,
            "cwd": info["nb_path_root"],
        }

        pm.engines.papermill_engines._engines["md_jinja"] = MarkdownJinjaEngine

        task = ploomber.tasks.NotebookRunner(
            Path(input_path),
            ploomber.products.File(output_path + ".ipynb"),
            dag,
            params=parms_in,
            papermill_params=pm_params,
            kernelspec_name=info["kernel_name"],
            name=output_name,
        )

        if dependency:
            raise NotImplementedError
            # set DAG dependency here
            # something with task.set_upstream(other_task?)

    return task


def create_ploomber_script_task(
    script,
    info,
    cat_path,
    global_params,
    dag,
    dependency=None,
):
    """
    Creates a Ploomber task for running a script, including necessary parameters.

    Args:
        script (str): The key from the dictionary of scripts.
        info (dict): Various specifications for the notebook, originally from config.yml.
        cat_path (str or None): Path to the catalog file if using a catalog, otherwise None.
        global_params (dict): Global parameters from config.yml.
        dag (ploomber.DAG): Ploomber DAG to add the task to.
        dependency (ploomber.Task, optional): The upstream task. Defaults to None.

    Returns:
        ploomber.Task: The Ploomber task object.

    Raises:
        NotImplementedError: Raised if dependency is not None (setting DAG dependency is not implemented yet).
    """

    parameter_groups = info["parameter_groups"]

    # passing in subset kwargs if they're provided
    if "subset" in info:
        subset_kwargs = info["subset"]
    else:
        subset_kwargs = {}

    default_params = {}
    if "default_params" in info:
        default_params = info["default_params"]

    for key, parms in parameter_groups.items():
        input_path = f"{info["nb_path_root"]}/{script}.py"
        output_name = f"{script}-{key}" if key != "none" else f"{script}"

        # output_path = f"{output_dir}/{output_name}"

        # all of these things should be optional
        parms_in = dict(**default_params)
        parms_in.update(**global_params)
        parms_in.update(dict(**parms))

        parms_in["subset_kwargs"] = subset_kwargs

        if cat_path is not None:
            parms_in["path_to_cat"] = cat_path

        task = ploomber.tasks.ScriptRunner(
            Path(input_path),
            ploomber.products.File(info["product"]),
            dag,
            params=parms_in,
            name=output_name,
        )

        if dependency is not None:
            raise NotImplementedError
            # set DAG dependency here
            # something with task.set_upstream(other_task?)

    return task


def is_bad_env(control, nb_info):
    return not control["env_check"][nb_info["kernel_name"]]
