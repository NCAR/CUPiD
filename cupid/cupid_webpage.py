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

import click
import yaml
from git_helper import GitHelper


@click.command()
@click.argument("config_path", default="config.yml")
@click.option(
    "--github-pages",
    "-g",
    is_flag=True,
    help="Publish to GitHub pages\n"
    "If given, then -d/--publish-dir must be provided and it must be a git repo.",
)
@click.option(
    "--name",
    "-n",
    default="",
    help="Name of sub-directory in -d/--publish-dir that HTML outputs should be copied to",
)
@click.option(
    "--overwrite",
    "-o",
    is_flag=True,
    help="Overwrite existing publish directory",
)
@click.option(
    "--publish-dir",
    "-d",
    default="",
    help="Directory where the HTML outputs should be copied (into a new sub-directory given by -n/--name)",
)
def build(config_path, github_pages, name, overwrite, publish_dir):
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
    if github_pages:
        # Check that you gave --publish-dir
        if not publish_dir:
            raise RuntimeError(
                "When specifying -g/--github-pages, you must specify -d/--publish-dir",
            )

        # Check that git repo is ready
        if os.path.split(publish_dir)[-1] != "versions":
            publish_dir = os.path.join(publish_dir, "versions")
        git_dir = os.path.join(publish_dir, os.pardir, ".git")
        if not os.path.isdir(git_dir):
            raise RuntimeError(f"Not an existing git repo: '{os.path.pardir(git_dir)}'")
        git_repo = GitHelper(os.path.split(git_dir)[0], name)
    if publish_dir:
        if not name:
            raise RuntimeError(
                "When specifying -d/--publish-dir, you must also provide -n/--name",
            )
        publish_dir = os.path.join(publish_dir, name)
        if os.path.exists(publish_dir):
            if not overwrite:
                raise FileExistsError(
                    f"Add -o to overwrite existing directory '{publish_dir}'",
                )
        print(f"Publishing to '{publish_dir}'")

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

    if publish_dir:
        publish_parent_dir = os.path.split(publish_dir)[0]
        if not os.path.exists(publish_parent_dir):
            os.makedirs(publish_parent_dir)
        shutil.copytree(
            html_output_path,
            publish_dir,
            dirs_exist_ok=overwrite,
        )

        if github_pages:
            # Write to index.html, if needed
            index_html_file = os.path.join(publish_parent_dir, os.pardir, "index.html")
            new_line = f'<a href="versions/{name}/index.html"/>{name}</a><p>\n'
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
