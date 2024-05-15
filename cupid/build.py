#!/usr/bin/env python
"""
This script provides functionality to build a Jupyter book based on
the configuration specified in a YAML file.

The main function `build()` reads the configuration file (default config.yml),
extracts the necessary information such as the name of the book and the
directory containing computed notebooks, and then proceeds to clean and build the
Jupyter book using the `jupyter-book` command-line tool.

Args:
    CONFIG_PATH: str, path to configuration file (default config.yml)

Returns:
    None
"""

import subprocess
import sys
import click
import yaml

@click.command()
@click.argument("config_path", default="config.yml")
def build(config_path):
    """
    Build a Jupyter book based on the TOC in CONFIG_PATH. Called by `cupid-build`.

    Args:
        CONFIG_PATH: str, path to configuration file (default config.yml)

    Returns:
        None
    """

    with open(config_path, "r") as fid:
        control = yaml.safe_load(fid)

    sname = control["data_sources"]["sname"]
    run_dir = control["data_sources"]["run_dir"]

    subprocess.run(["jupyter-book", "clean", f"{run_dir}/computed_notebooks/{sname}"])
    subprocess.run(
        ["jupyter-book", "build", f"{run_dir}/computed_notebooks/{sname}", "--all"]
    )

    # Originally used this code to copy jupyter book HTML to a location to host it online

    #     if "publish_location" in control:

    #         user = os.environ.get("USER")
    #         remote_mach = control["publish_location"]["remote_mach"]
    #         remote_dir = control["publish_location"]["remote_dir"]
    # this seems more complicated than expected...people have mentioned paramiko library?
    # subprocess.run(["mkdir", "-p", remote_dir])
    # subprocess.run(["scp", "-r", f"{run_dir}/computed_notebooks/{sname}/_build/html/*",
    #                 f"{user}@{remote_mach}:{remote_dir}"])

    return None
