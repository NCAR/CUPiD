#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

import yaml


def _parse_args():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description="Generate cupid_adf_config.yml based on an existing CUPID YAML file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Command line argument for location of CESM source code (required)
    parser.add_argument(
        "--cesm-root",
        action="store",
        dest="cesm_root",
        required=True,
        help="Location of CESM source code",
    )
    # Command line argument for CUPiD example from which to get config.yml
    parser.add_argument(
        "--cupid-config-loc",
        action="store",
        dest="cupid_config_loc",
        default=None,
        help="CUPiD example to use as template for config.yml",
    )
    parser.add_argument(
        "--run-type",
        action="store",
        required=True,
        help="either BGC (biogeochemistry) or SP (satellite phenology)",
    )
    parser.add_argument(
        "--out-dir",
        action="store",
        required=True,
        help="the output directory where config files are saved",
    )
    return parser.parse_args()


def generate_ilamb_config(cesm_root, cupid_config_loc, run_type, out_dir):
    """Use cupid config file (YAML) from cupid_config_loc and adf_file (YAML)
    to produce out_file by modifying adf_file with data from cupid config file.
    """
    sys.path.append(os.path.join(cesm_root, "cime"))

    cupid_root = os.path.join(cesm_root, "tools", "CUPiD")
    # Is cupid_config_loc a valid value?
    if cupid_config_loc is None:
        cupid_config_loc = os.path.join(cupid_root, "examples", "key_metrics")
    if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
        raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    # with open(os.path.join(cupid_config_loc, "config.yml")) as c:
    #     c_dict = yaml.safe_load(c)
    if run_type == "BGC":
        ilamb_config = "ilamb_nohoff_final_CLM_template.cfg"
    elif run_type == "SP":
        ilamb_config = "ilamb_nohoff_final_CLM_SP_template.cfg"
    with open(ilamb_config, encoding="UTF-8") as i_config:
        i_dict = yaml.safe_load(i_config)
        # TODO: PROBABLY ACTUALLY JUST NEED TO EDIT GLADE/CAMPAIGN PATHS

    # read parameters from CUPID
    # use `get` to default to None
    # DOUT = c_dict["global_params"]["CESM_output_dir"]
    # base_case_name = c_dict["global_params"]["base_case_name"]
    # test_case_name = c_dict["global_params"]["case_name"]

    with open(out_dir + "/" + ilamb_config, "w") as f:
        # Header of file is a comment logging provenance
        f.write(
            "# This file has been auto-generated using generate_ilamb_config_file.py\n",
        )
        f.write(f"# It is based off of {cupid_config_loc}/config.yml\n")
        f.write("# Arguments:\n")
        f.write(f"# {cesm_root=}\n")
        f.write(f"# {cupid_config_loc=}\n")
        f.write(f"# {run_type=}\n")
        # enter in each element of the dictionary into the new file
        yaml.dump(i_dict, f, sort_keys=False)
        # TODO: not a yaml file...


def generate_ilamb_model_setup(cesm_root, cupid_config_loc, run_type, out_dir):
    """Create model_setup.txt file for use in ILAMB"""
    sys.path.append(os.path.join(cesm_root, "cime"))

    # cupid_root = os.path.join(cesm_root, "tools", "CUPiD")
    # # Is cupid_config_loc a valid value?
    # if cupid_config_loc is None:
    #     cupid_config_loc = os.path.join(cupid_root, "examples", "key_metrics")
    # if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
    #     raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    # with open(os.path.join(cupid_config_loc, "config.yml")) as c:
    #     c_dict = yaml.safe_load(c)
    with open("model_setup.txt", "w") as ms:

        ms.write(
            "# Model Name    , Location of Files                                                                                     ,  Shift From,  Shift To\n",  # noqa: E501
        )
        ms.write(
            "CTSM51          , /glade/campaign/cgd/tss/common/Land_Only_Simulations/CTSM52_DEV/ctsm51_ctsm51d166deadveg_1deg_CRUJRA_FLDS_ABsnoCDE_blk_A5BCD_hist/lnd/hist/",  # noqa: E501
        )


if __name__ == "__main__":
    args = vars(_parse_args())
    print(args)
    generate_ilamb_config(
        args["cesm_root"],
        args["cupid_config_loc"],
        args["run_type"],
        args["out_dir"],
    )
    generate_ilamb_model_setup(
        args["cesm_root"],
        args["cupid_config_loc"],
        args["run_type"],
        args["out_dir"],
    )
