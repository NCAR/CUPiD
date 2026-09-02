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
    "--cupid-ts-dir",
    default="/glade/campaign/cesm/development/cross-wg/diagnostic_framework/CESM_output_for_testing",
    help="Timeseries directory root; eg, if permission issues, use your scratch",
)
@click.option(
    "--cupid-regrid",
    default=False,
    help="If True, time series files will be remapped",
)
@click.option(
    "--cupid-regrid-atm-file",
    default=None,
    help="Mapping file for regridding atmosphere time series (or None to leave on native grid)",
)
@click.option("--cupid-startdate", default="0001-01-01", help="CUPiD case start date")
@click.option("--cupid-enddates", default="0101-01-01", help="CUPiD case end date")
@click.option(
    "--cupid-climo-end-year",
    default=100,
    help="CUPiD climo end year for LDF",
)
@click.option(
    "--cupid-climo-n-year",
    default=20,
    help="Length of climatology for LDF",
)
@click.option(
    "--cupid-align-year",
    default="",
    help="Number of years to offset time axis for global timeseries plots of CESM case",
)
@click.option(
    "--case-nickname",
    default="NONE",
    help="Name to use for case in plot legends",
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
@click.option(
    "--cupid-comparison-cases",
    default="",
    help="List of cases to compare CESM case against",
)
@click.option(
    "--cupid-comparison-roots",
    default="",
    help="Root directories of comparison case(s)",
)
@click.option(
    "--cupid-comparison-nicknames",
    default="",
    help="Name(s) to use for comparison case(s) in plot legends",
)
@click.option(
    "--cupid-comparison-climo-end-years",
    default="",
    help="CUPiD climo end year of comparison case(s) (for LDF)",
)
@click.option(
    "--cupid-comparison-climo-n-years",
    default="",
    help="Length of climatology of comparison case(s) (for LDF)",
)
@click.option(
    "--cupid-comparison-startdates",
    default="",
    help="Start date(s) of comparison case(s)",
)
@click.option(
    "--cupid-comparison-align-years",
    default="",
    help="Number of years to offset time axis for global timeseries plots of comparison case(s)",
)
@click.option(
    "--cupid-comparison-regrid-atm-files",
    default="",
    help="Mapping file(s) for regridding comparison cases atmosphere time series (or None to leave on native grid)",
)
def generate_cupid_config(
    case_root,
    cesm_root,
    cupid_root,
    case_nickname,
    cupid_example,
    cupid_ts_dir,
    cupid_regrid,
    cupid_startdate,
    cupid_enddates,
    cupid_climo_end_year,
    cupid_climo_n_year,
    cupid_align_year,
    cupid_regrid_atm_file,
    adf_output_root,
    ldf_output_root,
    ilamb_output_root,
    cupid_run_adf,
    cupid_run_ldf,
    cupid_run_ilamb,
    run_cvdp,
    cupid_comparison_cases,
    cupid_comparison_roots,
    cupid_comparison_nicknames,
    cupid_comparison_startdates,
    cupid_comparison_climo_end_years,
    cupid_comparison_climo_n_years,
    cupid_comparison_align_years,
    cupid_comparison_regrid_atm_files,
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
    - Output directory paths for CESM results.

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

    cupid_comparison_cases : str, list
        The name (or names) of case(s) to compare against.

    cupid_comparison_roots : str, list
        The root directory (or directories) of the comparison cases.

    cupid_ts_dir : str
        The root directory for the timeseries.

    cupid_startdate : str
        The start date of the case being analyzed ("YYYY-MM-DD").

    cupid_enddates : str, list
        The end date(s) of the case(s) being analyzed ("YYYY-MM-DD").

    generate_cupid_config_for_cesm_case : str, list
        The end date(s) of the case(s) to compare against ("YYYY-MM-DD").

    cupid_climo_end_year : int
        The end year of the climatology for the case being analyzed (YYYY)

    cupid_climo_n_year : int
        The number of years over which the climatology should run for the case being analyzed.

    cupid_comparison_climo_end_years : int, list
        The end year of the climatology for the comparison case(s) (YYYY)

    cupid_comparison_climo_n_years : int, list
        The number of years over which the climatology should run for the comparison case(s).

    cupid_comparison_startdates : str, list

    adf_output_root : str
        The root directory where ADF output will be stored (defaults to case_root).

    ldf_output_root : str
        The root directory where LDF output will be stored (defaults to case_root).

    ilamb_output_root : str
        The root directory where ILAMB output will be stored (defaults to case_root).

    run_cvdp : Bool
        Boolean flag to indicate whether to run CVDP analysis.

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

    # --------------------------------------------------------------------------------
    with open(os.path.join(cupid_root, "examples", cupid_example, "config.yml")) as f:
        my_dict = yaml.safe_load(f)

    my_dict["data_sources"]["nb_path_root"] = os.path.join(
        cupid_root,
        "nblibrary",
    )

    if isinstance(cupid_comparison_cases, str):
        if len(cupid_comparison_cases) > 0:
            cupid_comparison_cases = cupid_comparison_cases.split(",")
    num_cases = len(cupid_comparison_cases)
    if num_cases == 0:
        cupid_comparison_cases = []
        cupid_comparison_roots = []
        cupid_comparison_nicknames = []
        cupid_comparison_regrid_atm_files = []
        cupid_comparison_climo_n_years = []
        cupid_comparison_climo_end_years = []
        cupid_comparison_align_years = []
    else:
        cupid_comparison_roots = standardize_cupid_comparison_field(
            cupid_comparison_roots,
            "cupid_comparison_roots",
            num_cases,
        )
        cupid_comparison_nicknames = standardize_cupid_comparison_field(
            cupid_comparison_nicknames,
            "cupid_comparison_nicknames",
            num_cases,
        )
        cupid_comparison_regrid_atm_files = standardize_cupid_comparison_field(
            cupid_comparison_regrid_atm_files,
            "cupid_comparison_regrid_atm_files",
            num_cases,
        )
        cupid_comparison_startdates = standardize_cupid_comparison_field(
            cupid_comparison_startdates,
            "cupid_comparison_startdates",
            num_cases,
        )
        cupid_comparison_climo_n_years = standardize_cupid_comparison_field(
            cupid_comparison_climo_n_years,
            "cupid_comparison_climo_n_years",
            num_cases,
        )
        cupid_comparison_climo_end_years = standardize_cupid_comparison_field(
            cupid_comparison_climo_end_years,
            "cupid_comparison_climo_end_years",
            num_cases,
        )
        cupid_comparison_align_years = standardize_cupid_comparison_field(
            cupid_comparison_align_years,
            "cupid_comparison_align_years",
            num_cases,
        )
    cupid_enddates = standardize_cupid_comparison_field(
        cupid_enddates,
        "cupid_enddates",
        num_cases + 1,
    )

    my_dict["global_params"]["case_names"] = [case] + cupid_comparison_cases
    my_dict["global_params"]["CESM_output_dir"] = [os.path.dirname(dout_s_root)] + [
        os.path.abspath(cupid_comparison_root)
        for cupid_comparison_root in cupid_comparison_roots
    ]

    my_dict["global_params"]["start_dates"] = [
        cupid_startdate,
    ] + cupid_comparison_startdates
    my_dict["global_params"]["end_dates"] = cupid_enddates
    my_dict["global_params"]["ts_dir"] = os.path.abspath(cupid_ts_dir)

    # Run from January of start year to December of end year
    my_dict["global_params"]["climo_start_years"] = [
        int(cupid_climo_end_year) - int(cupid_climo_n_year) + 1,
    ]
    my_dict["global_params"]["climo_end_years"] = [int(cupid_climo_end_year)]
    climo_nyears = [int(cupid_climo_n_year)]
    for end_year, n_year in zip(
        cupid_comparison_climo_end_years,
        cupid_comparison_climo_n_years,
    ):
        my_dict["global_params"]["climo_start_years"].append(
            int(end_year) - int(n_year) + 1,
        )
        my_dict["global_params"]["climo_end_years"].append(int(end_year))
        climo_nyears.append(int(n_year))

    # Set nicknames for cases
    my_dict["global_params"]["case_nicknames"] = []
    for n, nickname in enumerate([case_nickname] + cupid_comparison_nicknames):
        if nickname != "NONE":
            my_dict["global_params"]["case_nicknames"].append(nickname)
        else:
            my_dict["global_params"]["case_nicknames"].append(
                my_dict["global_params"]["case_names"][n],
            )

    for component in my_dict["timeseries"]:
        if (
            isinstance(my_dict["timeseries"][component], dict)
            and "start_years" in my_dict["timeseries"][component]
        ):
            my_dict["timeseries"][component]["start_years"] = []
            for start_date in my_dict["global_params"]["start_dates"]:
                my_dict["timeseries"][component]["start_years"].append(
                    int(start_date.split("-")[0]),
                )
        if (
            isinstance(my_dict["timeseries"][component], dict)
            and "end_years" in my_dict["timeseries"][component]
        ):
            my_dict["timeseries"][component]["end_years"] = []
            for end_date in my_dict["global_params"]["end_dates"]:
                end_year = int(end_date.split("-")[0])
                # If end_year is YYYY-01-01, we want end_year to be YYYY-1
                if (int(end_date.split("-")[1]) == 1) and (
                    int(end_date.split("-")[2]) == 1
                ):
                    end_year = end_year - 1
                my_dict["timeseries"][component]["end_years"].append(end_year)

    if "atm" in my_dict["timeseries"]:
        my_dict["timeseries"]["atm"]["mapping_file"] = []
        for regrid_atm_file in [
            cupid_regrid_atm_file,
        ] + cupid_comparison_regrid_atm_files:
            if regrid_atm_file == "NONE":
                my_dict["timeseries"]["atm"]["mapping_file"].append(None)
            else:
                my_dict["timeseries"]["atm"]["mapping_file"].append(regrid_atm_file)

    # Some atm notebooks need to know if CUPiD regridded the data
    # (because that changes the directory where time series files are found)
    for notebook in ["Global_PSL_NMSE_compare_obs_lens", "TimeSeriesPlots"]:
        if notebook in my_dict["compute_notebooks"].get("atm", {}):
            my_dict["compute_notebooks"]["atm"][notebook]["parameter_groups"]["none"][
                "regridded_output"
            ] = []
            for regrid_atm_file in my_dict["timeseries"]["atm"]["mapping_file"]:
                my_dict["compute_notebooks"]["atm"][notebook]["parameter_groups"][
                    "none"
                ]["regridded_output"].append(
                    regrid_atm_file is not None and cupid_regrid,
                )

    # TimeSeriesPlots also needs case_align_years
    if "TimeSeriesPlots" in my_dict["compute_notebooks"].get("atm", {}):
        my_dict["compute_notebooks"]["atm"]["TimeSeriesPlots"]["parameter_groups"][
            "none"
        ]["case_align_years"] = [int(cupid_align_year)] + [
            int(align_year) for align_year in cupid_comparison_align_years
        ]

    if cupid_run_adf or cupid_run_ldf or cupid_run_ilamb:
        if "index" in my_dict["compute_notebooks"]["infrastructure"]:
            del my_dict["compute_notebooks"]["infrastructure"]["index"]
        my_dict["compute_notebooks"]["infrastructure"] = {
            "summary_tables": {"parameter_groups": {"none": {}}},
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

    if "LDF" in my_dict["compute_notebooks"].get("lnd", {}):
        if "external_tool" not in my_dict["compute_notebooks"]["lnd"]["LDF"]:
            my_dict["compute_notebooks"]["lnd"]["LDF"]["external_tool"] = {}
        my_dict["compute_notebooks"]["lnd"]["LDF"]["external_tool"]["defaults_file"] = (
            os.path.join(
                cupid_root,
                "externals",
                "LDF",
                "lib",
                "ldf_variable_defaults.yaml",
            )
        )
        my_dict["compute_notebooks"]["lnd"]["LDF"]["external_tool"]["regions_file"] = (
            os.path.join(cupid_root, "externals", "LDF", "lib", "regions_lnd.yaml")
        )

    if "Greenland_SMB_visual_compare_obs" in my_dict["compute_notebooks"].get(
        "glc",
        {},
    ):
        my_dict["compute_notebooks"]["glc"]["Greenland_SMB_visual_compare_obs"][
            "parameter_groups"
        ]["none"]["climo_nyears"] = climo_nyears

    # Regional Ocean Open Boundary Conditions needs access to ocean input directory
    # The ocean input directory is (hackily) accessible through the case root directory
    if "Regional_Ocean_OBC" in my_dict["compute_notebooks"].get("ocn", {}):
        my_dict["compute_notebooks"]["ocn"]["Regional_Ocean_OBC"]["parameter_groups"][
            "none"
        ]["case_root"] = case_root

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


def standardize_cupid_comparison_field(
    cupid_comparison_input,
    name,
    num_cases,
    allow_single_val=True,
):
    """--cupid-comparison-* arguments can take several forms:
    1. A string representing a comma-separated list
    2. A string that should be treated as the value for every comparison case
    3. A list of values corresponding to each case

    This function converts arguments of type [1] or [2] to that of type [3],
    and then ensures that the resulting list is the proper size.
    """
    try:
        old_limit = sys.tracebacklimit
    except AttributeError:  # no tracebacklimit set
        old_limit = None
    sys.tracebacklimit = 0
    if isinstance(cupid_comparison_input, str):
        cupid_comparison_input = cupid_comparison_input.split(",")
    if len(cupid_comparison_input) == 1 and num_cases > 1 and allow_single_val:
        cupid_comparison_input = num_cases * [cupid_comparison_input[0]]
    if len(cupid_comparison_input) != num_cases:
        print(cupid_comparison_input)
        raise ValueError(
            f"Need {name} argument to be length {num_cases}, not {len(cupid_comparison_input)}",
        )
    if old_limit:
        sys.tracebacklimit = old_limit
    else:
        del sys.tracebacklimit
    return cupid_comparison_input


if __name__ == "__main__":
    generate_cupid_config()
