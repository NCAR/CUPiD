from __future__ import annotations

import glob
import json
import os.path
import shutil
import subprocess

import xarray as xr


def setup_run_mdtf(self):
    """
    Create MDTF directory tree, generate input settings jsonc file
    Submit MDTF diagnostics.
    Returns mdtf_proc for sub-process control (waits for it to finish in run_adf_diag)

    """

    copy_files_only = (
        False  # True (copy files but don't run), False (copy files and run MDTF)
    )
    # Note that the MDTF variable test_mode (set in the mdtf_info of the yaml file)
    # has a different meaning: Data is fetched but PODs are not run.

    print("\n  Setting up MDTF...")
    # We want access to the entire dict of mdtf_info
    mdtf_info = self.get_mdtf_info("ALL")
    verbose = mdtf_info["verbose"]

    #
    # Create a dict with all the case info needed for MDTF case_list
    #     Note that model and convention are hard-coded to CESM because that's all we expect here
    #     This could be changed by inputing them into ADF with other MDTF-specific variables
    #
    case_list_keys = ["CASENAME", "FIRSTYR", "LASTYR", "model", "convention"]

    # Casenames, paths and start/end years come through the ADF
    case_names = self.get_cam_info("cam_case_name", required=True)
    start_years = self.climo_yrs["syears"]
    end_years = self.climo_yrs["eyears"]

    case_list_all = []
    for icase, case in enumerate(case_names):
        case_list_values = [
            case,
            start_years[icase],
            end_years[icase],
            "CESM",
            "CESM",
        ]
        case_list_all.append(dict(zip(case_list_keys, case_list_values)))
    mdtf_info[
        "case_list"
    ] = case_list_all  # this list of dicts is the format wanted by MDTF

    # The plot_path is given by case in ADF but MDTF needs one top dir, so use case 0
    # Working dir and output dir can be different. These could be set in config.yaml
    # but then we don't get the nicely formated plot_location
    case_idx = 0
    plot_path = os.path.join(self.plot_location[case_idx], "mdtf")
    for var in ["WORKING_DIR", "OUTPUT_DIR"]:
        mdtf_info[var] = plot_path

    #
    # Write the input settings json file
    #
    mdtf_input_settings_filename = self.get_mdtf_info(
        "mdtf_input_settings_filename",
        required=True,
    )

    with open(
        mdtf_input_settings_filename,
        "w",
        encoding="utf-8",
    ) as out_file:
        json.dump(mdtf_info, out_file, sort_keys=True, indent=4, ensure_ascii=False)
    mdtf_codebase = self.get_mdtf_info("mdtf_codebase_loc")
    print(f"\t Using MDTF code base {mdtf_codebase}")

    #
    # Move the data to the dir structure and file names expected by the MDTF
    #    model_input_data/case/freq/case.VAR.freq.nc

    self.move_tsfiles_for_mdtf(verbose)

    #
    # Submit the MDTF script in background mode, send output to mdtf.out file
    #
    mdtf_log = "mdtf.out"  # maybe set this to cam_diag_plot_loc: /glade/scratch/${user}/ADF/plots
    mdtf_exe = mdtf_codebase + os.sep + "mdtf -f " + mdtf_input_settings_filename
    if copy_files_only:
        print("\t ...Copy files only. NOT Running MDTF")
        print(f"\t    Command: {mdtf_exe} Log: {mdtf_log}")
        return 0
    else:
        print(f"\t ...Running MDTF in background. Command: {mdtf_exe} Log: {mdtf_log}")
        print(f"Running MDTF in background. Command: {mdtf_exe} Log: {mdtf_log}")
        with open(mdtf_log, "w", encoding="utf-8") as subout:
            mdtf_proc_var = subprocess.Popen(
                [mdtf_exe],
                shell=True,
                stdout=subout,
                stderr=subout,
                close_fds=True,
            )
        return mdtf_proc_var


