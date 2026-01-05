"""Utilities for generating parallelizable plot loops.

This module provides functions for creating maps and plots across multiple cases,
crops, and time ranges. It supports generating comparative visualizations with
optional key case comparisons and customizable plot parameters.
"""
from __future__ import annotations

import os
import sys
import warnings

from bokeh_html_utils import sanitize_filename
from dask.distributed import as_completed
from dask.distributed import Client
from plotting_utils import get_dummy_map
from plotting_utils import get_key_case
from plotting_utils import get_mean_map
from results_maps import DEFAULT_NO_VRANGE
from results_maps import ResultsMaps

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)
# pylint: disable=wrong-import-position,import-error
from ctsm_postprocessing.crops.crop_case_list import CropCaseList  # noqa: E402
from ctsm_postprocessing.crops.cropcase import CropCase  # noqa: E402

SUBMISSION_INDENT = "   "


def get_figpath_with_keycase(fig_path, key_case, key_case_dict):
    """Generate a figure path with key case identifier appended.

    If there is only one key case, returns the original path unchanged.
    Otherwise, appends the key case name to the filename before the extension.

    Args:
        fig_path: Original figure file path
        key_case: Key case identifier string
        key_case_dict: Dictionary of key cases

    Returns:
        str: Modified figure path with key case identifier if needed
    """
    if len(key_case_dict) == 1:
        return fig_path
    dirname = os.path.dirname(fig_path)
    basename = os.path.basename(fig_path)
    root, ext = os.path.splitext(basename)
    root += "_" + key_case
    root = sanitize_filename(root)
    basename = root + ext
    fig_path = os.path.join(dirname, basename)
    return fig_path


def plot_loop(
    *,
    get_mean_fn: callable,
    key_diff_abs_error: bool,
    results_da_name: str,
    img_dir: str,
    dask_client: Client,
    case_list: CropCaseList,
    opts: dict,
    crop_dict: dict,
    incl_yrs_ranges_dict: dict,
    key_case_dict: dict,
    get_mean_fn_args: list = None,
    get_mean_fn_kwargs: dict = None,
    custom_dropdown_items: list = None,
    custom_radio_items: list = None,
    vrange: tuple = DEFAULT_NO_VRANGE,
):
    """Generate plots for all combinations of crops, time ranges, and key cases.

    This is the main entry point for creating a series of comparative maps across
    multiple cases, crops, and time periods. It iterates through all combinations
    and generates individual figures for each. Supports parallel execution via Dask
    when a client is provided.

    Args:
        get_mean_fn: Function to compute mean values for a case
        get_mean_fn_args: List of positional arguments to pass to get_mean_fn
        get_mean_fn_kwargs: Dictionary of keyword arguments to pass to get_mean_fn
        key_diff_abs_error: Whether difference from key case should be diff. of absolute errors
        results_da_name: Name for the results DataArray
        img_dir: Directory path where images will be saved
        dask_client: Dask distributed client for parallel execution, or None for serial
        case_list: List of cases to process
        opts: Dictionary of options including 'verbose' and 'case_legend_list'
        crop_dict: Dictionary mapping crop identifiers to crop names
        incl_yrs_ranges_dict: Dictionary of year ranges to plot
        key_case_dict: Dictionary of key cases for comparison
        custom_dropdown_items: Optional list of custom dropdown menu items
        custom_radio_items: Optional list of custom radio button items
        vrange: Optional tuple specifying value range for colorbar

    Note:
        When dask_client is provided, figures are generated in parallel using Dask's
        distributed scheduler. The function waits for all tasks to complete and
        performs cleanup to free worker memory.
    """

    # To avoid pylint "dangerous default value" warning
    if custom_dropdown_items is None:
        custom_dropdown_items = []
    if custom_radio_items is None:
        custom_radio_items = []
    if get_mean_fn_args is None:
        get_mean_fn_args = []
    if get_mean_fn_kwargs is None:
        get_mean_fn_kwargs = {}

    # For Dask parallel execution
    parallel = bool(dask_client)
    if parallel:
        futures = []

    for crop in crop_dict.values():
        case_list_thiscrop = case_list.sel(crop=crop)

        for (
            incl_yrs_range_input,
            yr_range_str,
            time_slice,
        ) in incl_yrs_ranges_dict.plot_items():
            suptitle = None
            for key_case_key, key_case_value in key_case_dict.items():

                # Get figure output path
                join_list = (
                    custom_dropdown_items + [crop, yr_range_str] + custom_radio_items
                )
                if len(key_case_dict) > 1:
                    join_list.append(key_case_key)
                fig_basename = sanitize_filename("_".join(join_list)) + ".png"
                fig_path = os.path.join(img_dir, fig_basename)

                kwargs = {
                    "get_mean_fn": get_mean_fn,
                    "get_mean_fn_args": get_mean_fn_args,
                    "get_mean_fn_kwargs": get_mean_fn_kwargs,
                    "key_diff_abs_error": key_diff_abs_error,
                    "results_da_name": results_da_name,
                    "fig_path": fig_path,
                    "opts": opts,
                    "vrange": vrange,
                    "crop": crop,
                    "case_list_thiscrop": case_list_thiscrop,
                    "incl_yrs_range_input": incl_yrs_range_input,
                    "yr_range_str": yr_range_str,
                    "time_slice": time_slice,
                    "suptitle": suptitle,
                    "key_case_value": key_case_value,
                }

                if opts["verbose"]:
                    print(f"Submitting {crop} {yr_range_str}, {key_case_key}...")

                with warnings.catch_warnings():
                    # I'd like to actually resolve this warning rather than just suppressing
                    # it, but it is *complicated*.
                    warnings.filterwarnings("ignore", message=".*sending large graph.*")

                    if parallel:
                        future = dask_client.submit(_one_figure, **kwargs)
                        futures.append(future)
                        if len(futures) >= opts["max_parallel_jobs"]:
                            wait_for_jobs_to_finish(dask_client, opts, futures)
                            futures = []
                    else:
                        _one_figure(**kwargs)

    # Wait for all jobs to complete
    if parallel:
        wait_for_jobs_to_finish(dask_client, opts, futures)


