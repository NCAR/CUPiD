#!/usr/bin/env python
"""
This script provides functionality to build a Jupyter book based on
the configuration specified in a YAML file.

The main function `build()` reads the configuration file (default config.yml),
extracts the necessary information such as the name of the book and the
directory containing computed notebooks, and then proceeds to clean and build
the Jupyter book using the `jupyter-book` command-line tool.

Args:
    CONFIG_PATH: str, path to configuration file (default config.yml)

Returns:
    None
"""
from __future__ import annotations

import shutil
import subprocess

import click
import yaml


@click.command()
@click.argument("config_path", default="config.yml")
def build(config_path):
    """
    Build a Jupyter book based on the TOC in CONFIG_PATH. Called by `cupid-webpage`.

    Args:
        CONFIG_PATH: str, path to configuration file (default config.yml)

    Returns:
        None
    """

    with open(config_path) as fid:
        control = yaml.safe_load(fid)

    run_dir = control["data_sources"]["run_dir"]

    subprocess.run(["jupyter-book", "clean", f"{run_dir}/computed_notebooks"])
    subprocess.run(
        ["jupyter-book", "build", f"{run_dir}/computed_notebooks", "--all"],
    )
    for component in control["compute_notebooks"]:
        for notebook in control["compute_notebooks"][component]:
            if "external_tool" in control["compute_notebooks"][component][notebook]:
                if (
                    control["compute_notebooks"][component][notebook][
                        "external_tool"
                    ].get("tool_name")
                    == "ADF"
                ):
                    shutil.copytree(
                        f"{run_dir}/ADF_output",
                        f"{run_dir}/computed_notebooks/_build/html/ADF",
                    )
            if "external_tool" in control["compute_notebooks"][component][notebook]:
                if (
                    control["compute_notebooks"][component][notebook][
                        "external_tool"
                    ].get("tool_name")
                    == "ILAMB"
                ):
                    shutil.copytree(
                        f"{run_dir}/ILAMB_output",
                        f"{run_dir}/computed_notebooks/_build/html/ILAMB",
                    )

    # Originally used this code to copy jupyter book HTML to a location to host it online

    #     if "publish_location" in control:

    #         user = os.environ.get("USER")
    #         remote_mach = control["publish_location"]["remote_mach"]
    #         remote_dir = control["publish_location"]["remote_dir"]
    # this seems more complicated than expected...people have mentioned paramiko library?
    # subprocess.run(["mkdir", "-p", remote_dir])
    # subprocess.run(["scp", "-r", f"{run_dir}/computed_notebooks/_build/html/*",
    #                 f"{user}@{remote_mach}:{remote_dir}"])

    return None


if __name__ == "__main__":
    build()
