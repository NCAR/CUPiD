#!/usr/bin/env python3
"""
Unit tests for GitHelper class

You can run this like so:
    python3 -m unittest test_unit_git_helper.py
"""

import os
import sys
import unittest
import tempfile
import shutil
import subprocess
from pathlib import Path

# -- add top-level CUPiD dir to path
sys.path.insert(1, os.path.join(os.path.dirname(__file__), os.pardir))

# pylint: disable=wrong-import-position
from cupid.git_helper import GitHelper

# pylint: disable=invalid-name


def check_call_suppress_output(args, shell=False, cwd=None):
    """Make a subprocess call with the given args, suppressing all output unless there's an error"""
    try:
        subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            shell=shell,
            cwd=cwd,
        )
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {e.cmd}")
        print("stdout:")
        print(e.stdout)
        print("stderr:")
        print(e.stderr)
        raise


class TestGitHelper(unittest.TestCase):
    """
    Tests for GitHelper class in git_helper.py
    """

    # ------------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------------

    def setUp(self):
        # Create and change to a temporary directory, saving the original directory for later
        self._return_dir = os.getcwd()
        self._tempdir = tempfile.mkdtemp()
        os.chdir(self._tempdir)

        # Initialize a git repo in the temporary directory
        check_call_suppress_output("git init", shell=True)

        # Set up a different directory for publishing to
        self._pubdir = tempfile.mkdtemp()
        check_call_suppress_output("git init", shell=True, cwd=self._pubdir)
        # Needs to be clean, so we'll need an initial commit
        Path.touch(os.path.join(self._pubdir, ".gitignore"))
        check_call_suppress_output("git add .gitignore", shell=True, cwd=self._pubdir)
        check_call_suppress_output("git commit -m 'initial commit'", shell=True, cwd=self._pubdir)

    def tearDown(self):
        # Change back to original directory
        os.chdir(self._return_dir)
        # Delete temporary directory
        shutil.rmtree(self._tempdir, ignore_errors=True)

    # ------------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------------

    def test_init(self):
        """Just make sure you can initialize a GitHelper without error"""
        _ = GitHelper(self._pubdir, "some version", publish_url="dummy_url.com")
