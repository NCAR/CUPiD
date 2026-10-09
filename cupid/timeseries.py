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
    try:
        os.chmod(
            filepath,
            file_mode,
        )  # change permissions to group specified in config file, eg rw for all
        os.chown(
            filepath,
            -1,
            file_gid,
        )  # change group to group specified in config file, eg, 'cesm' gid 1017
    except PermissionError:
        print(f"WARNING: can not change permissions or group on {filepath}")
    dirpath = ""
    for segment in filepath.split("/")[:-1]:
        dirpath = dirpath + "/" + segment
    try:
        os.chmod(
            dirpath,
            dir_mode,
        )  # This changes the tseries directory permission multiple times
        #    if multiple files are in same directory, so efficiency could certainly be improved
        os.chown(dirpath, -1, dir_gid)
    except PermissionError:
        print(f"WARNING: can not change permissions or group on {dirpath}")


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
    slice_size,
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
         if True, regenerate existing time series files (and derived variables);
         if False, skip time steps already covered by complete time series files
     - start_years: list of ints
         first year for desired range of years
     - end_years: list of ints
         last year for desired range of years
     - height_dim: str
         name of height dimension for given component, eg 'lev'. Unused: GenTS
         classifies variables by dimensionality, so vertical coordinates
         (hyam/hybm/hyai/hybi) are carried into every output file automatically.
     - slice_size: list of ints
         number of years per time series file, one entry per case; windows are
         aligned to the case's start year
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

        hist_loc = hist_locs[case_idx]
        out_dir = ts_dir[case_idx]

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

        hf_collection = hf_collection.pull_metadata(show_progress=False)
        hf_collection = hf_collection.include_years(
            start_years[case_idx],
            end_years[case_idx],
        )
        hf_collection = hf_collection.slice_groups(
            slice_size_years=slice_size[case_idx],
            start_year=start_years[case_idx],
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

            ts_collection = ts_collection.include("*", var_glob=sorted(requested))

        if overwrite_ts[case_idx]:
            ts_collection = ts_collection.apply_overwrite("*")
        else:
            ts_collection = ts_collection.skip_existing()

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
                    overwrite=overwrite_ts[case_idx],
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

    Each time series file of a constituent variable yields one derived file, so
    sliced or continued output is handled per slice.

    If the file for the derived variable exists, the kwarg `overwrite` determines
    whether to overwrite the file (true) or exit with a warning message.
    """

    for var in vars_to_derive:
        if var == "PRECT":
            precc_files = []
            precl_files = []
            for precc_file in sorted(glob.glob(os.path.join(ts_dir, "*.PRECC.*"))):
                precl_file = precc_file.replace(".PRECC.", ".PRECL.")
                if os.path.isfile(precl_file):
                    precc_files.append(precc_file)
                    precl_files.append(precl_file)
            if not precc_files:
                ermsg = (
                    "PRECC and PRECL were not both present; PRECT cannot be calculated."
                )
                ermsg += " Please remove PRECT from diag_var_list or find the relevant CAM files."
                raise FileNotFoundError(ermsg)

            for precc_file, precl_file in zip(precc_files, precl_files):
                prect_file = precc_file.replace(".PRECC.", ".PRECT.")
                if Path(prect_file).is_file():
                    if overwrite:
                        Path(prect_file).unlink()
                    else:
                        logger.warning(
                            f"[{__name__}] Warning: PRECT file was found and overwrite is False."
                            + " Will use existing file.",
                        )
                        continue

                # Copy PRECL file to PRECT file, leaving the GenTS output untouched
                os.system(f"cp {precl_file} {prect_file}")
                # append PRECC to the PRECT file (it now has PRECL and PRECC)
                os.system(f"ncks -A -v PRECC {precc_file} {prect_file}")
                # compute PRECT = PRECC + PRECL in new file
                os.system(f"ncap2 -A -s 'PRECT=(PRECC+PRECL)' {prect_file}")

        if var == "RESTOM":
            # RESTOM = FSNT-FLNT
            # Have to be more precise than with PRECT because FSNTOA, FSTNC, etc are valid variables
            # TODO: can GenTS provide a list of files it just created?
            fsnt_file_glob = glob.glob(os.path.join(ts_dir, "*.FSNT.*"))
            fsnt_files = []
            flnt_files = []
            for fsnt_file in fsnt_file_glob:
                flnt_file = fsnt_file.replace(".FSNT.", ".FLNT.")
                if os.path.isfile(flnt_file):
                    fsnt_files.append(fsnt_file)
                    flnt_files.append(flnt_file)
            if not fsnt_files or not flnt_files:
                #     input_files = [
                #         sorted(glob.glob(os.path.join(ts_dir, f"*.{v}.*")))
                #         for v in ["FLNT", "FSNT"]
                #     ]
                #     constit_files = []
                #     for elem in input_files:
                #         constit_files += elem
                # else:
                ermsg = (
                    "FSNT and FLNT were not both present; RESTOM cannot be calculated."
                )
                ermsg += " Please remove RESTOM from diag_var_list or find the relevant CAM files."
                raise FileNotFoundError(ermsg)

            # create new file name for RESTOM
            for fsnt_file, flnt_file in zip(fsnt_files, flnt_files):
                restom_file = fsnt_file.replace("FSNT", "RESTOM")
                if Path(restom_file).is_file():
                    if overwrite:
                        Path(restom_file).unlink()
                    else:
                        logger.warning(
                            f"[{__name__}] Warning: RESTOM file was found and overwrite is False."
                            + "Will use existing file.",
                        )
                        continue

                # Copy FLNT file to RESTOM file
                # TODO: this creates a RESTOM file that also contains FLNT and FSNT;
                #       should we start by creating a temporary file and remove
                #       those variables in the final version?
                os.system(f"cp {flnt_file} {restom_file}")
                # append FSNT to the RESTOM file (it now has FLNT and FSNT)
                os.system(f"ncks -A -v FSNT {fsnt_file} {restom_file}")
                # compute RESTOM = FSNT-FLNT in new file
                os.system(f"ncap2 -A -s 'RESTOM=(FSNT-FLNT)' {restom_file}")
                # modify longname attribute of RESTOM
                os.system(
                    f'ncatted -a long_name,RESTOM,m,c,"Residual energy flux at top of model" {restom_file}',
                )
