"""
Plotting utilities for land model diagnostics.

This module provides utilities for creating and managing map-based visualizations
of land model output data. It includes functions for comparing grids, calculating
differences between datasets, and a class for managing multiple map plots with
consistent formatting and colorbars.

Key Components:
    - Grid comparison and validation functions
    - Map difference calculation utilities
    - ResultsMaps class for multi-panel map visualizations

Default Colormaps:
    - Sequential: viridis (for single datasets)
    - Diverging: coolwarm (for differences)
    - Diverging (diff-of-diff): PiYG_r (for differences of differences)
"""
from __future__ import annotations

import warnings

import numpy as np
import xarray as xr
from dict_slice_str_indexed import DictSliceStrIndexed

NO_INTSXN_TIME_SLICE = None
RESULT_MAP_NO_UNITS_MSG = "Results map from this_fn() is missing units attribute"


def check_grid_match(grid0, grid1, tol=0):
    """
    Check whether latitude or longitude values match between two grids.

    This function compares two grid arrays (typically latitude or longitude coordinates)
    to determine if they match within a specified tolerance. It handles both xarray
    DataArrays and numpy arrays, and properly accounts for NaN values.

    Parameters
    ----------
    grid0 : array-like or xr.DataArray
        First grid to compare (e.g., latitude or longitude values).
    grid1 : array-like or xr.DataArray
        Second grid to compare (e.g., latitude or longitude values).
    tol : float, optional
        Tolerance for considering values as matching. Default is 0 (exact match).

    Returns
    -------
    match : bool
        True if grids match within tolerance, False otherwise.
    max_abs_diff : float or None
        Maximum absolute difference between the grids. None if shapes don't match.

    Warnings
    --------
    RuntimeWarning
        If NaN values are present in the grids or if NaN patterns don't match.
    """
    # Check if shapes match first
    if grid0.shape != grid1.shape:
        return False, None

    # Extract numpy arrays if xarray DataArrays were provided
    if hasattr(grid0, "values"):
        grid0 = grid0.values
    if hasattr(grid1, "values"):
        grid1 = grid1.values

    # Calculate absolute differences
    abs_diff = np.abs(grid1 - grid0)

    # Handle NaN values
    if np.any(np.isnan(abs_diff)):
        if np.any(np.isnan(grid0) != np.isnan(grid1)):
            warnings.warn("NaN(s) in grid don't match", RuntimeWarning)
            return False, None
        warnings.warn("NaN(s) in grid", RuntimeWarning)

    # Find maximum difference and check against tolerance
    max_abs_diff = np.nanmax(abs_diff)
    match = max_abs_diff < tol

    return match, max_abs_diff


def get_difference_map(da0, da1, *, name=None, units=None):
    """
    Calculate the difference between two maps (da1 - da0).

    This function computes the difference between two xarray DataArrays,
    ensuring that their dimensions and sizes match before performing the
    subtraction.

    Parameters
    ----------
    da0 : xr.DataArray
        First DataArray (subtracted from da1).
    da1 : xr.DataArray
        Second DataArray (minuend).

    Returns
    -------
    da_diff : xr.DataArray
        Difference map (da1 - da0).

    Raises
    ------
    RuntimeError
        If dimensions or sizes don't match between the input DataArrays,
        or if the result has unexpected dimensions.
    """
    # Verify that input DataArrays have matching dimensions
    if not all(da1.sizes[d] == da0.sizes[d] for d in da1.dims):
        raise RuntimeError(
            f"Size mismatch between da1 ({da1.sizes}) and da0 ({da0.sizes})",
        )

    # Calculate difference
    da_diff = da1 - da0

    # Verify that result has expected dimensions
    if not all(da1.sizes[d] == da_diff.sizes[d] for d in da1.dims):
        raise RuntimeError(
            f"Size mismatch between da1 ({da1.sizes}) and map_diff ({da_diff.sizes})",
        )

    # Save metadata, if supplied
    if name is not None:
        da_diff.name = name
    if units is not None:
        da_diff.attrs["units"] = units

    return da_diff


def interp_key_case_grid(case_name, key_case_name, da, da_key_case):
    lats_match = check_grid_match(da["lat"], da_key_case["lat"])
    lons_match = check_grid_match(da["lon"], da_key_case["lon"])

    # Interpolate reference case to current grid if needed
    if not (lats_match and lons_match):
        print(
            f"Nearest-neighbor interpolating {key_case_name} to match {case_name} grid",
        )
        da_key_case = da_key_case.interp_like(da, method="nearest")
    return da_key_case


def get_key_diff(key_diff_abs_error, da, da_key_case):
    da_attrs = da.attrs
    # TODO: Check for units match between da and da_key_case?
    if key_diff_abs_error:
        # Difference in absolute error: |da| - |da_key|
        da = get_difference_map(abs(da_key_case), abs(da))
    else:
        # Simple difference: da - da_key
        da = get_difference_map(da_key_case, da)
    da.attrs = da_attrs
    return da


def get_maturity_level_from_stat(stat_input):
    """
    Separate maturity level from stat input string, if any
    """
    maturity = None
    if "@" in stat_input:
        stat_input, maturity = stat_input.split("@")
    return stat_input, maturity


def get_yr_range(ds):
    if "time" not in ds.dims or ds.sizes["time"] == 0:
        return [None, None]
    first_year = ds["time"].values[0].year
    last_year = ds["time"].values[-1].year
    return [first_year, last_year]


