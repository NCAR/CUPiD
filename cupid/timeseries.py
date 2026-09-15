"""
Timeseries generation tool adapted from ADF for general CUPiD use.
"""

# ++++++++++++++++++++++++++++++
# Import standard python modules
# ++++++++++++++++++++++++++++++
from __future__ import annotations

import glob
import os
from pathlib import Path

from gents.hfcollection import HFCollection
from gents.timeseries import TSCollection


def fix_permissions(
    filepath,
    file_mode,
    dir_mode,
    file_gid,
    dir_gid,
):
    """Fix file and directory permissions and groups"""
    os.chmod(
        filepath,
        file_mode,
    )  # change permissions to group specified in config file, eg rw for all
    os.chown(
        filepath,
        -1,
        file_gid,
    )  # change group to group specified in config file, eg, 'cesm' gid 1017
    dirpath = ""
    for segment in filepath.split("/")[:-1]:
        dirpath = dirpath + "/" + segment
    os.chmod(
        dirpath,
        dir_mode,
    )  # This changes the tseries directory permission multiple times
    #    if multiple files are in same directory, so efficiency could certainly be improved
    os.chown(dirpath, -1, dir_gid)


def create_time_series(
    component,
    diag_var_list,
    derive_vars,
    case_names,
    hist_str,
    hist_locs,
    ts_dir,
    ts_done,
    overwrite_ts,
    start_years,
    end_years,
    height_dim,
    num_procs,
    serial,
    logger,
    file_mode,
    dir_mode,
    file_gid,
    dir_gid,
):
    """
    Generate time series versions of the history file data. Called by ``cupid-timeseries``.

    Delegates to GenTS, which discovers the history files, reads their time
    metadata, and writes one file per variable. Output is named
    ``{case}.{hist_str}.{var}.{YYYYMM-YYYYMM}.nc`` inside ``ts_dir``.

    Args
    ----
     - component: str
         name of component, eg 'cam'
     - diag_var_list: list
         variables to create diagnostics (or timeseries) from; the sentinel
         ``['process_all']`` requests every primary variable in the history files
     - derive_vars: dict
         information on derivable variables
         eg, {'PRECT': ['PRECL','PRECC'],
              'RESTOM': ['FLNT','FSNT']}
         GenTS performs no computation, so these are derived afterwards by
         ``derive_cam_variables``; only their constituents are generated here.
     - case_names: list, str
         name of simulaton case
     - hist_str: str
         CESM history number, ie h0, h1, etc.
     - hist_locs: list, str
         location of CESM history files
     - ts_dir: list, str
         location where time series files will be saved, or pre-made time series files exist
     - ts_done: list, boolean
         check if time series files already exist
     - overwrite_ts: list, boolean
         check if existing time series files will bew overwritten
     - start_years: list of ints
         first year for desired range of years
     - end_years: list of ints
         last year for desired range of years
     - height_dim: str
         name of height dimension for given component, eg 'lev'. Unused: GenTS
         classifies variables by dimensionality, so vertical coordinates
         (hyam/hybm/hyai/hybi) are carried into every output file automatically.
     - num_procs: int
         number of processors
     - serial: bool
         if True, run in serial; if False, run in parallel

    """

    # Don't do anything if list of requested diagnostics is empty
    if not diag_var_list:
        logger.info(f"\n  No time series files requested for {component}...")
        return

    # Notify user that script has started:
    logger.info(f"\n  Generating {component} time series files...")

    num_processes = 1 if serial else num_procs
    generated_files = []

    for case_idx, case_name in enumerate(case_names):
        # Check if particular case should be processed:
        if ts_done[case_idx]:
            emsg = (
                "Configuration file indicates time series files have been pre-computed"
            )
            emsg += f" for case '{case_name}'.  Will rely on those files directly."
            logger.info(emsg)
            continue

        logger.info(f"\t Processing time series for case '{case_name}' :")

        hist_loc = str(Path(hist_locs[case_idx]))
        out_dir = str(Path(ts_dir[case_idx]))

        try:
            hf_collection = HFCollection(
                hist_loc,
                num_processes=num_processes,
            ).include(f"*.{hist_str}.*")
        except FileNotFoundError:
            hf_collection = None

        if hf_collection is None or len(hf_collection) == 0:
            wmsg = (
                f"WARNING: No history files matching '*.{hist_str}.*' in '{hist_loc}'."
            )
            wmsg += f" No {component} time series generated for case '{case_name}'."
            logger.warning(wmsg)
            continue

        hf_collection.pull_metadata(show_progress=False)
        hf_collection = hf_collection.include_years(
            start_years[case_idx],
            end_years[case_idx],
        )
        if len(hf_collection) == 0:
            wmsg = f"WARNING: No {hist_str} history files fall within years"
            wmsg += f" {start_years[case_idx]}-{end_years[case_idx]} for case '{case_name}'."
            logger.warning(wmsg)
            continue

        ts_collection = TSCollection(
            hf_collection,
            out_dir,
            num_processes=num_processes,
        )

        vars_to_derive = []
        if diag_var_list == ["process_all"]:
            logger.info("generating time series for all variables")
        else:
            requested = set(diag_var_list)
            for var in diag_var_list:
                if var in derive_vars:
                    requested.update(derive_vars[var])
                    requested.discard(var)
                    vars_to_derive.append(var)

            available = {order["primary_var"] for order in ts_collection}
            for var in sorted(requested - available):
                wmsg = f"WARNING: {var} is not in the {hist_str} history files."
                wmsg += " No time series will be generated."
                logger.warning(wmsg)

            ts_collection = ts_collection.copy(
                ts_orders=[
                    order
                    for order in ts_collection
                    if order["primary_var"] in requested
                ],
            )

        if overwrite_ts[case_idx]:
            ts_collection = ts_collection.apply_overwrite("*")

        for order in ts_collection:
            logger.info(f"\t - time series for {order['primary_var']}")

        generated_files += ts_collection.execute(show_progress=False)

        # Derived vars need the previously-generated time series files
        if vars_to_derive:
            if component == "atm":
                derive_cam_variables(
                    logger,
                    vars_to_derive=vars_to_derive,
                    ts_dir=ts_dir[case_idx],
                )

    # End cases loop

    for file_i in generated_files:
        fix_permissions(file_i, file_mode, dir_mode, file_gid, dir_gid)

    logger.info(
        f"  ... {component} time series file generation has finished successfully.",
    )