def wait_for_jobs_to_finish(dask_client, opts, futures):
    if opts["verbose"]:
        print("Processing...")
    n_futures = len(futures)
    n_complete = 0
    for completed_future in as_completed(futures):
        result = completed_future.result()
        n_complete += 1
        if opts["verbose"]:
            print(f"{n_complete}/{n_futures} done: {result}")
        # Explicitly delete result to free memory
        del result
        # Cancel and delete the future itself
        completed_future.cancel()
        del completed_future

    # Clean up distributed worker memory
    del futures  # In case any futures didn't complete somehow
    dask_client.run(lambda: __import__("gc").collect())


def _one_figure(
    *,
    get_mean_fn: callable,
    get_mean_fn_args: list,
    get_mean_fn_kwargs: dict,
    key_diff_abs_error: bool,
    results_da_name: str,
    fig_path: str,
    opts: dict,
    vrange: tuple,
    crop: str,
    case_list_thiscrop: CropCaseList,
    incl_yrs_range_input,
    yr_range_str: str,
    time_slice: slice,
    suptitle: str,
    key_case_value: str,
) -> str:
    """Generate a single figure for a specific crop, time range, and key case.

    This function processes all cases for a given crop and time period, creating
    a multi-panel figure with one panel per case. It handles key case comparisons
    and saves the resulting figure to disk. Designed to be called either serially
    or as a Dask task for parallel execution.

    Note that any print() statements here won't be seen during or after parallel execution, but
    warnings will be unless suppressed at the Client level.

    Args:
        get_mean_fn: Function to compute mean values for a case
        get_mean_fn_args: List of positional arguments to pass to get_mean_fn
        get_mean_fn_kwargs: Dictionary of keyword arguments to pass to get_mean_fn
        key_diff_abs_error: Whether difference from key case should be diff. of absolute errors
        results_da_name: Name for the results DataArray
        fig_path: File path where figure will be saved
        opts: Dictionary of options including 'verbose', 'case_legend_list', and 'key_case'
        custom_dropdown_items: List of custom dropdown menu items
        custom_radio_items: List of custom radio button items
        vrange: Tuple specifying value range for colorbar
        crop: Crop name for this figure
        case_list_thiscrop: List of cases filtered for this crop
        incl_yrs_range_input: Year range input specification
        yr_range_str: String representation of year range
        time_slice: Time slice object for data selection
        suptitle: Super title for the figure (or None to auto-generate)
        key_case_key: Key identifier for the key case
        key_case_value: Value/configuration for the key case

    Returns:
        str: The figure's super title, used for completion status messages
    """

    # Get key case, if needed
    key_case = get_key_case(
        opts["case_legend_list"],
        key_case_value,
        case_list_thiscrop,
    )

    results = ResultsMaps(vrange=vrange, incl_yrs_range=incl_yrs_range_input)

    case_incl_yr_dict = {}
    map_keycase_dict_io = None
    for c, case in enumerate(case_list_thiscrop):
        results, case_incl_yr_dict, suptitle = _one_case(
            get_mean_fn=get_mean_fn,
            get_mean_fn_args=get_mean_fn_args,
            get_mean_fn_kwargs=get_mean_fn_kwargs,
            key_diff_abs_error=key_diff_abs_error,
            results_da_name=results_da_name,
            opts=opts,
            crop=crop,
            yr_range_str=yr_range_str,
            time_slice=time_slice,
            suptitle=suptitle,
            key_case=key_case,
            results=results,
            case_incl_yr_dict=case_incl_yr_dict,
            c=c,
            case=case,
            map_keycase_dict_io=map_keycase_dict_io,
        )

    # Plot
    results.plot(
        subplot_title_list=opts["case_legend_list"],
        suptitle=suptitle,
        one_colorbar=(key_case_value is None),
        fig_path=fig_path,
        key_plot=key_case_value,
        case_incl_yr_dict=case_incl_yr_dict,
    )

    return suptitle


