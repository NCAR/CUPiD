#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import yaml


def _parse_args():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description="Generate cupid_adf_config.yml based on an existing CUPID YAML file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--cupid_file",
        action="store",
        required=True,
        help="CUPID YAML file",
    )
    parser.add_argument(
        "--adf_template",
        action="store",
        required=True,
        help="an adf config file to use as a base",
    )
    parser.add_argument(
        "--out_file",
        action="store",
        required=True,
        help="the output file to save",
    )
    return parser.parse_args()


def generate_adf_config(cupid_file, adf_file, out_file):
    """Use cupid_file (YAML) and adf_file (YAML) to produce out_file
    by modifying adf_file with data from cupid_file.
    """
    with open(cupid_file, encoding="UTF-8") as c:
        c_dict = yaml.load(c, Loader=yaml.SafeLoader)
    with open(adf_file, encoding="UTF-8") as a:
        a_dict = yaml.load(a, Loader=yaml.SafeLoader)

    # read parameters from CUPID
    # use `get` to default to None
    DOUT = c_dict["global_params"]["CESM_output_dir"]
    base_case_name = c_dict["global_params"].get("base_case_name")
    test_case_name = c_dict["global_params"]["case_name"]
    c_ts = c_dict["timeseries"]
    ts_case_names = c_ts.get("case_name")
    if not ts_case_names:
        raise ValueError("CUPiD file does not have timeseries case_name array.")

    # Set case names for ADF config
    a_dict["diag_cam_climo"]["cam_case_name"] = test_case_name
    a_dict["diag_cam_baseline_climo"]["cam_case_name"] = base_case_name

    # TEST CASE HISTORY FILE PATH
    a_dict["diag_cam_climo"]["cam_hist_loc"] = "/".join([DOUT, "atm", "hist"])
    # TEST CASE TIME SERIES FILE PATH
    a_dict["diag_cam_climo"]["cam_ts_loc"] = "/".join([DOUT, "proc", "tseries"])
    # TEST CASE CLIMO FILE PATH
    a_dict["diag_cam_climo"]["cam_climo_loc"] = "/".join([DOUT, "proc", "climo"])
    # TEST CASE START / END YEARS
    test_case_cupid_ts_index = (
        ts_case_names.index(test_case_name) if test_case_name in ts_case_names else None
    )
    start_date = get_date_from_ts(c_ts["atm"], "start_years", test_case_cupid_ts_index)
    end_date = get_date_from_ts(c_ts["atm"], "end_years", test_case_cupid_ts_index)
    a_dict["diag_cam_climo"]["start_year"] = start_date
    a_dict["diag_cam_climo"]["end_year"] = end_date

    # Set values for BASELINE
    base_case_cupid_ts_index = (
        ts_case_names.index(base_case_name) if base_case_name in ts_case_names else None
    )
    if base_case_name is not None:
        base_case_output_dir = c_dict["global_params"].get("base_case_output_dir", DOUT)
        base_start_date = get_date_from_ts(
            c_ts["atm"],
            "start_years",
            base_case_cupid_ts_index,
        )
        base_end_date = get_date_from_ts(
            c_ts["atm"],
            "end_years",
            base_case_cupid_ts_index,
        )
        if base_start_date is None:
            base_start_date = start_date
        if base_end_date is None:
            base_end_date = end_date

    a_dict["diag_cam_baseline_climo"]["cam_hist_loc"] = "/".join(
        [base_case_output_dir, "atm", "hist"],
    )
    a_dict["diag_cam_baseline_climo"]["cam_ts_loc"] = "/".join(
        [base_case_output_dir, "proc", "tseries"],
    )
    a_dict["diag_cam_baseline_climo"]["cam_climo_loc"] = "/".join(
        [base_case_output_dir, "proc", "climo"],
    )
    a_dict["diag_cam_baseline_climo"]["start_year"] = base_start_date
    a_dict["diag_cam_baseline_climo"]["end_year"] = base_end_date

    a_dict["diag_basic_info"]["num_procs"] = c_dict["timeseries"].get("num_procs", 1)
    a_dict["diag_basic_info"]["cam_regrid_loc"] = "/".join(
        [DOUT, "proc", "regrid"],
    )  # This is where ADF will make "regrid" files
    a_dict["diag_basic_info"]["cam_diag_plot_loc"] = "/".join(
        [c_dict["data_sources"]["sname"], "ADF"],  # TODO: update this
    )  # this is where ADF will put plots, and "website" directory
    a_dict["user"] = os.getenv("USER")

    with open(out_file, "w") as f:
        # Header of file is a comment logging provenance
        f.write(
            "# This file has been auto-generated using generate_adf_config_file.py\n",
        )
        f.write("# Arguments:\n")
        f.write(f"# {cupid_file=}\n")
        f.write(f"# {adf_file=}\n")
        f.write(f"# Output: {out_file=}\n")
        # enter in each element of the dictionary into the new file
        yaml.dump(a_dict, f, sort_keys=False)


def get_date_from_ts(data: dict, keyname: str, listindex: int, default=None):
    if type(data) is not dict:
        raise TypeError(f"first argument needs to be dict, got {type(data)}")
    if keyname not in data:
        raise KeyError(f"no entry {keyname} in the dict")
    x = data[keyname]
    if isinstance(x, list):
        return x[listindex]
    elif isinstance(x, int):
        return x
    else:
        return default


if __name__ == "__main__":
    args = vars(_parse_args())
    print(args)
    generate_adf_config(args["cupid_file"], args["adf_template"], args["out_file"])
