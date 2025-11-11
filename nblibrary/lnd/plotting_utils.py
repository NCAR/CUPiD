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
from dict_slice_str_indexed import DictSliceStrIndexed


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


def get_yr_range(ds):
    if "time" not in ds.dims or ds.sizes["time"] == 0:
        return [None, None]
    first_year = ds["time"].values[0].year
    last_year = ds["time"].values[-1].year
    return [first_year, last_year]


def _get_range_overlap(list0, list1):
    if list0 == [None, None]:
        return None
    x = range(list0[0], list0[1] + 1)
    y = range(list1[0], list1[1] + 1)
    xs = set(x)
    intsxn = list(xs.intersection(y))
    if len(intsxn) == 0:
        return None
    return [intsxn[0], intsxn[-1]]


def get_mean_map(
    case,
    key_case,
    key_diff_abs_error,
    this_fn,
    *args,
    map_keycase_dict_io,
    time_slice=None,
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

    # Get this case's map
    case_cft_ds = case.cft_ds
    if time_slice is not None:
        time_slice = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice,
            calc_diff_from_key_case,
        )
        case_cft_ds = case_cft_ds.sel(time=time_slice)
    n_timesteps = case_cft_ds.sizes["time"]
    if n_timesteps == 0:
        case_first_yr = None
        case_last_yr = None
    else:
        case_first_yr = case_cft_ds["time"].values[0].year
        case_last_yr = case_cft_ds["time"].values[-1].year

    map_case = this_fn(
        case_cft_ds,
        *args,
        **kwargs,
    )

    # Get map_clm as difference between case and key_case, if doing so.
    # Otherwise just use map_case.
    if calc_diff_from_key_case:
        key = (time_slice, case.cft_ds.attrs["resolution"])
        if key in map_keycase_dict_io.keys():
            map_key_case = map_keycase_dict_io[*key]  # fmt: skip
        else:
            key_case_cft_ds = key_case.cft_ds
            if time_slice is not None:
                key_case_cft_ds = key_case_cft_ds.sel(time=time_slice)
            map_key_case = this_fn(
                key_case_cft_ds,
                *args,
                **kwargs,
            )

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


def _get_intsxn_time_slice_if_needed(
    case,
    key_case,
    time_slice_in,
    calc_diff_from_key_case,
):
    if time_slice_in is None:
        return None

    if not calc_diff_from_key_case:
        time_slice = time_slice_in
    else:
        case_yr_range = get_yr_range(case.cft_ds.sel(time=time_slice_in))
        key_case_yr_range = get_yr_range(key_case.cft_ds.sel(time=time_slice_in))
        if key_case_yr_range == [None, None]:
            raise NotImplementedError(
                f"key case '{key_case.name}' has no years in {time_slice_in}",
            )
        intsxn_yr_range = _get_range_overlap(case_yr_range, key_case_yr_range)
        if intsxn_yr_range is None:
            time_slice = slice(
                f"{key_case_yr_range[0]}-01-01",
                f"{key_case_yr_range[1]}-12-31",
            )
        else:
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
