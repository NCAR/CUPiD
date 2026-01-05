#!/usr/bin/env python3
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
@click.option(
    "--cupid-root",
    required=False,
    help="CUPiD root if running via CESM workflow",
)
def generate_all_cfg(cupid_config_loc, run_type, cupid_root=None):
    """Generate all files necessary to run ILAMB based on
    the CUPiD configuration file and the run type (BGC or SP)
    by running both generate_ilamb_cfg() and generate_ilamb_model_setup().
    """
    if not os.path.exists(os.path.join(cupid_config_loc, "config.yml")):
        raise KeyError(f"Can not find config.yml in {cupid_config_loc}")

    generate_ilamb_cfg(cupid_config_loc, run_type, cupid_root)
    generate_ilamb_model_setup(cupid_config_loc, run_type)


def generate_ilamb_cfg(cupid_config_loc, run_type, cupid_root=None):
    """Create ILAMB config file with correct paths to ILAMB auxiliary files
    given information from CUPiD configuration file"""

    with open(os.path.join(cupid_config_loc, "config.yml")) as c:
        c_dict = yaml.safe_load(c)
    if "ILAMB" in c_dict["compute_notebooks"]["lnd"].keys():
        ilamb_config_data_loc = c_dict["compute_notebooks"]["lnd"]["ILAMB"][
            "external_tool"
        ]["ilamb_config_data_loc"]
    else:
        print(
            "Warning: ILAMB information not in configuration file. Please add ILAMB",
        )
        raise KeyError

    if cupid_root is None:  # this works fine if running standalone
        ilamb_config_loc = os.path.join(cupid_config_loc, "../../ilamb_aux")
    else:  # this is needed in CESM workflow
        ilamb_config_loc = os.path.join(cupid_root, "ilamb_aux")
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

    shift_str_case = ""
    shift_str_base_case = ""
    if "1850" in c_dict["global_params"]["case_name"]:
        shift_str_case = ", 50, 2000"
    if "1850" in c_dict["global_params"]["base_case_name"]:
        shift_str_base_case = ", 50, 2000"
    with open(os.path.join(cupid_config_loc, "model_setup.txt"), "w") as ms:
        ms.write(
            "# Model Name    , Location of Files                                                                    ,  Shift From,  Shift To\n",  # noqa: E501
        )
        ms.write(
            f"{c_dict['global_params']['case_name']}          , {case_output_dir}/lnd/hist/regrid/{shift_str_case}\n",
        )
        ms.write(
            f"{c_dict['global_params']['base_case_name']}          , {base_case_output_dir}/lnd/hist/regrid/{shift_str_base_case}\n",  # noqa: E501
        )
    print(f"wrote {os.path.join(cupid_config_loc, 'model_setup.txt')}")
    print(
        f"""WARNING: ILAMB requires regridded output to be in {base_case_output_dir}/lnd/hist/regrid/ directory.
            This might be done with something like the following:
            for FILE in hist/*;
              do fname=$(basename '$FILE');
              ncremap -t 1 -P clm --sgs_frc=landfrac --sgs_msk=landmask -m
                /glade/work/oleson/cesm2_3_alpha16b/cime/tools/mapping/gen_mapping_files/gen_ESMF_mapping_file/map_ne30pg3_TO_fv0.9x1.25_aave.231025.nc
              '$FILE' 'hist/regrid/$fname';
              done""",  # noqa: E501
    )
    print("You can now run ILAMB with the following commands:")
    print("If running via the CESM workflow, this will be run automatically.")
    print(
        "(Users on a super computer should make sure they are on a compute node rather than a login node)",
    )
    print("---------")
    print("conda activate cupid-analysis")
    print("export ILAMB_ROOT=../../ilamb_aux")
    if os.path.exists(os.path.join(cupid_config_loc, "ILAMB_output/")):
        print(
            f"WARNING: directory {os.path.join(cupid_config_loc, 'ILAMB_output/')} exists; this may cause issues with running ILAMB. It is recommended to remove this directory prior to running the following command.",  # noqa: E501
        )

    ilamb_run_opts = ["ilamb-run"]
    ilamb_run_opts.append(
        f"--config {os.path.join(cupid_config_loc, f'ilamb_nohoff_final_CLM_{run_type}.cfg')}",
    )
    ilamb_run_opts.append(
        f"--build_dir {os.path.join(cupid_config_loc, 'ILAMB_output/')}",
    )
    ilamb_run_opts.append(
        f"--df_errs {os.path.join(cupid_config_loc, 'ilamb_aux', 'quantiles_Whittaker_cmip5v6.parquet')}",
    )
    ilamb_run_opts.append(
        f"--define_regions {os.path.join(cupid_config_loc, 'ilamb_aux', 'DATA/regions/LandRegions.nc')} {os.path.join(cupid_config_loc, 'ilamb_aux', 'DATA/regions/Whittaker.nc')}",  # noqa: E501
    )
    ilamb_run_opts.append(
        f"--regions global --model_setup {os.path.join(cupid_config_loc, 'model_setup.txt')}",
    )
    ilamb_run_opts.append("--filter .clm2.h0")
    print(" ".join(ilamb_run_opts))

    print("---------")


if __name__ == "__main__":
    generate_all_cfg()
