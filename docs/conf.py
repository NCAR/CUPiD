# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
from __future__ import annotations

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.abspath("../.."))

print("sys.path:", sys.path)

# Copy README, NCAR_tips, and Contributors into docs
# This block allows us to remove the header image from any md files
# without affecting the original version, but still pull the source
# into the docs build fresh each time.

for file in ["README.md", "NCARtips.md", "Contributors.md"]:
    os.system(f"cp ../{file} ./")

    # Remove any images from the first line of the file
    with open(file) as f:
        file1 = f.readline()
        file1 = re.sub("<img.*?> ", "", file1)
        file_rest = f.read()

    with open(file, "w") as f:
        f.write(file1 + file_rest)

# -- Project information -----------------------------------------------------

project = "CUPiD"

current_year = datetime.datetime.now().year
copyright = f"{current_year}, University Corporation for Atmospheric Research"

author = "NSF NCAR"

# The master toctree document.
master_doc = "index"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "myst_nb",
    "sphinx_design",
    "nbsphinx",
]

intersphinx_mapping = {
    "dask": ("https://docs.dask.org/en/latest/", None),
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference/", None),
    "xarray": ("http://xarray.pydata.org/en/stable/", None),
    "pint": ("https://pint.readthedocs.io/en/stable/", None),
    "cftime": ("https://unidata.github.io/cftime/", None),
}

autosummary_generate = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["**.ipynb_checkpoints"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
# source_suffix = [".rst", ".md"]
source_suffix = {
    ".rst": "restructuredtext",
    ".ipynb": "myst-nb",
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"
html_title = ""

autosummary_imported_members = True

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = dict(
    # analytics_id=""  this is configured in rtfd.io
    # canonical_url="",
    repository_url="https://github.com/NCAR/CUPiD",
    repository_branch="main",
    path_to_docs="docs",
    use_edit_page_button=True,
    use_repository_button=True,
    use_issues_button=True,
    home_page_in_toc=True,
    extra_footer="<em>The National Center for Atmospheric Research is sponsored by the National Science Foundation. Any opinions, findings and conclusions or recommendations expressed in this material do not necessarily reflect the views of the National Science Foundation.</em>",  # noqa
)

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_logo = "_static/images/logos/logo.png"
html_favicon = "_static/images/logos/logo.png"

autoclass_content = "both"