def move_tsfiles_for_mdtf(self, verbose):
    """
    Move ts files to the directory structure and names required by MDTF
    Should change with data catalogues
    """
    cam_ts_loc = self.get_cam_info("cam_ts_loc", required=True)
    self.expand_references({"cam_ts_loc": cam_ts_loc})
    if verbose > 1:
        print(f"\t Using timeseries files from {cam_ts_loc[0]}")

    mdtf_model_data_root = self.get_mdtf_info("MODEL_DATA_ROOT")

    # These MDTF words for day & month .But CESM will have hour_6 and hour_3, etc.
    # Going to need a dict to translate.
    # Use cesm_freq_strings = freq_string_options.keys
    # and then freq = freq_string_option(freq_string_found)
    freq_string_cesm = ["month", "day", "hour_6", "hour_3", "hour_1"]  # keys
    freq_string_options = ["month", "day", "6hr", "3hr", "1hr"]  # values
    freq_string_dict = dict(zip(freq_string_cesm, freq_string_options))  # make dict

    hist_str_list = self.get_cam_info("hist_str")
    case_names = self.get_cam_info("cam_case_name", required=True)
    var_list = self.diag_var_list

    for case_idx, case_name in enumerate(case_names):

        hist_str_case = hist_str_list[case_idx]
        for hist_str in hist_str_case:
            if verbose > 1:
                print(f"\t looking for {hist_str} in {cam_ts_loc[0]}")
            for var in var_list:

                #
                # Source file is ADF time series file
                #
                adf_file_str = (
                    cam_ts_loc[case_idx]
                    + os.sep
                    + ".".join([case_name, hist_str, var, "*"])
                )  # * to match timestamp: could be multiples
                adf_file_list = glob.glob(adf_file_str)

                if len(adf_file_list) == 1:
                    if verbose > 1:
                        print(f"Copying ts file: {adf_file_list} to MDTF dir")
                elif len(adf_file_list) > 1:
                    if verbose > 0:
                        print(
                            f"WARNING: found multiple timeseries files {adf_file_list}."
                            + "Continuing with best guess; suggest cleaning up multiple dates in ts dir",
                        )
                else:
                    if verbose > 1:
                        print(
                            f"WARNING: No files matching {case_name}.{hist_str}.{var}"
                            + "found in {adf_file_str}. Skipping",
                        )
                    continue  # skip this case/hist_str/var file
                adf_file = adf_file_list[0]

                # If freq is not set, it means we just started this hist_str. So check the first ADF file to find it
                hist_file_ds = xr.open_dataset(
                    adf_file,
                    decode_cf=False,
                    decode_times=False,
                )
                if "time_period_freq" in hist_file_ds.attrs:
                    dataset_freq = hist_file_ds.attrs["time_period_freq"]
                    if verbose > 2:
                        print(f"time_period_freq attribute found: {dataset_freq}")
                else:
                    if verbose > 0:
                        print(
                            "WARNING: Necessary 'time_period_freq' attribute missing"
                            + f" from {adf_file}. Skipping file.",
                        )
                    continue

                found_strings = [
                    word for word in freq_string_cesm if word in dataset_freq
                ]
                if len(found_strings) == 1:
                    if verbose > 2:
                        print(
                            f"Found dataset_freq {dataset_freq} matches {found_strings}",
                        )
                elif len(found_strings) > 1:
                    if verbose > 0:
                        print(
                            f"WARNING: Found dataset_freq {dataset_freq}"
                            + "matches multiple string possibilities:"
                            + f"{', '.join(found_strings)}",
                        )
                else:
                    if verbose > 0:
                        print(
                            "WARNING: None of the frequency options"
                            + f"{freq_string_cesm} are present in the time_period_freq"
                            + f"attribute {dataset_freq}",
                        )
                        print(f"Skipping {adf_file}")
                        freq = "frequency_missing"
                    continue
                freq = freq_string_dict.get(found_strings[0])
                print(f"Translated {found_strings[0]} to {freq}")

                #
                # Destination file is MDTF directory and name structure
                #
                mdtf_dir = os.path.join(mdtf_model_data_root, case_name, freq)

                os.makedirs(mdtf_dir, exist_ok=True)
                mdtf_file = mdtf_dir + os.sep + ".".join([case_name, var, freq, "nc"])
                mdtf_file_list = glob.glob(
                    mdtf_file,
                )  # Check if file already exists in MDTF directory
                if mdtf_file_list:  # If file exists, don't overwrite:
                    # To do in the future: add logic that says to over-write or not
                    if verbose > 1:
                        print(
                            f"\t   INFO: not clobbering existing mdtf file {mdtf_file_list}",
                        )
                    continue  # simply skip file copy for this variable:

                if verbose > 1:
                    print(f"copying {adf_file} to {mdtf_file}")
                shutil.copyfile(adf_file, mdtf_file)
            # end for hist_str
        # end for var
    # end for case
