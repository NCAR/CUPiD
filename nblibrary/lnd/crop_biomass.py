"""
Module with functions for calculating crop biomass, ratios, etc.
"""
from __future__ import annotations

import os
import sys

import numpy as np

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)
# pylint: disable=wrong-import-position,import-error

# noqa: E402
from ctsm_postprocessing.crops.cropcase import CropCase  # noqa: E402
from ctsm_postprocessing.crops.crop_case_list import CropCaseList  # noqa: E402
from ctsm_postprocessing.crops.combine_cft_to_crop import (  # noqa: E402
    combine_cft_to_crop,
)


def _get_case_max_lai(case: CropCase) -> CropCase:
    if "MAX_TLAI_PERHARV" not in case.cft_ds:
        return case

    # List of variables to keep: Just what we need
    variables_to_keep = [
        "MAX_TLAI_PERHARV",
        "cft_crop",
        "pfts1d_ixy",
        "pfts1d_jxy",
        "cft_harv_area",
    ]

    # Get all data variables in the Dataset
    all_data_vars = list(case.cft_ds.data_vars.keys())

    # Drop everything except what's needed for gridding our result
    variables_to_drop = [var for var in all_data_vars if var not in variables_to_keep]
    cft_ds = case.cft_ds.drop_vars(variables_to_drop)
    cft_ds = cft_ds.drop_vars("crop")

    da = cft_ds["MAX_TLAI_PERHARV"].copy()
    da = da.where(da >= 0)
    da = da.mean(dim="mxharvests")
    assert not np.any(da < 0)

    # Combine CFTs to crops
    var = "max_tlai"
    var_crop = var + "_crop"
    cft_ds[var] = da
    cft_ds = combine_cft_to_crop(
        cft_ds,
        var,
        var_crop,
        method="mean",
        weights="cft_harv_area",
    )

    # This should be changed to happen automatically elsewhere!
    cft_ds[var_crop].attrs["units"] = "m2/m2"

    case.cft_ds[var_crop] = cft_ds[var_crop]

    return case


def _get_case_crop_biomass_vars(case: CropCase) -> CropCase:
    case = _get_case_max_lai(case)

    return case


def get_caselist_crop_biomass_vars(case_list: CropCaseList) -> CropCaseList:
    """
    Loop through cases in CaseList, getting crop biomass variables for each
    """
    for case in case_list:
        case = _get_case_crop_biomass_vars(case)

    return case_list
