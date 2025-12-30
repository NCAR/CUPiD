"""
Module for regridding EarthStat data
"""
from __future__ import annotations

import warnings

import xarray as xr
import xesmf as xe

# One level's worth of indentation for messages
INDENT = "    "


def _get_regridder_and_mask(da_in, mask_in, ds_target, method):
    """Get regridder and mask"""
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
        )
    mask_regridded = regridder(mask)

    return regridder, mask_regridded


def regrid_to_clm(
    *,
    ds_in,
    var,
    ds_target,
    method="conservative",
    area_in=None,
    area_out=None,
    mask_var=None,
):
    """Regrid an observational dataset to a CLM target grid using conservative regridding"""

    # Sense checks
    assert (area_in is None) == (area_out is None)
    if area_in is not None:
        area_out = area_out * area_in.sum() / area_out.sum()

    # Get mask of input data
    if mask_var is None:
        mask_var = var
    mask_in = ds_in[mask_var]

    # Extract data
    da_in = ds_in[var]
    if area_in is not None:
        # da_in /= area_in
        da_in = da_in / area_in
        da_in = da_in.where(area_in > 0)
    data_filled = da_in.fillna(0.0)

    # xesmf might look for a "mask" variable:
    # https://coecms-training.github.io/parallel/case-studies/regridding.html
    if "landmask" in ds_target:
        ds_target["mask"] = ds_target["landmask"].fillna(0)

    # Create and apply regridder
    regridder, _ = _get_regridder_and_mask(
        da_in,
        mask_in,
        ds_target,
        method,
    )
    da_out = regridder(data_filled)

    # NO; this adds an 8-9 percentage point overestimate in test variables HarvestArea and
    # Production. Which makes sense: These are not per-m2-of-gridcell numbers; these are gridcell
    # TOTALS.
    # # Normalize to account for partial coverage
    # da_out = da_out / mask_regridded

    # apply landmask from CLM target grid
    da_out = da_out * ds_target["landmask"]

    if area_out is not None:
        da_out *= area_out

    # If we chose a conservative method, assume we want the global sums to match before and after.
    if "conservative" in method:

        # Print error in global sum introduced by regridding
        before = ds_in[var].sum().values
        after = da_out.sum().values
        pct_diff = (after - before) / before * 100
        if "units" in ds_in[var].attrs:
            units = ds_in[var].attrs["units"]
        else:
            units = "unknown units"
        print(f"{INDENT}{var} ({units}):")
        print(f"{2*INDENT}Global sum before: {before:.2e}")
        print(f"{2*INDENT}Global sum  after: {after:.2e} ({pct_diff:.1f}% diff)")

        # Adjust so global sum matches what we had before regridding
        print(f"{2*INDENT}Adjusting to match.")
        da_out = da_out * ds_in[var].sum() / da_out.sum()
        after = da_out.sum().values
        diff = after - before
        pct_diff = diff / before * 100
        print(f"{2*INDENT}Global diff final: {diff:.2e} ({pct_diff:.1f}%)")

    # Recover attributes
    da_out.attrs = ds_in[var].attrs

    # Destroy regridder to avoid memory leak?
    # https://github.com/JiaweiZhuang/xESMF/issues/53#issuecomment-2114209348
    # Doesn't seem to help much, if at all. Maybe a couple hundred MB.
    regridder.grid_in.destroy()
    regridder.grid_out.destroy()
    del regridder

    return da_out
