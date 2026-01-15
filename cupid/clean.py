#!/usr/bin/env python
"""
This script provides functionality to clean the contents of the "computed_notebooks" folder
at the location specified by the "run_dir" variable in the CONFIG_PATH.

The main function `clean()` takes the path to the configuration file as input, reads the config file
to obtain the "run_dir" variable, and then deletes the contents of the "computed_notebooks" folder
at that location.

Usage: clean.py [OPTIONS] [CONFIG_PATH]

  Cleans the contents of the "computed_notebooks" folder at the location
  specified by the "run_dir" variable in the CONFIG_PATH.

  Args: CONFIG_PATH - The path to the configuration file.

Options:
  --help  Show this message and exit.
"""
from __future__ import annotations

import os
import shutil

import click


@click.command()
@click.argument(
    "run_dir",
    default=".",
    help="Path to run directory where computed_notebooks will be cleaned",
)
# Entry point to this script
def clean(run_dir):
    """Cleans the contents of the "computed_notebooks" folder at the location
    specified by the "run_dir" variable in the CONFIG_PATH.

    Args: RUN_DIR - The path to the directory to be cleaned.

    Called by ``cupid-clean``.
    """
    # Delete the "computed_notebooks" folder and all the contents inside of it
    shutil.rmtree(os.path.join(run_dir, "computed_notebooks"))
    print(f"All contents in {run_dir} have been cleaned.")


if __name__ == "__main__":
    clean()
