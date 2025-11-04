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

import xarray as xr


def call_ncrcat(cmd):
    """This is an internal function to `create_time_series`
    It just wraps the subprocess.call() function, so it can be
    used with the multiprocessing Pool that is constructed below.
    It is declared as global to avoid AttributeError.
    """
    return subprocess.run(cmd, shell=False)


def fix_permissions(path):
    """Fix file permissions and group to 'cesm'."""
    for root, dirs, files in os.walk(path):
        for d in dirs:  # fix dirs
            dpath = os.path.join(root, d)
            os.chmod(dpath, 0o755)  # rwx for owner, rx for group/others
            os.chown(dpath, -1, "cesm")  # change group only

        for f in files:  # fix files
            fpath = os.path.join(root, f)
            os.chmod(fpath, 0o666)  # rw for all
            os.chown(fpath, -1, "cesm")  # change group only


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
):
    """
    Generate time series versions of the history file data. Called by ``cupid-timeseries``.

    Args
    ----
     - component: str
         name of component, eg 'cam'
         # This could also be made into a dict and encorporate values such as height_dim
     - derive_vars: dict
         information on derivable variables
         eg, {'PRECT': ['PRECL','PRECC'],
              'RESTOM': ['FLNT','FSNT']}
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
         name of height dimension for given component, eg 'lev'
     - num_procs: int
         number of processors
     - diag_var_list: list
         list of variables to create diagnostics (or timeseries) from
     - serial: bool
         if True, run in serial; if False, run in parallel

    """

    # Don't do anything if list of requested diagnostics is empty
    if not diag_var_list:
        logger.info(f"\n  No time series files requested for {component}...")
        return

    # Notify user that script has started:
    logger.info(f"\n  Generating {component} time series files...")

    # Loop over cases:
    for case_idx, case_name in enumerate(case_names):
        # Check if particular case should be processed:
        if ts_done[case_idx]:
            emsg = (
                "Configuration file indicates time series files have been pre-computed"
            )
            emsg += f" for case '{case_name}'.  Will rely on those files directly."
            logger.info(emsg)
            continue
        # End if

        logger.info(f"\t Processing time series for case '{case_name}' :")

        # Extract start and end year values:
        start_year = start_years[case_idx]
        end_year = end_years[case_idx]

        # Create path object for the history file(s) location:
        starting_location = Path(hist_locs[case_idx])

        # Check that path actually exists:
        if not starting_location.is_dir():
            emsg = f"Provided 'cam_hist_loc' directory '{starting_location}' not found."
            emsg += " Script is ending here."

            raise FileNotFoundError(emsg)
        # End if

        # Check if history files actually exist. If not then kill script:
        if not list(starting_location.glob("*." + hist_str + ".*.nc")):
            emsg = f"No history *.{hist_str}.*.nc files found in '{starting_location}'."
            emsg += " Script is ending here."
            raise FileNotFoundError(emsg)
        # End if

        # Create empty list:
        files_list = []

        # Loop over start and end years:
        for year in range(start_year, end_year + 1):
            # Add files to main file list:
            for fname in starting_location.glob(
                f"*.{hist_str}.*{str(year).zfill(4)}*.nc",
            ):
                files_list.append(fname)
            # End for
        # End for

        # Create ordered list of CAM history files:
        hist_files = sorted(files_list)

        # Open an xarray dataset from the first model history file:
        hist_file_ds = xr.open_dataset(
            hist_files[0],
            decode_cf=False,
            decode_times=False,
        )

        # Get a list of data variables in the 1st hist file:
        hist_file_var_list = list(hist_file_ds.data_vars)
        # Note: could use `open_mfdataset`, but that can become very slow;
        #      This approach effectively assumes that all files contain the same variables.

        # Check what kind of vertical coordinate (if any) is being used for this model run:
        # ------------------------
        if height_dim in hist_file_ds:
            # Extract vertical level attributes:
            lev_attrs = hist_file_ds[height_dim].attrs

            # First check if there is a "vert_coord" attribute:
            if "vert_coord" in lev_attrs:
                vert_coord_type = lev_attrs["vert_coord"]
            else:
                # Next check that the "long_name" attribute exists:
                if "long_name" in lev_attrs:
                    # Extract long name:
                    lev_long_name = lev_attrs["long_name"]

                    # Check for "keywords" in the long name:
                    if "hybrid level" in lev_long_name:
                        # Set model to hybrid vertical levels:
                        vert_coord_type = "hybrid"
                    elif "zeta level" in lev_long_name:
                        # Set model to height (z) vertical levels:
                        vert_coord_type = "height"
                    else:
                        # Print a warning, and assume that no vertical
                        # level information is needed.
                        wmsg = "WARNING! Unable to determine the vertical coordinate"
                        wmsg += f" type from the {height_dim} long name, \n'{lev_long_name}'."
                        wmsg += (
                            "\nNo additional vertical coordinate information will be"
                        )
                        wmsg += (
                            f" transferred beyond the {height_dim} dimension itself."
                        )
                        logger.warning(wmsg)

                        vert_coord_type = None
                    # End if
                else:
                    # Print a warning, and assume hybrid levels (for now):
                    wmsg = (
                        f"WARNING!  No long name found for the {height_dim} dimension,"
                    )
                    wmsg += " so no additional vertical coordinate information will be"
                    wmsg += f" transferred beyond the {height_dim} dimension itself."
                    logger.warning(wmsg)

                    vert_coord_type = None
                # End if (long name)
            # End if (vert_coord)
        else:
            # No level dimension found, so assume there is no vertical coordinate:
            vert_coord_type = None
        # End if (lev, or height_dim, existence)
        # ------------------------

        # Check if time series directory exists, and if not, then create it:
        # Use pathlib to create parent directories, if necessary.
        Path(ts_dir[case_idx]).mkdir(parents=True, exist_ok=True)

        # INPUT NAME TEMPLATE: $CASE.$scomp.[$type.][$string.]$date[$ending]
        first_file_split = str(hist_files[0]).split(".")
        if first_file_split[-1] == "nc":
            time_string_start = first_file_split[-2].replace("-", "")
        else:
            time_string_start = first_file_split[-1].replace("-", "")
        last_file_split = str(hist_files[-1]).split(".")
        if last_file_split[-1] == "nc":
            time_string_finish = last_file_split[-2].replace("-", "")
        else:
            time_string_finish = last_file_split[-1].replace("-", "")
        time_string = "-".join([time_string_start, time_string_finish])

        # Loop over history variables:
        list_of_commands = []
        vars_to_derive = []
        # create copy of var list that can be modified for derivable variables
        if diag_var_list == ["process_all"]:
            logger.info("generating time series for all variables")
            # TODO: this does not seem to be working for ocn...
            diag_var_list = hist_file_var_list
        for var in diag_var_list:
            if var not in hist_file_var_list:
                if component == "ocn":
                    logger.warning(
                        "ocean vars seem to not be present in all files and thus cause errors",
                    )
                    continue
                if (
                    var in derive_vars
                ):  # TODO: dictionary implementation needs to be fixed with yaml file
                    constit_list = derive_vars[var]
                    for constit in constit_list:
                        if constit not in diag_var_list:
                            diag_var_list.append(constit)
                    vars_to_derive.append(var)
                    continue
                msg = f"WARNING: {var} is not in the file {hist_files[0]}."
                msg += " No time series will be generated."
                logger.warning(msg)
                continue

            # Check if variable has a height_dim (eg, 'lev') dimension according to first file:
            has_lev = bool(height_dim in hist_file_ds[var].dims)

            # Create full path name, file name template:
            # $cam_case_name.$hist_str.$variable.YYYYMM-YYYYMM.nc

            ts_outfil_str = (
                ts_dir[case_idx]
                + os.sep
                + ".".join([case_name, hist_str, var, time_string, "nc"])
            )

            # Check if files already exist in time series directory:
            ts_file_list = glob.glob(ts_outfil_str)

            # If files exist, then check if over-writing is allowed:
            if ts_file_list:
                if not overwrite_ts[case_idx]:
                    # If not, then simply skip this variable:
                    continue

            # Notify user of new time series file:
            logger.info(f"\t - time series for {var}")

            # Variable list starts with just the variable
            ncrcat_var_list = f"{var}"

            # Determine "ncrcat" command to generate time series file:
            if "date" in hist_file_ds[var].dims:
                ncrcat_var_list = ncrcat_var_list + ",date"
            if "datesec" in hist_file_ds[var].dims:
                ncrcat_var_list = ncrcat_var_list + ",datesec"

            if has_lev and vert_coord_type:
                # For now, only add these variables if using CAM:
                if "cam" in hist_str:  # Could also use if "cam" in component
                    # PS might be in a different history file. If so, continue without error.
                    ncrcat_var_list = ncrcat_var_list + ",hyam,hybm,hyai,hybi"

                    if "PS" in hist_file_var_list:
                        ncrcat_var_list = ncrcat_var_list + ",PS"
                        logger.info("Adding PS to file")
                    else:
                        wmsg = "WARNING: PS not found in history file."
                        wmsg += " It might be needed at some point."
                        logger.warning(wmsg)
                    # End if

                    if vert_coord_type == "height":
                        # Adding PMID here works, but significantly increases
                        # the storage (disk usage) requirements of the ADF.
                        # This can be alleviated in the future by figuring out
                        # a way to determine all of the regridding targets at
                        # the start of the ADF run, and then regridding a single
                        # PMID file to each one of those targets separately. -JN
                        if "PMID" in hist_file_var_list:
                            ncrcat_var_list = ncrcat_var_list + ",PMID"
                            logger.info("Adding PMID to file")
                        else:
                            wmsg = "WARNING: PMID not found in history file."
                            wmsg += " It might be needed at some point."
                            logger.warning(wmsg)
                        # End if PMID
                    # End if height
                # End if cam
            # End if has_lev

            cmd = (
                ["ncrcat", "-O", "-4", "-h", "--no_cll_mth", "-v", ncrcat_var_list]
                + hist_files
                + ["-o", ts_outfil_str]
            )

            # TODO: probably would be better to do at dir level...
            # Could go up a level but may run into other file owners--
            # which could be addressed with try/except but may be messy
            fix_permissions(ts_outfil_str)

            # Add to command list for use in multi-processing pool:
            list_of_commands.append(cmd)

        # End variable loop

        if vars_to_derive:
            if component == "atm":
                derive_cam_variables(
                    logger,
                    vars_to_derive=vars_to_derive,
                    ts_dir=ts_dir[case_idx],
                )

        if serial:
            for cmd in list_of_commands:
                call_ncrcat(cmd)
        else:  # if not serial
            # Now run the "ncrcat" subprocesses in parallel:
            with mp.Pool(processes=num_procs) as mpool:
                _ = mpool.map(call_ncrcat, list_of_commands)
            # End with
    # End cases loop

    # Notify user that script has ended:
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
