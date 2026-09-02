#!/usr/bin/env python3

"""
Consistency check for CUPiD config file.
This module checks the consistency of the CUPiD config file,
ensuring that required keys are present and that their values
are of the correct type and length. It also converts string
values to lists of the appropriate length, if necessary.
"""

global_required_lists = [
    "case_names",
    "case_nicknames",
]

global_required_list_or_str = [
    "CESM_output_dir",
]

global_optional_list_or_str = [
    "ts_dir",
    "start_dates",
    "end_dates",
    "climo_start_years",
    "climo_end_years",
]

ts_list_or_str = [
    "start_years",
    "end_years",
    "mapping_file",
    "ts_done",
    "overwrite_ts",
    "ts_output_dir",
]

compute_notebooks_list_or_str = [
    "regridded_output",
    "grid_name",
    "case_align_years",
]

component_list = ["atm", "lnd", "ocn", "ice", "glc", "rof"]

compute_notebook_paths = [
    (
        "rof",
        "global_discharge_gauge_compare_obs",
        "parameter_groups",
        "none",
        "grid_name",
    ),
    (
        "rof",
        "global_discharge_ocean_compare_obs",
        "parameter_groups",
        "none",
        "grid_name",
    ),
    (
        "atm",
        "Global_PSL_NMSE_compare_obs_lens",
        "parameter_groups",
        "none",
        "regridded_output",
    ),
    (
        "atm",
        "TimeSeriesPlots",
        "parameter_groups",
        "none",
        "regridded_output",
    ),
    (
        "atm",
        "TimeSeriesPlots",
        "parameter_groups",
        "none",
        "case_align_years",
    ),
    ("atm", "ADF", "external_tool", "regridded_output"),
    ("lnd", "LDF", "external_tool", "regridded_output"),
]


def check_consistency(control):
    global_params = control["global_params"]
    timeseries_params = control["timeseries"]
    compute_notebooks_params = control["compute_notebooks"]

    for param in global_required_lists:
        if param not in global_params:
            raise KeyError(f"Missing required key '{param}' in global_params section.")
        if not isinstance(global_params[param], list):
            raise TypeError(f"Value for '{param}' in global_params must be a list.")
        if isinstance(global_params[param], list) and len(global_params[param]) != len(
            global_params["case_names"],
        ):
            raise ValueError(
                f"Length of '{param}' in global_params must match length of 'case_names'.",
            )

    expected_length = len(global_params["case_names"])

    for param in global_required_list_or_str + global_optional_list_or_str:
        if param in global_params:
            global_params[param], ErrorMessage = check_type_and_length(
                global_params[param],
                expected_length,
            )
            if ErrorMessage:
                raise TypeError(f"'{param}' in global_params: {ErrorMessage}")
        elif param in global_required_list_or_str:
            raise KeyError(f"Missing required key '{param}' in global_params section.")

    for component in component_list:
        if component in timeseries_params:
            if (
                "start_years" not in timeseries_params[component]
                or "end_years" not in timeseries_params[component]
            ):
                raise KeyError(
                    f"Missing 'start_years' or 'end_years' key in timeseries section for component '{component}'.",
                )

            else:
                for param in ts_list_or_str[
                    :3
                ]:  # Only check start_years, end_years, and mapping_file for each component
                    if param in timeseries_params[component]:
                        timeseries_params[component][param], ErrorMessage = (
                            check_type_and_length(
                                timeseries_params[component][param],
                                expected_length,
                            )
                        )
                        if ErrorMessage:
                            raise TypeError(
                                f"'{param}' in timeseries section for component '{component}': {ErrorMessage}",
                            )

    for param in ts_list_or_str[
        3:
    ]:  # Check the rest of the parameters for list or string
        if param in timeseries_params:
            timeseries_params[param], ErrorMessage = check_type_and_length(
                timeseries_params[param],
                expected_length,
            )
            if ErrorMessage:
                raise TypeError(
                    f"'{param}' in timeseries section for component '{component}': {ErrorMessage}",
                )

    for path in compute_notebook_paths:
        section = compute_notebooks_params
        path_exists = True

        for key in path[:-1]:
            if key not in section or not isinstance(section[key], dict):
                path_exists = False
                break
            section = section[key]

        if not path_exists:
            continue

        param = path[-1]
        if param not in section:
            continue

        full_path = "compute_notebooks" + "".join(f"['{key}']" for key in path)
        value = section[param]

        section[param], ErrorMessage = check_type_and_length(value, expected_length)
        if ErrorMessage:
            raise TypeError(f"{full_path}: {ErrorMessage}")

    return control


def check_type_and_length(value, expected_length):
    ErrorMessage = ""

    if isinstance(value, list):
        if len(value) != expected_length:
            ErrorMessage = f"Expected a list of length {expected_length}, but got a list of length {len(value)}."
        else:
            value = value
    elif isinstance(value, (str, bool, int)):
        value = [value] * expected_length
    elif value is not None:
        ErrorMessage = f"Value must be a list, string, boolean, integer, or None, but got {type(value)}."
    return value, ErrorMessage
