# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

import django

# add the project root to the sphinx path
sys.path.insert(0, os.path.abspath(".."))

# set the settings variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

# set up django
django.setup()

# -- Project information -----------------------------------------------------

project = "Dj-Stripe"
copyright = "2021, The Dj-Stripe Team"
author = "The Dj-Stripe Team"

# The full version, including alpha/beta/rc tags
release = "2.5.1"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",  # parse both .rst and .md files
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    # 'sphinx.ext.autosummary',  # Create neat summary tables
]

# Prefix document path to section labels, to use:
# `path/to/file:heading` instead of just `heading`
# autosectionlabel_prefix_document = True
# autosectionlabel_maxdepth = 2

# autosummary_generate = True  # Turn on sphinx.ext.autosummary

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "../.venv"]

source_suffix = [".rst", ".md", ".py"]
# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"  # 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
