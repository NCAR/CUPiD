"""
Calculate some extra area, prod, yield, etc. variables
"""
# TODO: Move this to CropCase
from __future__ import annotations

import numpy as np
import xarray as xr


def extra_area_prod_yield_etc(case_list, opts):
    """
    Calculate some extra area, prod, yield, etc. variables
    """
    for case in case_list:
        case = _one_case(opts, case)

    return case_list


def _one_case(opts, case):
    """
    Process things for one case
    """
    case_ds = case.cft_ds

    # Set up for adding cft_crop variable
    cft_crop_array = np.full(case_ds.sizes["cft"], "", dtype=object)

    crop_cft_area_da = None
    crop_cft_prod_da = None
    for i, crop in enumerate(opts["crops_to_include"]):
        # Get data for CFTs of this crop
        crop_cft_area_da, crop_cft_prod_da = _one_crop(
            opts,
            case,
            case_ds,
            cft_crop_array,
            i,
            crop,
            crop_cft_area_da,
            crop_cft_prod_da,
        )

    # Add crop_cft_* variables to case_ds
    case_ds["crop_cft_area"] = crop_cft_area_da
    case_ds["crop_cft_prod"] = crop_cft_prod_da

    # Calculate CFT-level yield
    case_ds["crop_cft_yield"] = crop_cft_prod_da / crop_cft_area_da
    case_ds["crop_cft_yield"].attrs["units"] = (
        crop_cft_prod_da.attrs["units"] + "/" + crop_cft_area_da.attrs["units"]
    )

    # Collapse CFTs to individual crops
    case_ds["crop_area"] = crop_cft_area_da.sum(dim="cft", keep_attrs=True)
    case_ds["crop_prod"] = crop_cft_prod_da.sum(dim="cft", keep_attrs=True)

    # Calculate crop-level yield
    case_ds["crop_yield"] = case_ds["crop_prod"] / case_ds["crop_area"]
    case_ds["crop_yield"].attrs["units"] = (
        case_ds["crop_prod"].attrs["units"] + "/" + case_ds["crop_area"].attrs["units"]
    )

    # Save cft_crop variable
    case_ds["cft_crop"] = xr.DataArray(
        data=cft_crop_array,
        dims=["cft"],
        coords={"cft": case_ds["cft"]},
    )

    # Area harvested
    hr = case_ds["HARVEST_REASON_PERHARV"]
    cft_planted_area = (
        case_ds["pfts1d_gridcellarea"] * case_ds["pfts1d_wtgcell"]
    ).where(
        case_ds["pfts1d_wtgcell"] > 0,
    ) * 1e6  # convert km2 to m2
    cft_planted_area.attrs["units"] = "m2"
    case_ds["cft_harv_area"] = (cft_planted_area * (hr > 0)).sum(dim="mxharvests")
    case_ds["cft_harv_area_immature"] = (cft_planted_area * (hr > 1)).sum(
        dim="mxharvests",
    )
    case_ds["cft_harv_area_failed"] = (
        cft_planted_area * (1 - case_ds["VALID_HARVEST"]).where(hr > 0)
    ).sum(dim="mxharvests")
    case_ds["crop_harv_area"] = (
        case_ds["cft_harv_area"]
        .groupby(case_ds["cft_crop"])
        .sum(dim="cft")
        .rename({"cft_crop": "crop"})
    )
    case_ds["crop_harv_area_immature"] = (
        case_ds["cft_harv_area_immature"]
        .groupby(case_ds["cft_crop"])
        .sum(dim="cft")
        .rename({"cft_crop": "crop"})
    )
    case_ds["crop_harv_area_failed"] = (
        case_ds["cft_harv_area_failed"]
        .groupby(case_ds["cft_crop"])
        .sum(dim="cft")
        .rename({"cft_crop": "crop"})
    )

    return case


def _one_crop(
    opts,
    case,
    case_ds,
    cft_crop_array,
    i,
    crop,
    crop_cft_area_da,
    crop_cft_prod_da,
):
    """
    Process things for one crop
    """
    pft_nums = case.crop_list[crop].pft_nums
    cft_ds = case_ds.sel(cft=pft_nums)

    # Save name of this crop for cft_crop variable
    for pft_num in pft_nums:
        cft_crop_array[np.where(case_ds["cft"].values == pft_num)] = crop

    # Get area
    cft_area = cft_ds["pfts1d_gridcellarea"] * cft_ds["pfts1d_wtgcell"]
    cft_area *= 1e6  # Convert km2 to m2
    cft_area.attrs["units"] = "m2"

    # Get production
    cft_prod = cft_ds["YIELD_ANN"] * cft_area
    cft_prod.attrs["units"] = "g"

    # Setup crop_cft_* variables or append to them
    cft_area_expanded = cft_area.expand_dims(dim="crop", axis=0)
    cft_prod_expanded = cft_prod.expand_dims(dim="crop", axis=0)
    if i == 0:
        # Add crop (names) variable/dimension to case_ds, if needed
        if "crop" not in case_ds:
            crop_da = xr.DataArray(
                data=opts["crops_to_include"],
                dims=["crop"],
            )
            case_ds["crop"] = crop_da
        # Define crop_cft_* variables
        crop_cft_area_da = xr.DataArray(
            data=cft_area_expanded,
        )
        crop_cft_prod_da = xr.DataArray(
            data=cft_prod_expanded,
        )
    else:
        # Append this crop's DataArrays to existing ones
        crop_cft_area_da = xr.concat(
            [crop_cft_area_da, cft_area_expanded],
            dim="crop",
        )
        crop_cft_prod_da = xr.concat(
            [crop_cft_prod_da, cft_prod_expanded],
            dim="crop",
        )

    return crop_cft_area_da, crop_cft_prod_da