def derive_cam_variables(logger, vars_to_derive=None, ts_dir=None, overwrite=None):
    """
    Derive variables acccording to steps given here.  Since derivations will depend on the
    variable, each variable to derive will need its own set of steps below.

    Caution: this method assumes that there will be one time series file per variable

    If the file for the derived variable exists, the kwarg `overwrite` determines
    whether to overwrite the file (true) or exit with a warning message.
    """

    for var in vars_to_derive:
        if var == "PRECT":
            # PRECT can be found by simply adding PRECL and PRECC
            # grab file names for the PRECL and PRECC files from the case ts directory
            if glob.glob(os.path.join(ts_dir, "*PRECC*")) and glob.glob(
                os.path.join(ts_dir, "*PRECL*"),
            ):
                constit_files = sorted(glob.glob(os.path.join(ts_dir, "*PREC*")))
            else:
                ermsg = (
                    "PRECC and PRECL were not both present; PRECT cannot be calculated."
                )
                ermsg += " Please remove PRECT from diag_var_list or find the relevant CAM files."
                raise FileNotFoundError(ermsg)

            # create new file name for PRECT
            prect_file = constit_files[0].replace("PRECC", "PRECT")
            if Path(prect_file).is_file():
                if overwrite:
                    Path(prect_file).unlink()
                else:
                    logger.warning(
                        f"[{__name__}] Warning: PRECT file was found and overwrite is False"
                        + "Will use existing file.",
                    )
                    continue

            # append PRECC to the file containing PRECL
            os.system(f"ncks -A -v PRECC {constit_files[0]} {constit_files[1]}")
            # create new file with the sum of PRECC and PRECL
            os.system(f"ncap2 -s 'PRECT=(PRECC+PRECL)' {constit_files[1]} {prect_file}")

        if var == "RESTOM":
            # RESTOM = FSNT-FLNT
            # Have to be more precise than with PRECT because FSNTOA, FSTNC, etc are valid variables
            if glob.glob(os.path.join(ts_dir, "*.FSNT.*")) and glob.glob(
                os.path.join(ts_dir, "*.FLNT.*"),
            ):
                input_files = [
                    sorted(glob.glob(os.path.join(ts_dir, f"*.{v}.*")))
                    for v in ["FLNT", "FSNT"]
                ]
                constit_files = []
                for elem in input_files:
                    constit_files += elem
            else:
                ermsg = (
                    "FSNT and FLNT were not both present; RESTOM cannot be calculated."
                )
                ermsg += " Please remove RESTOM from diag_var_list or find the relevant CAM files."
                raise FileNotFoundError(ermsg)

            # create new file name for RESTOM
            derived_file = constit_files[0].replace("FLNT", "RESTOM")
            if Path(derived_file).is_file():
                if overwrite:
                    Path(derived_file).unlink()
                else:
                    logger.warning(
                        f"[{__name__}] Warning: RESTOM file was found and overwrite is False."
                        + "Will use existing file.",
                    )
                    continue

            # append FSNT to the file containing FLNT
            os.system(f"ncks -A -v FLNT {constit_files[0]} {constit_files[1]}")
            # create new file with the difference of FLNT and FSNT
            os.system(
                f"ncap2 -s 'RESTOM=(FSNT-FLNT)' {constit_files[1]} {derived_file}",
            )
