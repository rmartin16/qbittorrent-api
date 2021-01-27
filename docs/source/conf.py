# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))


# -- Project information -----------------------------------------------------
from datetime import datetime

project = "qbittorrent-api"
copyright = "%s, Russell Martin" % datetime.today().year
author = "Russell Martin"

# The full version, including alpha/beta/rc tags
release = ""


# -- General configuration ---------------------------------------------------
pygments_style = "sphinx"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.githubpages",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
## html_static_path = ["_static"]


import sphinx_glpi_theme

html_theme = "glpi"
html_theme_path = sphinx_glpi_theme.get_html_themes_path()

# sphinx-autoapi
# extensions.append('autoapi.extension')
# autoapi_type = 'python'
# autoapi_dirs = ['../../qbittorrentapi']
# autoapi_options = ['show-inheritance-diagram']
# autoapi_ignore = ['*decorators*', '*exceptions*']

# Add mappings
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
