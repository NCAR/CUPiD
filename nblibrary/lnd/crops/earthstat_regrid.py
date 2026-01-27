"""
Module for regridding EarthStat data.
"""

from __future__ import annotations

import gc
import warnings
from copy import deepcopy

import numpy as np
import xarray as xr
import xesmf as xe

# One level's worth of indentation for messages
INDENT = "    "

# Earth radius in km
EARTH_RADIUS_KM = 6371.0


def _calculate_gridcell_area(da: xr.DataArray | xr.Dataset) -> xr.DataArray:
    """
    Calculate gridcell area from lat/lon coordinates using spherical geometry.

    This computes the true gridcell area based on Earth's spherical geometry,
    which doesn't depend on whether there's land in the cell or not.

    Parameters
    ----------
    da : xarray.DataArray | xarray.Dataset
        Containing 'lat' and 'lon' coordinates. If Dataset, uses the 'area' variable.

    Returns
    -------
    xarray.DataArray
        Calculated gridcell areas in km^2.

    Raises
    ------
    AssertionError
        If input area units are not 'km^2' or if calculated area contains NaN values.
    """
    if isinstance(da, xr.Dataset):
        da = da["area"]

    # Get lat/lon coordinates, as well as area variable if any
    lat = da["lat"]
    lon = da["lon"]

    # Calculate grid spacing
    dlat = abs(float(lat[1] - lat[0])) if len(lat) > 1 else 1.0
    dlon = abs(float(lon[1] - lon[0])) if len(lon) > 1 else 1.0

    # Special handling needed if original units not km2
    if "units" in da.attrs:
        units_in = da.attrs["units"]
        assert units_in == "km^2", f"Handle area units of {units_in}"

    # Calculate area for each gridcell
    # Area = R^2 * dlon_radians * (sin(lat_upper) - sin(lat_lower))
    lat_rad = np.deg2rad(lat)
    dlon_rad = np.deg2rad(dlon)
    dlat_rad = np.deg2rad(dlat)

    lat_upper = lat_rad + dlat_rad / 2
    lat_lower = lat_rad - dlat_rad / 2

    area_calculated = (
        EARTH_RADIUS_KM**2 * dlon_rad * (np.sin(lat_upper) - np.sin(lat_lower))
    )

    # Broadcast to 2D if needed (for lat x lon grids)
    if "lon" in da.dims:
        area_calculated = area_calculated * xr.ones_like(da["lon"])

    # Save original attributes
    area_calculated.attrs = da.attrs

    # There should be no NaN cells
    assert (
        not area_calculated.isnull().any()
    ), "_calculate_gridcell_area() should produce no NaN"

    return area_calculated


def _get_regridder_and_mask(
    da_in: xr.DataArray,
    mask_in: xr.DataArray,
    ds_target: xr.Dataset,
    method: str,
) -> tuple[xe.Regridder, xr.DataArray]:
    """
    Get regridder and regridded mask for interpolation.

    Parameters
    ----------
    da_in : xarray.DataArray
        Input data to be regridded.
    mask_in : xarray.DataArray
        Mask for the input data.
    ds_target : xarray.Dataset
        Target dataset defining the output grid.
    method : str
        Regridding method (e.g., 'conservative', 'bilinear').

    Returns
    -------
    tuple[xesmf.Regridder, xarray.DataArray]
        Tuple containing:
        - regridder: xESMF Regridder object
        - mask_regridded: Regridded mask DataArray
    """
    # Create mask
    mask = xr.where(~mask_in.notnull() | (mask_in == 0), 0.0, 1.0)

    # Not sure how much of a difference specifying this makes, but anyway
    if "conservative" in method:
        # Extrapolation not available for conservative regridding methods
        extrap_method = None
    else:
        extrap_method = "inverse_dist"

    # Create and apply regridder
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Latitude is outside of")
        regridder = xe.Regridder(
            da_in,
            ds_target,
            method=method,
            ignore_degenerate=True,
            extrap_method=extrap_method,
            reuse_weights=False,
        )
    mask_regridded = regridder(mask)

    # Clean up mask to free memory
    del mask

    return regridder, mask_regridded


