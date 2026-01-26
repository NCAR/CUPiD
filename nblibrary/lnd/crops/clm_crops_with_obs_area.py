"""
Module for producing certain CLM crop variables as if it had been planted with observed crop area.
Note that this isn't perfect: If CLM didn't have area in a gridcell that the observed does, there
will of course not be CLM production there.
"""

from __future__ import annotations

import xarray as xr

from externals.ctsm_postprocessing.crops.cropcase import CropCase
from externals.ctsm_postprocessing.crops.crop_case_list import CropCaseList
from externals.ctsm_postprocessing.crops.extra_area_prod_yield_etc import (
    MATURITY_LEVELS,
)
from externals.ctsm_postprocessing.utils import ungrid

from .earthstat import check_dim_alignment
from .earthstat import EarthStat
from .plotting_utils import handle_exception


def process_case(
    cft_ds: xr.Dataset,
    earthstat_data: EarthStat,
    opts: dict,
    case_name: str,
) -> xr.Dataset:
    """
    For a case's cft_ds, get versions of CLM stats as if planted with EarthStat area.

    This function processes a case dataset to calculate production and other statistics using
    observed EarthStat crop areas instead of CLM's simulated areas.

    Parameters
    ----------
    cft_ds : xarray.Dataset
        Dataset containing CFT-level crop data.
    earthstat_data : EarthStat
        EarthStat object containing observed crop area data.
    opts : dict
        Options dictionary containing configuration settings, including 'debug' and 'imm_unm_list'.
    case_name : str
        Name of the case being processed (used for error messages).

    Returns
    -------
    xarray.Dataset
        Dataset with added EarthStat-based area, production, and immature/unmarketable variables.
        Returns original dataset if any processing step fails.
    """

    # Get EarthStat area
    try:
        cft_ds = _get_earthstat_area(cft_ds, earthstat_data, opts)
    except Exception as e:  # pylint: disable=broad-exception-caught
        skip_msg = f"Couldn't get EarthStat areas for case {case_name} due to"
        handle_exception(opts["debug"], e, skip_msg)
        return cft_ds

    # Calculate production as if planted with EarthStat area
    try:
        cft_ds = _get_prod_as_if_earthstat(cft_ds)
    except Exception as e:  # pylint: disable=broad-exception-caught
        skip_msg = f"Couldn't get EarthStat production for case {case_name} due to"
        handle_exception(opts["debug"], e, skip_msg)

    # Get unmarketable/immature as if using EarthStat areas
    try:
        cft_ds = _get_immunm_as_if_earthstat(cft_ds, opts)
    except Exception as e:  # pylint: disable=broad-exception-caught
        skip_msg = f"Couldn't get unmarketable/immature as if EarthStat for case {case_name} due to"
        handle_exception(opts["debug"], e, skip_msg)

    return cft_ds


def _get_immunm_as_if_earthstat(cft_ds: xr.Dataset, opts: dict) -> xr.Dataset:
    """
    Get unmarketable/immature harvest areas as if using EarthStat areas.

    Calculates the fraction of CLM harvest area that is immature or unmarketable, then applies
    those fractions to EarthStat areas.

    Parameters
    ----------
    cft_ds : xarray.Dataset
        Dataset containing crop_area_es, crop_harv_area, and crop_harv_area_{imm_or_unm}
        variables.
    opts : dict
        Options dictionary containing 'imm_unm_list' (list of strings like 'immature',
        'unmarketable').

    Returns
    -------
    xarray.Dataset
        Dataset with added crop_area_es_{imm_or_unm} variables for each item in imm_unm_list.
    """

    crop_area_var = "crop_area_es"
    if "gridcell" in cft_ds[crop_area_var].dims:
        crop_area_es = (
            cft_ds[crop_area_var].rename({"gridcell": "pft"}).set_index(pft="pft")
        )
    else:
        crop_area_es = cft_ds[crop_area_var]
    for imm_or_unm in opts["imm_unm_list"]:
        frac_ds = cft_ds[f"crop_harv_area_{imm_or_unm}"] / cft_ds["crop_harv_area"]
        cft_ds[f"crop_area_es_{imm_or_unm}"] = frac_ds * crop_area_es
    return cft_ds


