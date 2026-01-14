#!/usr/bin/env python
"""
This script provides functionality to build a Jupyter book based on
the configuration specified in a YAML file.

The main function `build()` reads the configuration file (default config.yml),
extracts the necessary information such as the name of the book and the
directory containing computed notebooks, and then proceeds to clean and build
the Jupyter book using the `jupyter-book` command-line tool.

Usage: generate_webpage.py [OPTIONS] [CONFIG_PATH]

  Build a Jupyter book based on the TOC in CONFIG_PATH. Called by `cupid-
  webpage`.

  Args:     CONFIG_PATH: str, path to configuration file (default config.yml)

  Returns:     None

Options:
  -g, --github-pages-dir TEXT  For publishing to GitHub pages: Directory where
                               the HTML outputs should be copied (into a new
                               sub-directory in versions/ given by -n/--name)
  -n, --name TEXT              Name of version to publish
  -o, --overwrite              Overwrite existing publish directory
  --help                       Show this message and exit.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from urllib.parse import quote

import click

try:
    from git_helper import GitHelper
except ModuleNotFoundError:
    from cupid.git_helper import GitHelper

try:
    from util import get_control_dict
    from util import is_bad_env
except ModuleNotFoundError:
    from cupid.util import get_control_dict
    from cupid.util import is_bad_env


def github_pages_publish(
    github_pages_dir,
    github_pages_dir_thisversion,
    name,
    overwrite,
    git_repo,
    html_output_path,
):
    """
    Publishes a version of the site to GitHub Pages.

    Copies the HTML output to the GitHub Pages directory, add prefix to `index.html`
    with a link to the new version, and pushes changes to the repository.

    Args:
        github_pages_dir (str): Root directory for GitHub Pages.
        github_pages_dir_thisversion (str): Directory for the specific version.
        name (str): Version name.
        overwrite (bool): Whether to overwrite existing files.
        git_repo (GitHelper): Git repository helper instance.
        html_output_path (str): Path to the generated HTML files.
    """
    parent_dir = os.path.split(github_pages_dir_thisversion)[-1]
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    shutil.copytree(
        html_output_path,
        github_pages_dir_thisversion,
        dirs_exist_ok=overwrite,
    )

    # Handle special characters, converting e.g. ^ to %5E
    name_url = quote(name)

    # Write to index.html, if needed
    index_html_file = os.path.join(github_pages_dir, "index.html")
    new_line = f'<a href="versions/{name_url}/index.html"/>{name}</a><p>\n'
    do_write = True
    if os.path.exists(index_html_file):
        with open(index_html_file) as f:
            for line in f:
                if line.strip() == new_line.strip():
                    do_write = False
                    break
    if do_write:
        with open(index_html_file, "a") as f:
            f.write(new_line)

    # Publish to GitHub.io
    git_repo.publish()


def github_pages_args(github_pages_dir, name, overwrite):
    """
    Prepares the GitHub Pages directory for publishing.
    Ensures a name is provided, initializes a `GitHelper` object,
    and checks if the version directory exists, handling overwrite conditions.

    Args:
        github_pages_dir (str): Root directory for GitHub Pages.
        name (str): Version name.
        overwrite (bool): Whether to overwrite an existing version directory.

    Returns:
        tuple: (str, GitHelper) - The version directory path and `GitHelper` instance.

    Raises:
        RuntimeError: If no name is provided.
        FileExistsError: If the directory exists and overwrite is not allowed.
    """
    # Check that you gave a name
    if not name:
        raise RuntimeError(
            "When specifying -g/--github-pages-dir, you must also provide -n/--name",
        )

    # Set up GitHelper object
    git_repo = GitHelper(github_pages_dir, name)
    this_version_dir = os.path.join(github_pages_dir, "versions", name)
    if os.path.exists(this_version_dir) and not overwrite:
        raise FileExistsError(
            f"Add -o to overwrite existing directory '{this_version_dir}'",
        )
    print(f"Publishing to '{this_version_dir}'")
    return this_version_dir, git_repo


@click.command()
@click.argument("config_path", default="config.yml")
@click.option(
    "--github-pages-dir",
    "-g",
    default="",
    help="For publishing to GitHub pages:\n"
    "Directory where the HTML outputs should be copied (into a new sub-directory in versions/ given by -n/--name)",
)
@click.option(
    "--name",
    "-n",
    default="",
    help="Name of version to publish",
)
@click.option(
    "--overwrite",
    "-o",
    is_flag=True,
    help="Overwrite existing publish directory",
)
def build(config_path, github_pages_dir, name, overwrite):
    """
    Build a Jupyter book based on the TOC in CONFIG_PATH. Called by ``cupid-webpage``.

    Args:
        CONFIG_PATH: str, path to configuration file (default config.yml)

    Returns:
        None
    """

    control = get_control_dict(config_path)

    # Check and process arguments
    if github_pages_dir:
        github_pages_dir = os.path.realpath(github_pages_dir)
        github_pages_dir_thisversion, git_repo = github_pages_args(
            github_pages_dir,
            name,
            overwrite,
        )

    run_dir = control["data_sources"]["run_dir"]

    subprocess.run(["jupyter-book", "clean", f"{run_dir}/computed_notebooks"])
    subprocess.run(
        ["jupyter-book", "build", f"{run_dir}/computed_notebooks", "--all"],
    )
    html_output_path = os.path.join(run_dir, "computed_notebooks", "_build", "html")
    for component in control["compute_notebooks"]:
        for notebook in control["compute_notebooks"][component]:
            # Skip this notebook if it wasn't run due to bad environment
            info = control["compute_notebooks"][component][notebook]
            if is_bad_env(control, info):
                print(f"Skipping {notebook}: Not run due to bad environment")
                continue

            if "external_tool" in control["compute_notebooks"][component][notebook]:
                tool_name = control["compute_notebooks"][component][notebook][
                    "external_tool"
                ].get("tool_name")
                if tool_name in ["ADF", "LDF", "CVDP", "ILAMB"]:
                    if os.path.isdir(f"{run_dir}/{tool_name}_output"):
                        shutil.copytree(
                            f"{run_dir}/{tool_name}_output",
                            os.path.join(html_output_path, component, tool_name),
                        )
                    else:
                        print(f"Warning: no directory {run_dir}/{tool_name}_output")

    if github_pages_dir:
        github_pages_publish(
            github_pages_dir,
            github_pages_dir_thisversion,
            name,
            overwrite,
            git_repo,
            html_output_path,
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
