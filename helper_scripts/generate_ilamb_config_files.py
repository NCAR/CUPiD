#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

import yaml


def _parse_args():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description="Generate an ILAMB model_setup.txt file based on an existing CUPID YAML file",
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
        help="CUPiD config file to use information from for model_setup.txt",
    )
    parser.add_argument(
        "--run-type",
        action="store",
        required=True,
        help="either 'BGC' (biogeochemistry) or 'SP' (satellite phenology)",
    )
    return parser.parse_args()


def generate_ilamb_model_setup(cesm_root, cupid_config_loc, run_type):
    """Create model_setup.txt file for use in ILAMB"""
    sys.path.append(os.path.join(cesm_root, "cime"))

    cupid_root = os.path.join(cesm_root, "tools", "CUPiD")
    # Is cupid_config_loc a valid value?
    if cupid_config_loc is None:
        cupid_config_loc = os.path.join(cupid_root, "examples", "key_metrics")
    if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
        raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    with open(os.path.join(cupid_config_loc, "config.yml")) as c:
        c_dict = yaml.safe_load(c)
    base_case_output_dir = os.path.join(
        c_dict["global_params"]["CESM_output_dir"],
        c_dict["global_params"]["base_case_name"],
    )
    with open(cupid_config_loc + "/model_setup.txt", "w") as ms:
        ms.write(
            "# Model Name    , Location of Files                                                                    ,  Shift From,  Shift To\n",  # noqa: E501
        )
        ms.write(
            f"CTSM51          , {base_case_output_dir}/lnd/hist/",
        )  # TODO: aslo update model name? Add to cupid config file?
    print(f"wrote {cupid_config_loc}/model_setup.txt")
    print("You can now run ILAMB with the following commands:")
    print("---")
    print("qinteractive -l select=1:ncpus=16:mpiprocs=16:mem=100G -l walltime=06:00:00")
    print("conda activate cupid-analysis")
    print("export ILAMB_ROOT=../ilamb_aux")
    print(
        f"mpiexec ilamb-run --config ../ilamb_aux/ilamb_nohoff_final_CLM_{run_type}.cfg --build_dir {cupid_config_loc}/ILAMB_output/ --df_errs ../ilamb_aux/quantiles_Whittaker_cmip5v6.parquet --define_regions ../ilamb_aux/DATA/regions/LandRegions.nc ../ilamb_aux/DATA/regions/Whittaker.nc --regions global --model_setup model_setup.txt --filter .clm2.h0.",  # noqa: E501
    )
    print("---------")


if __name__ == "__main__":
    args = vars(_parse_args())
    print(args)
    generate_ilamb_model_setup(
        args["cesm_root"],
        args["cupid_config_loc"],
        args["run_type"],
    )
