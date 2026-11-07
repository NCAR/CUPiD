"""
Useful functions for calculations related to CLM crop growing seasons
"""

from __future__ import annotations

import xarray as xr

from externals.ctsm_postprocessing.crops import combine_cft_to_crop

# Southern Hemisphere "overwintering" means spanning Jul. 1/2
SH_MIDWINTER_DOY = 182.5


def cft_ds_overwintering(cft_ds: xr.Dataset) -> xr.Dataset:
    """
    Calculate overwintering for each calendar year's harvests.

    Identifies crops that overwinter (span the winter solstice) in both Northern and Southern
    Hemispheres. For Northern Hemisphere, overwintering means spanning Dec. 31/Jan. 1. For
    Southern Hemisphere, overwintering means spanning Jul. 1/2.

    Parameters
    ----------
    cft_ds : xarray.Dataset
        Dataset containing CFT-level crop data with HDATES, SDATES_PERHARV, pfts1d_lat,
        HARVEST_REASON_PERHARV, cft_harv_area, and cft_crop variables.

    Returns
    -------
    xarray.Dataset
        Dataset with added overwinter_area and overwinter_area_crop variables.
    """

    # Whether the crop is in the Northern or Southern Hemisphere
    is_nh = cft_ds["pfts1d_lat"] >= 0

    # If Northern, "overwintering" means spanning Dec. 31/Jan. 1
    nh_overwinter = is_nh & (cft_ds["HDATES"] < cft_ds["SDATES_PERHARV"])
    sh_overwinter = (
        ~is_nh
        & (cft_ds["SDATES_PERHARV"] < SH_MIDWINTER_DOY)
        & (cft_ds["HDATES"] > SH_MIDWINTER_DOY)
    )

    # Save
    overwinter = (nh_overwinter | sh_overwinter) & (
        cft_ds["HARVEST_REASON_PERHARV"] > 0
    )
    cft_ds["overwinter_area"] = (overwinter * cft_ds["cft_harv_area"]).sum(
        dim="mxharvests",
    )
    cft_ds = combine_cft_to_crop.combine_cft_to_crop(
        cft_ds,
        "overwinter_area",
        "overwinter_area_crop",
        method="sum",
    )

    # Add units
    # TODO: This should be changed to happen automatically elsewhere!
    cft_ds["overwinter_area_crop"].attrs["units"] = "m2"

    return cft_ds


def cft_ds_gslen(cft_ds: xr.Dataset) -> xr.Dataset:
    """
    Calculate growing season length for each crop, combining its constituent CFTs.

    Computes mean growing season length across CFTs within each crop, weighted by harvest area
    and masked to only include marketable harvests.

    Parameters
    ----------
    cft_ds : xarray.Dataset
        Dataset containing CFT-level crop data with GSLEN_PERHARV, MARKETABLE_HARVEST,
        cft_harv_area, and cft_crop variables.

    Returns
    -------
    xarray.Dataset
        Dataset with added gslen_perharv_cft and gslen_perharv_crop variables.
    """
    # Get original DataArray and units
    da = cft_ds["GSLEN_PERHARV"]
    units = da.attrs["units"]

    # Mask to just valid harvests
    cft_ds["gslen_perharv_cft"] = da.where(cft_ds["MARKETABLE_HARVEST"])
    cft_ds["gslen_perharv_cft"].attrs["units"] = units

    # Combine CFTs to crops
    cft_ds = combine_cft_to_crop.combine_cft_to_crop(
        cft_ds,
        "gslen_perharv_cft",
        "gslen_perharv_crop",
        method="mean",
        weights="cft_harv_area",
    )
    cft_ds["gslen_perharv_crop"].attrs["units"] = units

    return cft_ds