def _one_case(
    *,
    get_mean_fn: callable,
    get_mean_fn_args: list,
    get_mean_fn_kwargs: dict,
    key_diff_abs_error: bool,
    results_da_name: str,
    opts: dict,
    crop: str,
    yr_range_str: str,
    time_slice: slice,
    suptitle: str,
    key_case: CropCase,
    results: ResultsMaps,
    case_incl_yr_dict: dict,
    c: int,
    case: CropCase,
    map_keycase_dict_io: dict,
) -> str:
    """Process a single case and add its results to the ResultsMaps object.

    This function computes the mean map for one case, stores timing information,
    adds the results to the ResultsMaps collection, and generates/returns the
    figure super title.

    Note that any print() statements here won't be seen during or after parallel execution, but
    warnings will be unless suppressed at the Client level.

    Args:
        get_mean_fn: Function to compute mean values for a case
        get_mean_fn_args: List of positional arguments to pass to get_mean_fn
        get_mean_fn_kwargs: Dictionary of keyword arguments to pass to get_mean_fn
        key_diff_abs_error: Whether difference from key case should be diff. of absolute errors
        results_da_name: Name for the results DataArray
        opts: Dictionary of options including 'case_legend_list'
        crop: Crop name being processed
        yr_range_str: String representation of year range
        time_slice: Time slice object for data selection
        suptitle: Existing super title (or None to generate new one)
        key_case: Key case CropCase object for comparison (or None)
        results: ResultsMaps object to store this case's results
        case_incl_yr_dict: Dictionary to store year range info per case
        c: Index of current case in case list
        case: CropCase object being processed
        map_keycase_dict_io: Dictionary for key case map caching (or None)

    Returns:
        str: Super title for the figure
    """
    case_legend = opts["case_legend_list"][c]

    (
        n_timesteps,
        map_clm,
        case_first_yr,
        case_last_yr,
        map_keycase_dict_io,
    ) = get_mean_map(
        case,
        key_case,
        key_diff_abs_error,
        get_mean_fn,
        *get_mean_fn_args,
        map_keycase_dict_io=map_keycase_dict_io,
        time_slice=time_slice,
        debug=opts["debug"],
        **get_mean_fn_kwargs,
    )

    # Save time info
    if n_timesteps == 0:
        case_incl_yr_dict[case_legend] = None
    else:
        case_incl_yr_dict[case_legend] = [case_first_yr, case_last_yr]

    # Save to ResultsMap
    if map_clm is None:
        map_clm = get_dummy_map()
    results[case_legend] = map_clm
    results[case_legend].name = results_da_name

    # Get the overall title for the figure. Only need to do this once,
    # which is why it's in this if-statement.
    if suptitle is None:
        suptitle = f"{results[case_legend].name}: {crop} [{yr_range_str}]"

    return results, case_incl_yr_dict, suptitle
