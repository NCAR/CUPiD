#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
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


def generate_ilamb_cfg(cesm_root, cupid_config_loc, run_type):
    """Create config file for use in ILAMB"""
    sys.path.append(os.path.join(cesm_root, "cime"))

    cupid_root = os.path.join(cesm_root, "tools", "CUPiD")
    # Is cupid_config_loc a valid value?
    if cupid_config_loc is None:
        cupid_config_loc = os.path.join(
            cupid_root,
            "examples",
            "external_diag_packages",
        )
    if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
        raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    with open(os.path.join(cupid_config_loc, "config.yml")) as c:
        c_dict = yaml.safe_load(c)
    ilamb_config_data_loc = c_dict["compute_notebooks"]["lnd"]["link_to_ILAMB"][
        "external_tool"
    ]["ilamb_config_data_loc"]

    ilamb_config_loc = os.path.join(cesm_root, "tools", "CUPiD", "ilamb_aux")
    with open(
        os.path.join(
            ilamb_config_loc,
            f"ilamb_nohoff_final_CLM_{run_type}_template.cfg",
        ),
    ) as cfg:
        cfg_content = cfg.read()
        cfg_content = cfg_content.replace("PATH/", ilamb_config_data_loc)
    with open(
        os.path.join(cupid_config_loc, f"ilamb_nohoff_final_CLM_{run_type}.cfg"),
        "w",
    ) as cfg:
        cfg.write(cfg_content)
    print(f"wrote {cupid_config_loc}/ilamb_nohoff_final_CLM_{run_type}.cfg")

    # copy ilamb_aux to local directory
    if os.path.exists(os.path.join(cupid_config_loc, "ilamb_aux")):
        shutil.rmtree(
            os.path.join(cupid_config_loc, "ilamb_aux"),
        )  # Remove the existing directory
    shutil.copytree(
        os.path.join(ilamb_config_loc),
        os.path.join(cupid_config_loc, "ilamb_aux"),
    )


def generate_ilamb_model_setup(cesm_root, cupid_config_loc, run_type):
    """Create model_setup.txt file for use in ILAMB"""
    sys.path.append(os.path.join(cesm_root, "cime"))

    cupid_root = os.path.join(cesm_root, "tools", "CUPiD")
    # Is cupid_config_loc a valid value?
    if cupid_config_loc is None:
        cupid_config_loc = os.path.join(
            cupid_root,
            "examples",
            "external_diag_packages",
        )
    if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
        raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    with open(os.path.join(cupid_config_loc, "config.yml")) as c:
        c_dict = yaml.safe_load(c)
    case_output_dir = os.path.join(
        c_dict["global_params"]["CESM_output_dir"],
        c_dict["global_params"]["case_name"],
    )
    if "base_case_output_dir" in c_dict["global_params"]:
        base_case_output_dir = os.path.join(
            c_dict["global_params"]["CESM_output_dir"],
            c_dict["global_params"]["base_case_name"],
        )
    else:
        base_case_output_dir = os.path.join(
            c_dict["global_params"]["CESM_output_dir"],
            c_dict["global_params"]["base_case_name"],
        )
    with open(os.path.join(cupid_config_loc, "model_setup.txt"), "w") as ms:
        ms.write(
            "# Model Name    , Location of Files                                                                    ,  Shift From,  Shift To\n",  # noqa: E501
        )
        ms.write(
            f"{c_dict['global_params']['case_name']}          , {case_output_dir}/lnd/hist/regrid/\n",
        )
        ms.write(
            f"{c_dict['global_params']['base_case_name']}          , {base_case_output_dir}/lnd/hist/regrid/\n",
        )
    print(f"wrote {os.path.join(cupid_config_loc, 'model_setup.txt')}")
    print(
        f"WARNING: ILAMB requires regridded output to be in {base_case_output_dir}/lnd/hist/regrid/ directory.",
    )
    print("You can now run ILAMB with the following commands:")
    print(
        "(Users on a super computer should make sure they are on a compute node rather than a login node)",
    )
    print("---------")
    print("conda activate cupid-analysis")
    print(f"export ILAMB_ROOT={os.path.join(cupid_config_loc, 'ilamb_aux')}")
    if os.path.exists(os.path.join(cupid_config_loc, "ILAMB_output/")):
        print(
            f"WARNING: directory {os.path.join(cupid_config_loc, 'ILAMB_output/')} exists; this may cause issues with runnign ILAMB. It is recommended to remove this directory prior to running the following command.",  # noqa: E501
        )
    print(
        f"ilamb-run --config {os.path.join(cupid_config_loc, f'ilamb_nohoff_final_CLM_{run_type}.cfg')} --build_dir {os.path.join(cupid_config_loc, 'ILAMB_output/')} --df_errs {os.path.join(cupid_config_loc, 'ilamb_aux', 'quantiles_Whittaker_cmip5v6.parquet')} --define_regions {os.path.join(cupid_config_loc, 'ilamb_aux', 'DATA/regions/LandRegions.nc')} {os.path.join(cupid_config_loc, 'ilamb_aux', 'DATA/regions/Whittaker.nc')} --regions global --model_setup {os.path.join(cupid_config_loc, 'model_setup.txt')} --filter .clm2.h0.",  # noqa: E501
    )
    print("---------")


if __name__ == "__main__":
    args = vars(_parse_args())
    print(args)
    generate_ilamb_cfg(args["cesm_root"], args["cupid_config_loc"], args["run_type"])
    generate_ilamb_model_setup(
        args["cesm_root"],
        args["cupid_config_loc"],
        args["run_type"],
    )
