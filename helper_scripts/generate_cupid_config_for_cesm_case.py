#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

import click
import yaml

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--cesm-root", required=True, help="Location of CESM source code")
@click.option("--case-root", default=os.getcwd(), help="CESM case directory")
@click.option(
    "--cupid-root",
    default=None,
    help="CUPiD directory (None => CESM_ROOT/tools/CUPiD)",
)
@click.option(
    "--cupid-example",
    default="key_metrics",
    help="CUPiD example to use as template for config.yml",
)
@click.option(
    "--cupid-baseline-case",
    default="b.e23_alpha17f.BLT1850.ne30_t232.092",
    help="Base case name",
)
@click.option(
    "--cupid-baseline-root",
    default="/glade/campaign/cesm/development/cross-wg/diagnostic_framework/CESM_output_for_testing",
    help="Base case root directory",
)
@click.option(
    "--cupid-ts-dir",
    default="/glade/campaign/cesm/development/cross-wg/diagnostic_framework/CESM_output_for_testing",
    help="Timeseries directory root; eg, if permission issues, use your scratch",
)
@click.option("--cupid-startdate", default="0001-01-01", help="CUPiD case start date")
@click.option("--cupid-enddate", default="0101-01-01", help="CUPiD case end date")
@click.option(
    "--cupid-base-startdate",
    default="0001-01-01",
    help="CUPiD base case start date",
)
@click.option(
    "--cupid-base-enddate",
    default="0101-01-01",
    help="CUPiD base case end date",
)
@click.option(
    "--adf-output-root",
    default=None,
    help="Directory where ADF will be run (None => case root)",
)
@click.option(
    "--ldf-output-root",
    default=None,
    help="Directory where LDF will be run (None => case root)",
)
@click.option(
    "--ilamb-output-root",
    default=None,
    help="Directory where ILAMB will be run (None => case root)",
)
@click.option(
    "--cupid-run-adf",
    default=None,
    help="Boolean flag to indicate whether to run ADF analysis",
)
@click.option(
    "--cupid-run-ldf",
    default=None,
    help="Boolean flag to indicate whether to run LDF analysis",
)
@click.option(
    "--cupid-run-ilamb",
    default=None,
    help="Boolean flag to indicate whether to run ILAMB analysis",
)
@click.option("--run-cvdp", is_flag=True, default=False, help="Run CVDP diagnostics")
def generate_cupid_config(
    case_root,
    cesm_root,
    cupid_root,
    cupid_example,
    cupid_baseline_case,
    cupid_baseline_root,
    cupid_ts_dir,
    cupid_startdate,
    cupid_enddate,
    cupid_base_startdate,
    cupid_base_enddate,
    adf_output_root,
    ldf_output_root,
    ilamb_output_root,
    cupid_run_adf,
    cupid_run_ldf,
    cupid_run_ilamb,
    run_cvdp,
):
    """
    Generate a CUPiD `config.yml` file based on information from a CESM case and
    a specific CUPiD example configuration (such as 'key metrics').

    This function takes the root directory of the CESM case and the CESM installation,
    along with the name of a CUPiD example. It validates the example, loads information
    from the CESM case (such as the case name and output directory), modifies the
    configuration based on the case-specific data, and generates a new `config.yml` file
    in the current working directory.

    The generated `config.yml` file contains:
    - Global parameters such as case name, start and end dates.
    - Time series information for atmospheric end years.
    - Base output directory paths for CESM results.

    Arguments:
    ----------
    case_root : str
        The root directory of the CESM case from which case-specific data will be retrieved.

    cesm_root : str
        The root directory of the CESM installation, where CIME scripts reside.

    cupid_root : str
        The root directory where CUPiD examples reside (defaults to subdirectory of cesm_root).

    cupid_example : str
        The name of a CUPiD example (e.g., 'key metrics') to base the configuration file on.
        Must be a valid subdirectory within the CUPiD examples directory.

    cupid_baseline_case : str
        The name of the base case.

    cupid_baseline_root : str
        The root directory of the base case.

    cupid_ts_dir : str
        The root directory for the timeseries.

    cupid_startdate : str
        The start date of the case being analyzed ("YYYY-MM-DD").

    cupid_enddate : str
        The end date of the case being analyzed ("YYYY-MM-DD").

    cupid_base_startdate : str
        The start date of the base case ("YYYY-MM-DD").

    cupid_base_enddate : str
        The end date of the base case ("YYYY-MM-DD").

    adf_output_root : str
        The root directory where ADF output will be stored (defaults to case_root).

    ldf_output_root : str
        The root directory where LDF output will be stored (defaults to case_root).

    ilamb_output_root : str
        The root directory where ILAMB output will be stored (defaults to case_root).

    cupid_run_adf : Bool
        Boolean flag to indicate whether to run ADF analysis.

    cupid_run_ldf : Bool
        Boolean flag to indicate whether to run LDF analysis.

    cupid_run_ilamb : Bool
        Boolean flag to indicate whether to run ILAMB analysis.

    Raises:
    -------
    KeyError:
        If the provided CUPiD example is not found in the valid CUPiD examples directory.

    Outputs:
    --------
    config.yml : file
        A YAML file containing the generated configuration based on the provided CESM case
        and CUPiD example.
    """

    sys.path.append(os.path.join(cesm_root, "cime"))
    from CIME.case import Case

    # Is adf_output_root provided?
    if adf_output_root is None:
        adf_output_root = case_root
    if ldf_output_root is None:
        ldf_output_root = case_root
    if ilamb_output_root is None:
        ilamb_output_root = case_root

    # Is cupid_example a valid value?
    if cupid_root is None:
        cupid_root = os.path.join(cesm_root, "tools", "CUPiD")
    cupid_examples = os.path.join(cupid_root, "examples")
    valid_examples = [
        example
        for example in next(os.walk(cupid_examples))[1]
        if example not in ["ilamb"]
    ]
    if cupid_example not in valid_examples:
        error_msg = f"argument --cupid-example: invalid choice '{cupid_example}'"
        raise KeyError(
            f"{error_msg} (choose from subdirectories of {cupid_examples}: {valid_examples})",
        )

    with Case(case_root, read_only=False, record=True) as cesm_case:
        case = cesm_case.get_value("CASE")
        dout_s_root = cesm_case.get_value("DOUT_S_ROOT")

    # TODO: these sea-ice specific vars (and some glc vars) should also be added as environment vars
    # See https://github.com/NCAR/CUPiD/issues/189
    climo_nyears = 35
    base_climo_nyears = 40

    # --------------------------------------------------------------------------------
    with open(os.path.join(cupid_root, "examples", cupid_example, "config.yml")) as f:
        my_dict = yaml.safe_load(f)

    my_dict["data_sources"]["nb_path_root"] = os.path.join(
        cupid_root,
        "nblibrary",
    )
    my_dict["global_params"]["case_name"] = case
    my_dict["global_params"]["start_date"] = cupid_startdate
    my_dict["global_params"]["end_date"] = cupid_enddate
    my_dict["global_params"]["base_case_name"] = cupid_baseline_case
    my_dict["global_params"]["base_case_output_dir"] = cupid_baseline_root
    my_dict["global_params"]["ts_dir"] = cupid_ts_dir
    my_dict["global_params"]["base_start_date"] = cupid_base_startdate
    my_dict["global_params"]["base_end_date"] = cupid_base_enddate
    my_dict["timeseries"]["case_name"] = [case, cupid_baseline_case]

    for component in my_dict["timeseries"]:
        if (
            isinstance(my_dict["timeseries"][component], dict)
            and "start_years" in my_dict["timeseries"][component]
        ):
            cupid_start_year = int(cupid_startdate.split("-")[0])
            cupid_base_start_year = int(cupid_base_startdate.split("-")[0])
            my_dict["timeseries"][component]["start_years"] = [
                cupid_start_year,
                cupid_base_start_year,
            ]
        if (
            isinstance(my_dict["timeseries"][component], dict)
            and "end_years" in my_dict["timeseries"][component]
        ):
            # Assumption that end_year is YYYY-01-01, so we want end_year to be YYYY-1
            cupid_end_year = int(cupid_enddate.split("-")[0]) - 1
            cupid_base_end_year = int(cupid_base_enddate.split("-")[0]) - 1
            my_dict["timeseries"][component]["end_years"] = [
                cupid_end_year,
                cupid_base_end_year,
            ]
        if (
            isinstance(my_dict["timeseries"][component], dict)
            and "start_years" in my_dict["timeseries"][component]
        ):
            cupid_start_year = int(cupid_startdate.split("-")[0])
            cupid_base_start_year = int(cupid_base_startdate.split("-")[0])
            my_dict["timeseries"][component]["start_years"] = [
                cupid_start_year,
                cupid_base_start_year,
            ]

    if cupid_run_adf or cupid_run_ldf or cupid_run_ilamb:
        if "index" in my_dict["compute_notebooks"]["infrastructure"]:
            del my_dict["compute_notebooks"]["infrastructure"]["index"]
        my_dict["compute_notebooks"]["infrastructure"] = {
            "summary_tables": {parameter_groups: {none: {}}},
        }
        my_dict["book_toc"]["root"] = "infrastructure/summary_tables"
        if cupid_run_adf:
            my_dict["compute_notebooks"]["infrastructure"]["summary_tables"][
                "parameter_groups"
            ]["none"]["adf_root"] = f"{adf_output_root}/ADF_output/"
        if cupid_run_ldf:
            my_dict["compute_notebooks"]["infrastructure"]["summary_tables"][
                "parameter_groups"
            ]["none"]["ldf_root"] = f"{ldf_output_root}/LDF_output/"
        if cupid_run_ilamb:
            my_dict["compute_notebooks"]["infrastructure"]["summary_tables"][
                "parameter_groups"
            ]["none"]["ilamb_root"] = f"{ilamb_output_root}/ILAMB_output/"
            my_dict["compute_notebooks"]["infrastructure"]["summary_tables"][
                "parameter_groups"
            ]["none"]["ilamb_vars_highlight"] = [
                "Gross Primary Productivity",
                "Runoff",
                "Snow Water Equivalent",
                "Surface Relative Humidity",
                "Precipitation",
            ]

    if "ADF" in my_dict["compute_notebooks"].get("atm", {}):
        my_dict["compute_notebooks"]["atm"]["ADF"]["parameter_groups"]["none"][
            "adf_root"
        ] = os.path.join(adf_output_root, "ADF_output")
        if "diag_cvdp_info" in my_dict["compute_notebooks"]["atm"]["ADF"].get(
            "external_tool",
            {},
        ):
            my_dict["compute_notebooks"]["atm"]["ADF"]["external_tool"][
                "diag_cvdp_info"
            ]["cvdp_run"] = run_cvdp
    if "CVDP" in my_dict["compute_notebooks"].get("atm", {}):
        my_dict["compute_notebooks"]["atm"]["CVDP"]["parameter_groups"]["none"][
            "cvdp_loc"
        ] = os.path.join(adf_output_root, "CVDP_output")

    if "Greenland_SMB_visual_compare_obs" in my_dict["compute_notebooks"].get(
        "glc",
        {},
    ):
        my_dict["compute_notebooks"]["glc"]["Greenland_SMB_visual_compare_obs"][
            "parameter_groups"
        ]["none"]["climo_nyears"] = climo_nyears
        my_dict["compute_notebooks"]["glc"]["Greenland_SMB_visual_compare_obs"][
            "parameter_groups"
        ]["none"]["base_climo_nyears"] = base_climo_nyears

    # Regional Ocean Open Boundary Conditions needs access to ocean input directory
    # The ocean input directory is (hackily) accessible through the case root directory
    if "Regional_Ocean_OBC" in my_dict["compute_notebooks"].get("ocn", {}):
        my_dict["compute_notebooks"]["ocn"]["Regional_Ocean_OBC"]["parameter_groups"][
            "none"
        ]["case_root"] = case_root

    # replace with environment variable
    my_dict["global_params"]["CESM_output_dir"] = os.path.dirname(dout_s_root)

    # create new file, make it writeable
    with open("config.yml", "w") as f:
        # Header of file is a comment logging provenance
        f.write(f"# This file has been auto-generated for use with {case}\n")
        f.write(f"# It is based off of examples/{cupid_example}/config.yml\n")
        f.write("# Arguments used:\n")
        f.write(f"# cesm_root = {cesm_root}\n")
        f.write(f"# case_root = {case_root}\n")
        f.write(f"# cupid_example= {cupid_example}\n")

        # enter in each element of the dictionary into the new file
        yaml.dump(my_dict, f, sort_keys=False)


if __name__ == "__main__":
    generate_cupid_config()
