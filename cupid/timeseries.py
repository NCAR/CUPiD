def create_time_series(case_names, hist_str, hist_locs, ts_dir, ts_done, overwrite_ts, start_years, end_years):
    """
    Generate time series versions of the history file data.

    Args
    ----
     - case_names: list, str
         name of simulaton case
     - hist_str: str
         CESM history number, ie h0, h1, etc.
     - hist_locs: list, str
         location of CESM history files
     - ts_dir: list, str
         location where time series files will be saved, or where pre-made time series files exist
     - ts_done: list, boolean
         check if time series files already exist
     - overwrite_ts: list, boolean
         check if existing time series files will bew overwritten
     - start_years: list, str or int
         first year for desired range of years
     - end_years: list, str or int
         last year for desired range of years
    
    """

    global call_ncrcat

    def call_ncrcat(cmd):
        """this is an internal function to `create_time_series`
        It just wraps the subprocess.call() function, so it can be
        used with the multiprocessing Pool that is constructed below.
        It is declared as global to avoid AttributeError.
        """
        return subprocess.run(cmd, shell=False)

    # End def

    # Notify user that script has started:
    print("\n  Generating time series files...")

    # get info about variable defaults
    res = self.variable_defaults

    # Loop over cases:
    for case_idx, case_name in enumerate(case_names):
        # Check if particular case should be processed:
        if ts_done[case_idx]:
            emsg = " Configuration file indicates time series files have been pre-computed"
            emsg += f" for case '{case_name}'.  Will rely on those files directly."
            print(emsg)
            continue
        # End if

        print(f"\t Processing time series for case '{case_name}' :")

        # Extract start and end year values:
        start_year = start_years[case_idx]
        end_year = end_years[case_idx]

        # Create path object for the history file(s) location:
        starting_location = Path(hist_locs[case_idx])

        # Check that path actually exists:
        if not starting_location.is_dir():
            emsg = "Provided 'cam_hist_loc' directory '{starting_location}' not found."
            emsg += " Script is ending here."
            # End if

            self.end_diag_fail(emsg)
        # End if

        # Check if history files actually exist. If not then kill script:
        if not list(starting_location.glob("*" + hist_str + ".*.nc")):
            emsg = (
                f"No history *{hist_str}.*.nc files found in '{starting_location}'."
            )
            emsg += " Script is ending here."
            self.end_diag_fail(emsg)
        # End if

        # Create empty list:
        files_list = []

        # Loop over start and end years:
        for year in range(start_year, end_year + 1):
            # Add files to main file list:
            for fname in starting_location.glob(
                f"*{hist_str}.*{str(year).zfill(4)}*.nc"
            ):
                files_list.append(fname)
            # End for
        # End for

        # Create ordered list of CAM history files:
        hist_files = sorted(files_list)

        # Open an xarray dataset from the first model history file:
        hist_file_ds = xr.open_dataset(
            hist_files[0], decode_cf=False, decode_times=False
        )

        # Get a list of data variables in the 1st hist file:
        hist_file_var_list = list(hist_file_ds.data_vars)
        # Note: could use `open_mfdataset`, but that can become very slow;
        #      This approach effectively assumes that all files contain the same variables.


        # Check what kind of vertical coordinate (if any) is being used for this model run:
        # ------------------------
        if "lev" in hist_file_ds:
            # Extract vertical level attributes:
            lev_attrs = hist_file_ds["lev"].attrs

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
                        wmsg = (
                            "WARNING! Unable to determine the vertical coordinate"
                        )
                        wmsg += f" type from the 'lev' long name, which is:\n'{lev_long_name}'."
                        wmsg += "\nNo additional vertical coordinate information will be"
                        wmsg += " transferred beyond the 'lev' dimension itself."
                        print(wmsg)

                        vert_coord_type = None
                    # End if
                else:
                    # Print a warning, and assume hybrid levels (for now):
                    wmsg = "WARNING!  No long name found for the 'lev' dimension,"
                    wmsg += (
                        " so no additional vertical coordinate information will be"
                    )
                    wmsg += " transferred beyond the 'lev' dimension itself."
                    print(wmsg)

                    vert_coord_type = None
                # End if (long name)
            # End if (vert_coord)
        else:
            # No level dimension found, so assume there is no vertical coordinate:
            vert_coord_type = None
        # End if (lev existence)
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
        diag_var_list = self.diag_var_list
        for var in diag_var_list:
            if var not in hist_file_var_list:
                vres = res.get(var, {})
                if "derivable_from" in vres:
                    constit_list = vres["derivable_from"]
                    for constit in constit_list:
                        if constit not in diag_var_list:
                            diag_var_list.append(constit)
                    vars_to_derive.append(var)
                    continue
                else:
                    msg = f"WARNING: {var} is not in the file {hist_files[0]}."
                    msg += " No time series will be generated."
                    print(msg)
                    continue

            # Check if variable has a "lev" dimension according to first file:
            has_lev = bool("lev" in hist_file_ds[var].dims)

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
            print(f"\t - time series for {var}")

            # Variable list starts with just the variable
            ncrcat_var_list = f"{var}"

            # Determine "ncrcat" command to generate time series file:
            if "date" in hist_file_ds[var].dims:
                ncrcat_var_list = ncrcat_var_list + ",date"
            if "datesec" in hist_file_ds[var].dims:
                ncrcat_var_list = ncrcat_var_list + ",datesec"

            if has_lev and vert_coord_type:
                # For now, only add these variables if using CAM:
                if "cam" in hist_str:
                    # PS might be in a different history file. If so, continue without error.
                    ncrcat_var_list = ncrcat_var_list + ",hyam,hybm,hyai,hybi"

                    if "PS" in hist_file_var_list:
                        ncrcat_var_list = ncrcat_var_list + ",PS"
                        print("Adding PS to file")
                    else:
                        wmsg = "WARNING: PS not found in history file."
                        wmsg += " It might be needed at some point."
                        print(wmsg)
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
                            print("Adding PMID to file")
                        else:
                            wmsg = "WARNING: PMID not found in history file."
                            wmsg += " It might be needed at some point."
                            print(wmsg)
                        # End if PMID
                    # End if height
                # End if cam
            # End if has_lev

            cmd = (
                ["ncrcat", "-O", "-4", "-h", "--no_cll_mth", "-v", ncrcat_var_list]
                + hist_files
                + ["-o", ts_outfil_str]
            )

            # Add to command list for use in multi-processing pool:
            list_of_commands.append(cmd)

        # End variable loop

        # Now run the "ncrcat" subprocesses in parallel:
        with mp.Pool(processes=self.num_procs) as mpool:
            _ = mpool.map(call_ncrcat, list_of_commands)

        if vars_to_derive:
            self.derive_variables(
                vars_to_derive=vars_to_derive, ts_dir=ts_dir[case_idx]
            )
        # End with

    # End cases loop

    # Notify user that script has ended:
    print("  ...time series file generation has finished successfully.")
