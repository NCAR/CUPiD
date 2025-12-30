"""
Module for regridding EarthStat data.
"""
from __future__ import annotations

import gc
import warnings
from copy import deepcopy

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
            reuse_weights=False,
        )
    mask_regridded = regridder(mask)

    # Clean up mask to free memory
    del mask

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

    # Deep copy ds_in as it's needed for correctness
    ds_in = deepcopy(ds_in)

    # Sense checks
    assert (area_in is None) == (area_out is None)
    if area_in is not None:
        area_out = area_out * area_in.sum() / area_out.sum()

    # Get mask of input data
    if mask_var is None:
        mask_var = var
    mask_in = ds_in[mask_var]

    # Extract data and save things we'll need later
    da_in = ds_in[var]
    var_attrs = ds_in[var].attrs
    var_sum_before = ds_in[var].sum() if "conservative" in method else None

    if area_in is not None:
        # da_in /= area_in
        da_in_temp = da_in / area_in
        da_in = da_in_temp.where(area_in > 0)
        del da_in_temp
    data_filled = da_in.fillna(0.0)

    # Clean up things we no longer need
    del da_in, ds_in

    # xesmf might look for a "mask" variable:
    # https://coecms-training.github.io/parallel/case-studies/regridding.html
    # Create a deep copy to avoid modifying the input ds_target
    ds_target_copy = None
    if "landmask" in ds_target:
        ds_target_copy = deepcopy(ds_target)
        ds_target_copy["mask"] = ds_target_copy["landmask"].fillna(0)
        ds_target_for_regrid = ds_target_copy
    else:
        ds_target_for_regrid = ds_target

    # Create and apply regridder
    regridder, mask_regridded = _get_regridder_and_mask(
        data_filled,
        mask_in,
        ds_target_for_regrid,
        method,
    )
    da_out = regridder(data_filled)

    # Clean up data_filled immediately after use
    del data_filled

    # Clean up mask_regridded immediately after use
    del mask_regridded

    # Clean up ds_target copy if we made one
    if ds_target_copy is not None:
        del ds_target_copy
        del ds_target_for_regrid

    # Force garbage collection after regridding
    gc.collect()

    # NO; this adds an 8-9 percentage point overestimate in test variables HarvestArea and
    # Production. Which makes sense: These are not per-m2-of-gridcell numbers; these are gridcell
    # TOTALS.
    # # Normalize to account for partial coverage
    # da_out = da_out / mask_regridded

    # apply landmask from CLM target grid
    da_out = da_out * ds_target["landmask"]

    if area_out is not None:
        da_out *= area_out

    # Force computation to avoid keeping lazy references
    da_out = da_out.compute()

    # If we chose a conservative method, assume we want the global sums to match before and after.
    if "conservative" in method:

        # Compute sums once and store to avoid recreating arrays
        var_sum_after = da_out.sum()

        # Print error in global sum introduced by regridding
        before = var_sum_before.values
        after = var_sum_after.values
        pct_diff = (after - before) / before * 100
        if "units" in var_attrs:
            units = var_attrs["units"]
        else:
            units = "unknown units"
        print(f"{INDENT}{var} ({units}):")
        print(f"{2*INDENT}Global sum before: {before:.2e}")
        print(f"{2*INDENT}Global sum  after: {after:.2e} ({pct_diff:.1f}% diff)")

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

    return da_out
