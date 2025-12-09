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

# Crop phase transitions
PHASE_TRANSITIONS = ["EMERGENCE", "ANTHESIS", "MATURITY"]

# The sum of these should be total plant biomass
BIOMASS_COMPARTMENTS = ["FROOT", "LEAF", "LIVECROOT", "LIVESTEM", "REPR"]
ABOVEGROUND_COMPARTMENTS = [c for c in BIOMASS_COMPARTMENTS if "ROOT" not in c]
BELOWGROUND_COMPARTMENTS = [
    c for c in BIOMASS_COMPARTMENTS if c not in ABOVEGROUND_COMPARTMENTS
]


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


def _get_das_to_combine(case, var_list):
    # Get units
    # Every variable should have a unit attribute
    msg = f"Not every variable in list has units: {var_list}"
    assert all("units" in case.cft_ds[v].attrs for v in var_list), msg
    # Should be the same for all variables
    unit_set = {case.cft_ds[v].attrs["units"] for v in var_list}
    msg = f"Multiple units ({unit_set}) found in these variables: {var_list}"
    assert len(unit_set) == 1, msg
    units = case.cft_ds[var_list[0]].attrs["units"]

    # Collect DataArrays to sum, masking invalid values
    da = case.cft_ds[var_list].to_array()

    # Mask negative values, which indicates either (a) no harvest occurred or (b) harvest occurred
    # before that phase transition
    da = da.where(da < 0)

    return units, da


def _get_case_abovebelowground_biomass(case: CropCase) -> CropCase:
    for a_or_b in ["above", "below"]:

        # Get compartments to sum
        if a_or_b == "above":
            compartment_list = ABOVEGROUND_COMPARTMENTS
        elif a_or_b == "below":
            compartment_list = BELOWGROUND_COMPARTMENTS

        # Setup for nonsense check
        var_list_list = []

        for phase_transition in PHASE_TRANSITIONS:
            # Get variables to sum
            var_list = [
                f"{c}C_AT_{phase_transition.upper()}_PERHARV" for c in compartment_list
            ]
            if not all(v in case.cft_ds for v in var_list):
                continue
            var_list_list.append(var_list)

            # Get variables to sum and their units
            units, da = _get_das_to_combine(case, var_list)

            # Sum them
            da = da.sum("variable")
            var = f"{a_or_b}groundc_at_{phase_transition.lower()}"
            case.cft_ds[var] = da.mean(dim="mxharvests", keep_attrs=True)
            case.cft_ds[var].attrs["units"] = units

            # Combine CFTs to crops
            var_crop = var + "_crop"
            case.cft_ds = combine_cft_to_crop(
                case.cft_ds,
                var,
                var_crop,
                method="mean",
                weights="cft_harv_area",
            )
            case.cft_ds[var_crop].attrs["units"] = case.cft_ds[var].attrs["units"]

        # Nonsense check: Expected (relative) number of negatives at each phase
        _check_nonsense_neg_at_valid_harv(case, var_list_list)

    return case


def _check_nonsense_neg_at_valid_harv(case, var_list_list):
    """
    Nonsense check: The biomass pool outputs should be negative when a valid harvest doesn't
    occur (i.e., we're harvesting, and not a "fake harvest" or when the crop doesn't make it
    to the given phase transition.
    1. Because these values are only ever written at the time of valid harvest, the AT_HARVEST
        values should never be negative when a valid harvest occurs.
    2. Because anthesis can't occur before emergence, the number of negative AT_ANTHESIS
        values should always be ≥ the number of negative AT_EMERGENCE values.
    Only do this check if the phase transition list is what we expect, the case had all the
    biomass pool variables, and the case has our "valid harvest" variable.
    """
    valid_harvest_var = "VALID_HARVEST"
    do_check = (
        set(PHASE_TRANSITIONS) == {"EMERGENCE", "ANTHESIS", "MATURITY"}
        and len(var_list_list) == len(PHASE_TRANSITIONS)
        and valid_harvest_var in case.cft_ds
    )
    if not do_check:
        return
    err_msg_list = []

    # Get DataArray for each phase transition showing where negative
    da_neg_emergence = _get_negative_at_valid_harvest(
        "EMERGENCE",
        var_list_list,
        case.cft_ds,
        valid_harvest_var,
    )
    da_neg_anthesis = _get_negative_at_valid_harvest(
        "ANTHESIS",
        var_list_list,
        case.cft_ds,
        valid_harvest_var,
    )
    da_neg_maturity = _get_negative_at_valid_harvest(
        "MATURITY",
        var_list_list,
        case.cft_ds,
        valid_harvest_var,
    )

    # 1. There should never be any negative values at maturity
    n_neg_at_maturity = np.sum(da_neg_maturity)
    if n_neg_at_maturity:
        err_msg_list.append(f"{n_neg_at_maturity} cells had negatives at maturity")

    # 2. There should never be a valid value at anthesis but not emergence
    n_neg_emerg_not_anth = np.sum(da_neg_emergence & ~da_neg_anthesis)
    if n_neg_emerg_not_anth:
        err_msg_list.append(
            f"{n_neg_emerg_not_anth} cells had negatives at emergence but not anthesis",
        )

    # Throw error with all messages if either test failed
    if err_msg_list:
        err_msg = "; ".join(err_msg_list)
        raise AssertionError(err_msg)


def _get_negative_at_valid_harvest(
    phase_transition,
    var_list_list,
    cft_ds,
    valid_harvest_var,
):
    var_list = var_list_list[PHASE_TRANSITIONS.index(phase_transition)]
    da = cft_ds[var_list].to_array()

    # _get_case_abovebelowground_biomass() sets all negative values to NaN. So if we replace all
    # NaNs with negative values, we can then re-NaN valid harvests and count the resulting NaNs.
    da_filled = da.fillna(-1)
    valid_harvests = cft_ds[valid_harvest_var]
    negative_at_valid_harvest = np.isnan(da_filled.where(1 - valid_harvests) < 0)

    return negative_at_valid_harvest


def _get_case_grainc_at_maturity(case: CropCase) -> CropCase:
    # TODO: Will need to add GRAINC_TO_SEED_VIABLE_PERHARV
    product_list = ["FOOD", "SEED"]
    var_list = [f"GRAINC_TO_{p}_VIABLE_PERHARV" for p in product_list]

    if not all(v in case.cft_ds for v in var_list):
        return case

    # Get variables to sum and their units
    units, da = _get_das_to_combine(case, var_list)

    # Get grain C at maturity.
    assert np.any(da < 0), f"Unexpected negative value(s) in variables {var_list}"
    case.cft_ds[var] = da.mean(dim="mxharvests", keep_attrs=True)

    # Combine CFTs to crops
    var_crop = var + "_crop"
    case.cft_ds = combine_cft_to_crop(
        case.cft_ds,
        var,
        var_crop,
        method="mean",
        weights="cft_harv_area",
    )
    case.cft_ds[var_crop].attrs["units"] = case.cft_ds[var_in].attrs["units"]
    assert np.any(case.cft_ds[var_crop] > 0)
    return case


def _get_case_crop_biomass_vars(case: CropCase) -> CropCase:
    case = _get_case_max_lai(case)
    case = _get_case_abovebelowground_biomass(case)
    # case = _get_case_grainc_at_maturity(case)

    return case


def get_caselist_crop_biomass_vars(case_list: CropCaseList) -> CropCaseList:
    """
    Loop through cases in CaseList, getting crop biomass variables for each
    """
    for case in case_list:
        case = _get_case_crop_biomass_vars(case)

    return case_list
