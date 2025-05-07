"""
Timeseries generation tool adapted from ADF for general CUPiD use.
"""
# ++++++++++++++++++++++++++++++
# Import standard python modules
# ++++++++++++++++++++++++++++++
from __future__ import annotations

import glob
import multiprocessing as mp
import os
import subprocess
from pathlib import Path


def call_ncremap(cmd):
    """This is an internal function to `create_time_series`
    It just wraps the subprocess.call() function, so it can be
    used with the multiprocessing Pool that is constructed below.
    It is declared as global to avoid AttributeError.
    """
    return subprocess.run(cmd, shell=False)


def remap_time_series(
    component,
    diag_var_list,
    case_names,
    hist_str,
    ts_dir,
    start_years,
    end_years,
    mapping_files,
    num_procs,
    serial,
    logger,
):
    """
    Generate time series versions of the history file data.

    Args
    ----
     - component: str
         name of component, eg 'cam'
     - diag_var_list: list
         list of variables to create diagnostics (or timeseries) from
     - case_names: list, str
         name of simulaton case
     - hist_str: str
         CESM history number, ie h0, h1, etc.
     - ts_dir: list, str
         location where time series files will be saved, or pre-made time series files exist
     - start_years: list of ints
         first year for desired range of years
     - end_years: list of ints
         last year for desired range of years
     - mapping_files: list, str
         name of ESMF mapping files to use with ncremap
         (must be same length as case_names)
     - num_procs: int
         number of processors
     - serial: bool
         if True, run in serial; if False, run in parallel

    """

    # Don't do anything if list of requested diagnostics is empty
    if not diag_var_list:
        logger.info(f"\n  No variables to regrid for {component}...")
        return

    # Notify user that script has started:
    logger.info(f"\n  Regridding {component} time series files...")

    if isinstance(case_names, str):
        case_names = [case_names]
    if isinstance(mapping_files, str):
        mapping_files = [mapping_files]

    # Loop over cases:
    for case_idx, case_name in enumerate(case_names):
        logger.info(f"\t Regridding time series for case '{case_name}' :")
        if case_idx < len(mapping_files):
            mapping_file = mapping_files[case_idx]
        else:
            mapping_file = mapping_files[0]
        if mapping_file is None:
            logger.warning(f"[{__name__}]: no mapping file provided for {case_name}")
            continue

        for var in diag_var_list:

            ts_infile_str = (
                ts_dir[case_idx]
                + os.sep
                + ".".join([case_name, hist_str, var, "*", "nc"])
            )

            # Check if files already exist in time series directory:
            ts_file_list = glob.glob(ts_infile_str)

        list_of_commands = []
        for ts_file in ts_file_list:
            # Set up path to output file (creating toplevel dir if necessary)
            ts_file_nopath = os.path.basename(ts_file)
            ts_file_path = os.path.dirname(ts_file)
            out_file = os.path.join(ts_file_path, "regrid", ts_file_nopath)
            Path(os.path.dirname(out_file)).mkdir(parents=True, exist_ok=True)

            # Notify user that remapped file is being created
            if Path(out_file).is_file():
                logger.warning(
                    f"[{__name__}]: {out_file} exists and will not be overwritten",
                )
                continue
            logger.info(f"\t - regridding time series file {var}")

            cmd = ["ncremap", "-m", mapping_file, ts_file, out_file]

            # Add to command list for use in multi-processing pool:
            list_of_commands.append(cmd)

        if serial:
            for cmd in list_of_commands:
                call_ncremap(cmd)
        else:  # if not serial
            # Now run the "ncrcat" subprocesses in parallel:
            with mp.Pool(processes=num_procs) as mpool:
                _ = mpool.map(call_ncremap, list_of_commands)
            # End with
    # End cases loop

    # Notify user that script has ended:
    logger.info(
        f"  ... {component} time series file remapping has finished successfully.",
    )
