# /usr/bin/env python3
from __future__ import annotations

import os
import shutil

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
    "--run-type",
    required=True,
    help="either 'BGC' (biogeochemistry) or 'SP' (satellite phenology)",
)
def generate_all_cfg(cupid_config_loc, run_type):
    """Generate all files necessary to run ILAMB based on
    the CUPiD configuration file and the run type (BGC or SP)
    by running both generate_ilamb_cfg() and generate_ilamb_model_setup().
    """
    if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
        raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    generate_ilamb_cfg(cupid_config_loc, run_type)
    generate_ilamb_model_setup(cupid_config_loc, run_type)


def generate_ilamb_cfg(cupid_config_loc, run_type):
    """Create ILAMB config file with correct paths to ILAMB auxiliary files
    given information from CUPiD configuration file"""

    with open(os.path.join(cupid_config_loc, "config.yml")) as c:
        c_dict = yaml.safe_load(c)
    if "link_to_ILAMB" in c_dict["compute_notebooks"]["lnd"].keys():
        ilamb_config_data_loc = c_dict["compute_notebooks"]["lnd"]["link_to_ILAMB"][
            "external_tool"
        ]["ilamb_config_data_loc"]
    else:
        print(
            "Warning: ILAMB information not in configuration file. Please add link_to_ILAMB",
        )
        raise KeyError

    ilamb_config_loc = os.path.join(cupid_config_loc, "../../ilamb_aux")
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


def generate_ilamb_model_setup(cupid_config_loc, run_type):
    """Create model_setup.txt file for use in ILAMB"""

    with open(os.path.join(cupid_config_loc, "config.yml")) as c:
        c_dict = yaml.safe_load(c)
    case_output_dir = os.path.join(
        c_dict["global_params"]["CESM_output_dir"],
        c_dict["global_params"]["case_name"],
    )
    if "base_case_output_dir" in c_dict["global_params"]:
        base_case_output_dir = os.path.join(
            c_dict["global_params"]["base_case_output_dir"],
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
    generate_all_cfg()
