#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

import yaml


def _parse_args():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description="Generate config.yml based on an existing CUPID example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Command line argument for location of CESM source code (required)
    parser.add_argument(
        "--cesm-root",
        action="store",
        dest="cesm_root",
        help="Location of CESM source code",
    )

    # Command line argument for CUPiD example from which to get config.yml
    parser.add_argument(
        "--cupid-example",
        action="store",
        dest="cupid_example",
        default="key_metrics",
        help="CUPiD example to use as template for config.yml",
    )

    # Command line argument location of CESM case directory
    parser.add_argument(
        "--case-root",
        action="store",
        dest="case_root",
        default=os.getcwd(),
        help="CESM case directory",
    )

    return parser.parse_args()


def generate_cupid_config(case_root, cesm_root, cupid_example):
    sys.path.append(os.path.join(cesm_root, "cime"))
    from CIME.case import Case

    with Case(case_root, read_only=False, record=True) as cesm_case:
        case = cesm_case.get_value("CASE")
        dout_s_root = cesm_case.get_value("DOUT_S_ROOT")
    cupid_root = os.path.join(cesm_root, "tools", "CUPiD")

    with open(os.path.join(cupid_root, "examples", cupid_example, "config.yml")) as f:
        my_dict = yaml.safe_load(f)

    my_dict["global_params"]["case_name"] = case
    my_dict["timeseries"]["case_name"] = case

    # replace with environment variable
    my_dict["global_params"]["CESM_output_dir"] = dout_s_root

    # create new file, make it writeable
    with open("config.yml", "w") as f:
        # write a comment
        f.write(f"# This file has been auto-generated for use with {case}\n")
        f.write(f"# It is based off of examples/{cupid_example}/config.yml\n")
        # enter in each element of the dictionary into the new file
        yaml.dump(my_dict, f, sort_keys=False)


if __name__ == "__main__":
    args = vars(_parse_args())
    generate_cupid_config(**args)
