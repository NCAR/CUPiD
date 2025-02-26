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

import os
import shutil
import subprocess
from urllib.parse import quote

import click
import yaml
from git_helper import GitHelper


def github_pages_publish(
    github_pages_dir,
    github_pages_dir_thisversion,
    name,
    overwrite,
    git_repo,
    html_output_path,
):
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
    Build a Jupyter book based on the TOC in CONFIG_PATH. Called by `cupid-webpage`.

    Args:
        CONFIG_PATH: str, path to configuration file (default config.yml)

    Returns:
        None
    """

    with open(config_path) as fid:
        control = yaml.safe_load(fid)

    # Check and process arguments
    if github_pages_dir:
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
            if "external_tool" in control["compute_notebooks"][component][notebook]:
                if (
                    control["compute_notebooks"][component][notebook][
                        "external_tool"
                    ].get("tool_name")
                    == "ADF"
                ):
                    shutil.copytree(
                        f"{run_dir}/ADF_output",
                        os.path.join(html_output_path, "ADF"),
                    )

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