def _get_prod_as_if_earthstat(cft_ds: xr.Dataset) -> xr.Dataset:
    """
    Calculate production as if planted with EarthStat area.

    Multiplies CLM crop yields by EarthStat areas to get production values for each maturity
    level.

    Parameters
    ----------
    cft_ds : xarray.Dataset
        Dataset containing crop_area_es, crop_yield_{maturity} variables for each maturity level
        in MATURITY_LEVELS.

    Returns
    -------
    xarray.Dataset
        Dataset with added crop_prod_{maturity}_es variables for each maturity level.

    Raises
    ------
    NotImplementedError
        If area units are not 'm2' or yield units are not 'g/m2'.
    """

    area_units = cft_ds["crop_area_es"].attrs["units"]
    area_units_exp = "m2"
    for m in MATURITY_LEVELS:
        m = m.lower()
        crop_yield_var = f"crop_yield_{m}"
        yield_units = cft_ds[crop_yield_var].attrs["units"]
        yield_units_exp = "g/m2"
        if area_units != area_units_exp or yield_units != yield_units_exp:
            raise NotImplementedError(
                (
                    f"Yield calculation assumes area in {area_units_exp}"
                    f" (got {area_units}) and yield in {yield_units_exp} (got {yield_units})"
                ),
            )
        crop_prod_es_var = f"crop_prod_{m}_es"
        cft_ds[crop_prod_es_var] = cft_ds["crop_area_es"] * cft_ds[
            crop_yield_var
        ].rename({"pft": "gridcell"})
        cft_ds[crop_prod_es_var].attrs["units"] = "g"
    return cft_ds


def _get_earthstat_area(
    cft_ds: xr.Dataset,
    earthstat_data: EarthStat,
    opts: dict,
) -> xr.Dataset:
    """
    Get EarthStat crop areas and add them to the dataset.

    Retrieves observed crop areas from EarthStat, converts units to match CLM, and adds them
    to the dataset. Also saves the EarthStat time axis for reference.

    Parameters
    ----------
    cft_ds : xarray.Dataset
        Dataset containing crop dimension and crop_area variable.
    earthstat_data : EarthStat
        EarthStat object containing observed crop area data.
    opts : dict
        Options dictionary (currently unused but kept for API consistency).

    Returns
    -------
    xarray.Dataset
        Dataset with added crop_area_es and earthstat_time variables.

    Raises
    ------
    NotImplementedError
        If CLM area units are not 'm2' or EarthStat area units are not 'Mha'.
    """

    for i, crop in enumerate(cft_ds["crop"].values):
        # Get EarthStat area
        crop_area_es = ungrid(
            gridded_data=earthstat_data.get_data(
                cft_ds.attrs["resolution"],
                "area",
                crop,
                "Mha",
            ),
            ungridded_ds=cft_ds,
        )

        # Setup crop_*crop_area_es_expanded variable or append to it
        if i == 0:
            crop_area_es_expanded = crop_area_es.expand_dims(dim="crop", axis=0)
        else:
            # Append this crop's DataArray to existing one
            crop_area_es_expanded = xr.concat(
                [crop_area_es_expanded, crop_area_es],
                dim="crop",
            )

    # Convert area units
    clm_units = cft_ds["crop_area"].attrs["units"]
    es_units = crop_area_es.attrs["units"]
    if clm_units == "m2" and es_units == "Mha":
        crop_area_es_expanded = crop_area_es_expanded * 1e4 * 1e6
        crop_area_es_expanded.attrs["units"] = "m2"
    else:
        raise NotImplementedError(
            (
                f"Conversion assumes CLM area in m2 (got {clm_units})"
                f" and EarthStat area in Mha (got {es_units})"
            ),
        )

    # Before saving, check alignment of all dims
    crop_area_es_expanded = check_dim_alignment(crop_area_es_expanded, cft_ds)

    # Save EarthStat time axis to avoid plotting years with no EarthStat data
    earthstat_time = crop_area_es_expanded["time"]
    earthstat_time = earthstat_time.rename({"time": "earthstat_time_coord"})
    cft_ds["earthstat_time"] = earthstat_time

    # Save to cft_ds, filling with NaN as necessary (e.g., if there are CLM years not in
    # EarthStat).
    cft_ds["crop_area_es"] = crop_area_es_expanded

    return cft_ds


def process_caselist(
    case_list: CropCaseList,
    earthstat_data: EarthStat,
    opts: dict,
) -> CropCaseList:
    """
    For each case in case list, get versions of CLM stats as if planted with EarthStat area.

    Processes all cases in a CropCaseList to calculate production and other statistics using
    observed EarthStat crop areas.

    Parameters
    ----------
    case_list : CropCaseList
        List of CropCase objects to process.
    earthstat_data : EarthStat
        EarthStat object containing observed crop area data.
    opts : dict
        Options dictionary containing configuration settings.

    Returns
    -------
    CropCaseList
        The same CropCaseList with updated cft_ds attributes containing EarthStat-based variables.
    """
    case: CropCase

    for case in case_list:
        case.cft_ds = process_case(case.cft_ds, earthstat_data, opts, case.name)

    return case_list
