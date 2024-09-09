#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import yaml


def _parse_args():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description="Generate config.yml based on an existing CUPID example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Command line argument for name of case (required)
    parser.add_argument("--case", action="store", dest="case", help="Name of CESM case")

    # Command line argument for name of case (required)
    parser.add_argument(
        "--cesm-output-dir",
        action="store",
        dest="cesm_output_dir",
        help="Location of CESM history files (short-term archive)",
    )

    parser.add_argument(
        "--cupid-root",
        action="store",
        dest="cupid_root",
        help="Location of CUPiD in file system",
    )

    parser.add_argument(
        "--cupid-example",
        action="store",
        dest="cupid_example",
        default="key_metrics",
        help="CUPiD example to use as template for config.yml",
    )

    return parser.parse_args()


def generate_cupid_config(case, cesm_output_dir, cupid_root, cupid_example):
    with open(os.path.join(cupid_root, "examples", cupid_example, "config.yml")) as f:
        my_dict = yaml.safe_load(f)

    my_dict["global_params"]["case_name"] = case
    my_dict["timeseries"]["case_name"] = case

    # replace with environment variable
    my_dict["global_params"]["CESM_output_dir"] = cesm_output_dir

    # create new file, make it writeable
    with open("config.yml", "w") as f:
        # write a comment
        f.write("# sample comment\n")
        # enter in each element of the dictionary into the new file
        yaml.dump(my_dict, f, sort_keys=False)


if __name__ == "__main__":
    args = vars(_parse_args())
    generate_cupid_config(**args)
