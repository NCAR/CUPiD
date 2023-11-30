#!/usr/bin/env python

import subprocess
import sys
import os
import yaml

def build():
    """
    Build a Jupyter book based on the TOC in config.yml. Called by `nbscuid-build`.
    
    Args:
        none
    Returns:
        None
    """
    
    config_path = str(sys.argv[1])
    
    with open(config_path, "r") as fid:
        control = yaml.safe_load(fid)
    
    sname = control["data_sources"]["sname"]
    run_dir = control["data_sources"]["run_dir"]

    subprocess.run(["jupyter-book", "clean" , f"{run_dir}/computed_notebooks/{sname}"])
    subprocess.run(["jupyter-book",  "build" , f"{run_dir}/computed_notebooks/{sname}",  "--all"])

### Originally used this code to copy jupyter book HTML to a location to host it online

#     if 'publish_location' in control:
        
#         user = os.environ.get('USER')
#         remote_mach = control["publish_location"]["remote_mach"]
#         remote_dir = control["publish_location"]["remote_dir"]
# this seems more complicated than expected...people have mentioned paramiko library?
        # subprocess.run(["mkdir", "-p", remote_dir])
        # subprocess.run(["scp", "-r", f"{run_dir}/computed_notebooks/{sname}/_build/html/*", f"{user}@{remote_mach}:{remote_dir}"])
        
    return None

