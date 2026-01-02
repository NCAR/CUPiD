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

# Needed only for the temporary kludge that is _fill_missing_gc2f_units
GC2F = "GRAINC_TO_FOOD"
GC2F_UNITS_SOURCE_VAR = "GRAINC_TO_FOOD_PERHARV"


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


def _fill_missing_gc2f_units(case, var_list, e):
    """
    It's okay for units to be missing from GRAINC_TO_FOOD variables, as long as there's a _PERHARV
    version we can take the units from.

    TODO: Delete before merging CUPiD notebook? This was a temporary hack necessary before CropCase
    import was fixed to add units.
    """
    any_gc2f = any(GC2F in v for v in var_list)
    if (
        any_gc2f
        and GC2F_UNITS_SOURCE_VAR in case.cft_ds
        and "units" in case.cft_ds[GC2F_UNITS_SOURCE_VAR].attrs
    ):
        units = case.cft_ds[GC2F_UNITS_SOURCE_VAR].attrs["units"]
        print(f"{e}; assuming {units} based on {GC2F_UNITS_SOURCE_VAR}")
        for v in var_list:
            if GC2F in v:
                case.cft_ds[v].attrs["units"] = units
                case.cft_ds[v].attrs["units_source"] = GC2F_UNITS_SOURCE_VAR
        assert all("units" in case.cft_ds[v].attrs for v in var_list), e
    else:
        raise e
    return case


def _get_das_to_combine(case, var_list):
    # Every variable should have a unit attribute
    msg = f"{case.name}: Not every variable in list has units: {var_list}"
    try:
        assert all("units" in case.cft_ds[v].attrs for v in var_list), msg
    except AssertionError as e:
        case = _fill_missing_gc2f_units(case, var_list, e)

    # Units should be the same for all variables
    unit_set = {case.cft_ds[v].attrs["units"] for v in var_list}
    msg = f"Multiple units ({unit_set}) found in these variables: {var_list}"
    assert len(unit_set) == 1, msg
    units = case.cft_ds[var_list[0]].attrs["units"]

    # Collect DataArrays to combine
    da = case.cft_ds[var_list].to_array()

    # Mask negative values, which indicates either (a) no harvest occurred or (b) harvest occurred
    # before that phase transition
    da = da.where(da >= 0)

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

            # Mask where there was no harvest
            da = da.where(case.cft_ds["HARVEST_REASON_PERHARV"] > 0)

            # Sum them
            da = da.sum(dim="variable", keep_attrs=True)
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
    valid_harvest_var = "USABLE_HARVEST"
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
    # Get grain product variables
    maturity_level = "USABLE"
    product_list = ["FOOD", "SEED"]
    missing_products = []
    var_list = []
    missing_vars = []
    for product in product_list:
        var = f"GRAINC_TO_{product}_{maturity_level}_PERHARV"
        if var in case.cft_ds:
            var_list.append(var)
        else:
            missing_products.append(product)
            missing_vars.append(var)

    # If no grain products present, return.
    if len(missing_products) == len(product_list):
        print(f"{case.name}: No grain C product variables found: {missing_vars}")
        return case
    # If only some grain products are present, warn about missing ones
    if missing_products:
        present_products = [p for p in product_list if p not in missing_products]
        print(
            f"{case.name}: Missing grain C outputs for {missing_products}; including only {present_products}",
        )

    # Get variables to sum and their units
    units, da = _get_das_to_combine(case, var_list)

    # Mask not-mature-enough harvests
    mask_var = f"{maturity_level}_HARVEST"
    da = da.where(mask_var)

    # Get grain C at maturity for each CFT
    assert not np.any(da < 0), f"Unexpected negative value(s) in variables {var_list}"
    var = "grainc_at_maturity"
    case.cft_ds[var] = da.mean(dim="mxharvests", keep_attrs=True).sum(
        dim="variable",
        keep_attrs=True,
    )

    # Combine CFTs to crops
    var_crop = var + "_crop"
    case.cft_ds = combine_cft_to_crop(
        case.cft_ds,
        var,
        var_crop,
        method="mean",
        weights="cft_harv_area",
    )
    case.cft_ds[var_crop].attrs["units"] = units
    return case


def _get_case_crop_biomass_vars(case: CropCase) -> CropCase:
    case = _get_case_max_lai(case)
    case = _get_case_abovebelowground_biomass(case)
    case = _get_case_grainc_at_maturity(case)

    return case


def get_caselist_crop_biomass_vars(case_list: CropCaseList) -> CropCaseList:
    """
    Loop through cases in CaseList, getting crop biomass variables for each
    """
    for case in case_list:
        case = _get_case_crop_biomass_vars(case)

    return case_list