def _get_range_overlap(*ranges):
    """
    Find the overlap between an arbitrary number of year ranges.

    This function calculates the intersection of multiple year ranges, returning
    the overlapping period if one exists.

    Parameters
    ----------
    *ranges : list or tuple
        Variable number of ranges, each as [start, end] or (start, end) where
        both start and end are inclusive. A range of [None, None] indicates
        no valid range.

    Returns
    -------
    list or None
        [start, end] of the overlapping range (inclusive), or None if:
        - No ranges are provided
        - Any range is [None, None]
        - No overlap exists between the ranges

    Raises
    ------
    ValueError
        If any range doesn't have exactly two elements, or if end < start.
    """
    if len(ranges) == 0:
        return None

    # Check for [None, None] in any range and validate range format
    for i, r in enumerate(ranges):
        # Check that range has exactly two elements
        if len(r) != 2:
            raise ValueError(
                f"Range at position {i} has {len(r)} elements, expected 2: {r}",
            )

        # Check for [None, None]
        if r == [None, None] or r == (None, None):
            return None

        # Validate that end >= start
        if r[1] < r[0]:
            raise ValueError(f"Range at position {i} has end < start: [{r[0]}, {r[1]}]")

    # Find the maximum start and minimum end
    result_start = max(r[0] for r in ranges)
    result_end = min(r[1] for r in ranges)

    # No overlap if start > end
    if result_start > result_end:
        return None

    return [result_start, result_end]


def get_mean_map(
    case,
    key_case,
    key_diff_abs_error,
    this_fn,
    *args,
    map_keycase_dict_io,
    time_slice,
    **kwargs,
):
    """
    Note that time_slice is allowed to be unspecified, but this is NOT recommended as it can result
    in the case mean and key case mean being taken over different years. It is only provided to
    test for differences during development.
    """
    calc_diff_from_key_case = key_case is not None and case.name != key_case.name

    if not map_keycase_dict_io:
        map_keycase_dict_io = DictSliceStrIndexed()
    else:
        assert isinstance(map_keycase_dict_io, DictSliceStrIndexed)

    if time_slice is not None:
        time_slice = _get_intsxn_time_slice_of_cases(
            case,
            key_case,
            time_slice,
            calc_diff_from_key_case,
        )

    # Get this case's map
    if time_slice is None:
        n_timesteps = 0
    else:
        case = case.sel(time=time_slice)
        n_timesteps = case.cft_ds.sizes["time"]
    if n_timesteps == 0:
        map_case = xr.full_like(case.cft_ds["area"], fill_value=np.nan)
        case_first_yr = None
        case_last_yr = None
    else:
        map_case = this_fn(
            case,
            *args,
            **kwargs,
        )
        assert "units" in map_case.attrs, RESULT_MAP_NO_UNITS_MSG
        case_first_yr = case.cft_ds["time"].values[0].year
        case_last_yr = case.cft_ds["time"].values[-1].year

    # Get map_clm as difference between case and key_case, if doing so.
    # Otherwise just use map_case.
    if calc_diff_from_key_case and n_timesteps > 0:
        key = (time_slice, case.cft_ds.attrs["resolution"])
        if key in map_keycase_dict_io.keys():
            map_key_case = map_keycase_dict_io[*key]  # fmt: skip
        else:
            key_case = key_case.sel(time=time_slice)
            map_key_case = this_fn(
                key_case,
                *args,
                **kwargs,
            )
            assert "units" in map_key_case.attrs, RESULT_MAP_NO_UNITS_MSG

            # Interpolate key case map to this case's grid, if needed
            map_key_case = interp_key_case_grid(
                case.name,
                key_case.name,
                map_case,
                map_key_case,
            )

            # Save for later cases that will use the same key case map
            map_keycase_dict_io[*key] = map_key_case  # fmt: skip

        # Get difference map between this case and key case
        map_clm = get_key_diff(key_diff_abs_error, map_case, map_key_case)
    else:
        map_clm = map_case
    return n_timesteps, map_clm, case_first_yr, case_last_yr, map_keycase_dict_io


def _get_intsxn_time_slice_of_cases(
    case,
    key_case,
    time_slice_in,
    calc_diff_from_key_case,
):
    """
    Given a case, key case, and time slice, return the time slice that is the intersection among
    all three.
    """

    if not calc_diff_from_key_case:
        time_slice = time_slice_in
    else:
        time_slice = get_instxn_time_slice_of_ds(
            time_slice_in,
            case.cft_ds,
            key_case.cft_ds,
        )

    return time_slice


def get_instxn_time_slice_of_ds(time_slice_in, *args):
    """
    Given a time slice and an arbitrary number of Datasets, return the time slice that is the
    intersection among all.
    """
    args = [ds.sel(time=time_slice_in) for ds in args]
    intsxn_yr_range = _get_range_overlap(*[get_yr_range(ds) for ds in args])
    if intsxn_yr_range is None:
        return NO_INTSXN_TIME_SLICE

    time_slice = slice(
        f"{intsxn_yr_range[0]}-01-01",
        f"{intsxn_yr_range[1]}-12-31",
    )

    return time_slice


def get_key_case(case_legend_list, key_case_value, case_list):
    key_case = None
    if key_case_value is not None:
        for c, case_legend in enumerate(case_legend_list):
            if case_legend == key_case_value:
                key_case = case_list[c]
                break
        if key_case is None:
            raise RuntimeError(
                f"Case '{key_case_value}' not found in case_legend_list",
            )
    return key_case
