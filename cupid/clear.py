#!/usr/bin/env python
"""
This script provides functionality to clear the contents of the 'computed_notebooks' folder
at the location specified by the 'run_dir' variable in the 'config.yml' file.

The main function `clear()` takes the path to the config.yml file as input, reads the config file
to obtain the 'run_dir' variable, and then deletes the contents of the 'computed_notebooks' folder
at that location.

"""

import os
import shutil
import click
import cupid.util


def read_config_file(config_path):
    """
    Given the file path to config.yml, this function reads the config file content and
    returns the val of the run_dir string with '/computed_notebooks' appended to it

    Args:
        config_path: str, path to configuration file (default config.yml)

    Returns:
        None
    """
    # Obtain the contents of the config.yml file and extract the run_dir variable
    control = cupid.util.get_control_dict(config_path)
    run_dir = control["data_sources"].get("run_dir", None)

    if run_dir:
        # Append '/computed_notebooks' to the run_dir value if it is not empty
        full_path = os.path.join(run_dir, "computed_notebooks")
        return full_path

    # else run_dir is empty/wasn't found in config file so return error
    raise ValueError("'run_dir' was empty/not found in the config file.")


@click.command()
@click.argument("config_path", default="config.yml")
# Entry point to this script
def clear(config_path):
    """Clears the contents of the 'computed_notebooks' folder at the location
    specified by the 'run_dir' variable in the 'config.yml' file.

    Args: config_path - The path to the config.yml file.

    """

    run_dir = read_config_file(config_path)
    # Delete the 'computed_notebooks' folder and all the contents inside of it
    shutil.rmtree(run_dir)
    print(f"All contents in {run_dir} have been cleared.")
