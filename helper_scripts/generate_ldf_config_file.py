#!/usr/bin/env python3
from __future__ import annotations

import os

import click
import yaml

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--cupid-config-loc",
    required=True,
    help="CUPiD example to use as template for config.yml",
)
@click.option(
    "--ldf-template",
    required=True,
    help="an ldf config file to use as a base",
)
@click.option("--out-file", required=True, help="the output file to save")
def generate_ldf_config(cupid_config_loc, ldf_template, out_file):
    """Use cupid config file (YAML) from cupid_config_loc and ldf_template (YAML)
    to produce out_file by modifying ldf_template with data from cupid config file.
    """
    if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
        raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    with open(os.path.join(cupid_config_loc, "config.yml")) as c:
        c_dict = yaml.safe_load(c)
    with open(ldf_template, encoding="UTF-8") as a:
        a_dict = yaml.safe_load(a)

    # read parameters from CUPID
    # use `get` to default to None
    DOUT = c_dict["global_params"]["CESM_output_dir"]
    base_case_name = c_dict["global_params"]["base_case_name"]
    test_case_name = c_dict["global_params"]["case_name"]
    base_case_nickname = c_dict["global_params"]["base_case_nickname"]
    test_case_nickname = c_dict["global_params"]["case_nickname"]
    c_ts = c_dict["timeseries"]
    ts_case_names = c_ts.get("case_name")
    if not ts_case_names:
        raise ValueError("CUPiD file does not have timeseries case_name array.")

    # Set case names for LDF config
    a_dict["diag_cam_climo"]["cam_case_name"] = test_case_name
    a_dict["diag_cam_baseline_climo"]["cam_case_name"] = base_case_name
    if test_case_nickname:
        a_dict["diag_cam_climo"]["case_nickname"] = test_case_nickname
    else:
        a_dict["diag_cam_climo"]["case_nickname"] = test_case_name
    if base_case_nickname:
        a_dict["diag_cam_baseline_climo"]["case_nickname"] = base_case_nickname
    else:
        a_dict["diag_cam_baseline_climo"]["case_nickname"] = base_case_name

    # TEST CASE HISTORY FILE PATH
    a_dict["diag_cam_climo"]["cam_hist_loc"] = os.path.join(
        DOUT,
        test_case_name,
        "lnd",
        "hist",
    )
    # TEST CASE TIME SERIES FILE PATH
    a_dict["diag_cam_climo"]["cam_ts_loc"] = os.path.join(
        "/glade/derecho/scratch",
        os.environ["USER"],
        test_case_name,
        "lnd",
        "proc",
        "tseries",
    )
    # TEST CASE CLIMO FILE PATH
    a_dict["diag_cam_climo"]["cam_climo_loc"] = os.path.join(
        "/glade/derecho/scratch",
        os.environ["USER"],
        test_case_name,
        "lnd",
        "proc",
        "climo",
    )
    # UPDATE PATHS FOR REGRIDDED DATA
    try:
        if c_dict["compute_notebooks"]["lnd"]["LDF"]["external_tool"][
            "regridded_output"
        ]:
            a_dict["diag_cam_climo"]["cam_hist_loc"] = os.path.join(
                a_dict["diag_cam_climo"]["cam_hist_loc"],
                "regrid",
            )
            a_dict["diag_cam_climo"]["cam_ts_loc"] = os.path.join(
                a_dict["diag_cam_climo"]["cam_ts_loc"],
                "regrid",
            )
            a_dict["diag_cam_climo"]["cam_climo_loc"] = os.path.join(
                a_dict["diag_cam_climo"]["cam_climo_loc"],
                "regrid",
            )
    except:  # noqa: E722
        pass
    # TEST CASE START / END YEARS
    test_case_cupid_ts_index = (
        ts_case_names.index(test_case_name) if test_case_name in ts_case_names else None
    )
    start_date = get_date_from_ts(c_ts["lnd"], "start_years", test_case_cupid_ts_index)
    end_date = get_date_from_ts(c_ts["lnd"], "end_years", test_case_cupid_ts_index)
    a_dict["diag_cam_climo"]["start_year"] = c_dict["global_params"]["climo_start_date"]
    a_dict["diag_cam_climo"]["end_year"] = c_dict["global_params"]["climo_end_date"]

    # Set values for BASELINE
    base_case_cupid_ts_index = (
        ts_case_names.index(base_case_name) if base_case_name in ts_case_names else None
    )

    base_case_output_dir = os.path.join(
        c_dict["global_params"].get("base_case_output_dir", DOUT),
        base_case_name,
    )
    base_start_date = get_date_from_ts(
        c_ts["lnd"],
        "start_years",
        base_case_cupid_ts_index,
    )
    base_end_date = get_date_from_ts(
        c_ts["lnd"],
        "end_years",
        base_case_cupid_ts_index,
    )
    if base_start_date is None:
        base_start_date = start_date
    if base_end_date is None:
        base_end_date = end_date

    a_dict["diag_cam_baseline_climo"]["cam_hist_loc"] = os.path.join(
        base_case_output_dir,
        "lnd",
        "hist",
    )
    a_dict["diag_cam_baseline_climo"]["cam_ts_loc"] = os.path.join(
        "/glade/derecho/scratch",
        os.environ["USER"],
        base_case_name,
        "lnd",
        "proc",
        "tseries",
    )
    a_dict["diag_cam_baseline_climo"]["cam_climo_loc"] = os.path.join(
        "/glade/derecho/scratch",
        os.environ["USER"],
        base_case_name,
        "lnd",
        "proc",
        "climo",
    )
    try:
        if c_dict["compute_notebooks"]["lnd"]["LDF"]["external_tool"][
            "base_regridded_output"
        ]:
            a_dict["diag_cam_baseline_climo"]["cam_hist_loc"] = os.path.join(
                a_dict["diag_cam_baseline_climo"]["cam_hist_loc"],
                "regrid",
            )
            a_dict["diag_cam_baseline_climo"]["cam_ts_loc"] = os.path.join(
                a_dict["diag_cam_baseline_climo"]["cam_ts_loc"],
                "regrid",
            )
            a_dict["diag_cam_baseline_climo"]["cam_climo_loc"] = os.path.join(
                a_dict["diag_cam_baseline_climo"]["cam_climo_loc"],
                "regrid",
            )
    except:  # noqa: E722
        pass
    a_dict["diag_cam_baseline_climo"]["start_year"] = c_dict["global_params"][
        "base_climo_start_date"
    ]
    a_dict["diag_cam_baseline_climo"]["end_year"] = c_dict["global_params"][
        "base_climo_end_date"
    ]
    a_dict["diag_basic_info"]["defaults_file"] = c_dict["compute_notebooks"]["lnd"][
        "LDF"
    ]["external_tool"]["defaults_file"]
    a_dict["diag_basic_info"]["hist_str"] = c_dict["timeseries"]["lnd"]["hist_str"]
    a_dict["diag_basic_info"]["num_procs"] = c_dict["timeseries"].get("num_procs", 1)
    a_dict["diag_basic_info"]["cam_regrid_loc"] = os.path.join(
        "/glade/derecho/scratch",
        os.environ["USER"],
        base_case_name,
        "lnd",
        "proc",
        "regrid",
    )  # This is where LDF will make "regrid" files
    a_dict["diag_basic_info"]["cam_diag_plot_loc"] = os.path.join(
        cupid_config_loc,
        "LDF_output",
    )  # this is where LDF will put plots, and "website" directory
    a_dict["user"] = os.environ["USER"]

    diag_var_list = []
    analysis_scripts = []
    plotting_scripts = []
    region_list = []
    for component in c_dict["compute_notebooks"]:
        for nb in c_dict["compute_notebooks"][component]:
            if (
                c_dict["compute_notebooks"][component][nb]
                .get("external_tool", {})
                .get("tool_name")
                == "LDF"
            ):
                for var in c_dict["compute_notebooks"][component][nb][
                    "external_tool"
                ].get("vars", []):
                    if var not in diag_var_list:
                        diag_var_list.append(var)
                for script in c_dict["compute_notebooks"][component][nb][
                    "external_tool"
                ].get("analysis_scripts", []):
                    if script not in analysis_scripts:
                        analysis_scripts.append(script)
                for script in c_dict["compute_notebooks"][component][nb][
                    "external_tool"
                ].get("plotting_scripts", []):
                    if script not in plotting_scripts:
                        plotting_scripts.append(script)
                for region in c_dict["compute_notebooks"][component][nb][
                    "external_tool"
                ].get("region_list", []):
                    if region not in region_list:
                        region_list.append(region)
    if diag_var_list:
        a_dict["diag_var_list"] = diag_var_list
    if analysis_scripts:
        a_dict["analysis_scripts"] = analysis_scripts
    if plotting_scripts:
        a_dict["plotting_scripts"] = plotting_scripts
    if region_list:
        a_dict["region_list"] = region_list

    # os.getenv("USER")

    with open(out_file, "w") as f:
        # Header of file is a comment logging provenance
        f.write(
            "# This file has been auto-generated using generate_ldf_config_file.py\n",
        )
        f.write(f"# It is based off of {cupid_config_loc}/config.yml\n")
        f.write("# Arguments:\n")
        f.write(f"# {cupid_config_loc=}\n")
        f.write(f"# {ldf_template=}\n")
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
    generate_ldf_config()