def regrid_to_clm(
    *,
    ds_in: xr.Dataset,
    var: str,
    ds_target: xr.Dataset,
    method: str = "conservative",
    area_in: xr.DataArray | None = None,
    area_out: xr.DataArray | None = None,
    mask_var: str | None = None,
) -> xr.DataArray:
    """
    Regrid an observational dataset to a CLM target grid using conservative regridding.

    Parameters
    ----------
    ds_in : xarray.Dataset
        Input dataset to regrid.
    var : str
        Variable name to regrid.
    ds_target : xarray.Dataset
        Target CLM dataset defining the output grid.
    method : str, optional
        Regridding method. Default is 'conservative'.
    area_in : xarray.DataArray | None, optional
        Input gridcell areas. If None, areas are calculated from coordinates.
    area_out : xarray.DataArray | None, optional
        Output gridcell areas. If None, areas are calculated from coordinates.
    mask_var : str | None, optional
        Variable name to use for masking. If None, uses var.

    Returns
    -------
    xarray.DataArray
        Regridded data on the target grid.

    Raises
    ------
    AssertionError
        If area_in and area_out are not both None or both provided, or if output contains NaN.
    """

    # Deep copy ds_in so it doesn't get modified
    ds_in = deepcopy(ds_in)

    # Sense checks
    assert (area_in is None) == (area_out is None)

    # We don't want NaNs introduced to the output, so first let's make sure there are no NaNs in
    # our area variables. This should be gridcell area, but CLM saves NaN where there is no land
    # area. Fortunately, we can just replace the area variables, because we can compute gridcell
    # area a priori from the list of gridcell centers.
    if area_in is not None:
        area_in = _calculate_gridcell_area(area_in)
        area_out = _calculate_gridcell_area(area_out)

    # Get mask of input data
    if mask_var is None:
        mask_var = var
    mask_in = ds_in[mask_var]

    # Extract data and save things we'll need later
    da_in = ds_in[var]
    var_attrs = ds_in[var].attrs
    var_sum_before = ds_in[var].sum() if "conservative" in method else None
    # has_nan_before = da_in.isnull().any()

    if area_in is not None:
        # da_in /= area_in
        da_in_temp = da_in / area_in
        da_in = da_in_temp.where(area_in > 0)
        del da_in_temp
    data_filled = da_in.fillna(0.0)

    # Clean up things we no longer need
    del da_in, ds_in

    # Create and apply regridder
    regridder, mask_regridded = _get_regridder_and_mask(
        data_filled,
        mask_in,
        ds_target,
        method,
    )
    da_out = regridder(data_filled)

    # Clean up data_filled immediately after use
    del data_filled

    # Clean up mask_regridded immediately after use
    del mask_regridded

    # Force garbage collection after regridding
    gc.collect()

    # NO; this adds an 8-9 percentage point overestimate in test variables HarvestArea and
    # Production. Which makes sense: These are not per-m2-of-gridcell numbers; these are gridcell
    # TOTALS.
    # # Normalize to account for partial coverage
    # da_out = da_out / mask_regridded

    # NO; EarthStat data have no NaNs
    # # apply landmask from CLM target grid
    # da_out = da_out * ds_target["landmask"]

    if area_out is not None:
        da_out *= area_out

    # Force computation to avoid keeping lazy references
    da_out = da_out.compute()

    assert not da_out.isnull().any()

    # If we chose a conservative method, assume we want the global sums to match before and after.
    if "conservative" in method:

        # Compute sums once and store to avoid recreating arrays
        var_sum_after = da_out.sum()

        # Print error in global sum introduced by regridding
        before = var_sum_before.values
        after = var_sum_after.values
        diff = after - before
        pct_diff = diff / before * 100
        if "units" in var_attrs:
            units = var_attrs["units"]
        else:
            units = "unknown units"
        print(f"{INDENT}{var} ({units}):")
        print(f"{2*INDENT}Global sum before: {before:.2e}")
        print(f"{2*INDENT}Global sum  after: {after:.2e} ({pct_diff:.1f}% diff)")
        print(f"{2*INDENT}Global diff after: {diff:.2e} ({pct_diff:.1f}%)")

        # Adjust so global sum matches what we had before regridding
        print(f"{2*INDENT}Adjusting to match.")
        da_out = da_out * var_sum_before / var_sum_after

        # Clean up intermediate sum variables
        del var_sum_after

        after = da_out.sum().values
        diff = after - before
        pct_diff = diff / before * 100
        print(f"{2*INDENT}Global diff final: {diff:.2e} ({pct_diff:.1f}%)")
    del var_sum_before

    # Recover attributes
    da_out.attrs = var_attrs

    # Destroy regridder to avoid memory leak
    # https://github.com/JiaweiZhuang/xESMF/issues/53#issuecomment-2114209348
    regridder.grid_in.destroy()
    regridder.grid_out.destroy()
    del regridder

    # Force garbage collection to ensure cleanup
    gc.collect()

    assert not da_out.isnull().any()

    return da_out
