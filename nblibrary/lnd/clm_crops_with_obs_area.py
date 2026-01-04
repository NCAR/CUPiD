"""
Module for producing certain CLM crop variables as it had been planted with observed crop area.
Note that this isn't perfect: If CLM didn't have area in a gridcell that the observed does, there
will of course not be CLM production there.
"""
# noqa: E402
from __future__ import annotations

import os
import sys

import earthstat
import xarray as xr

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)

# pylint: disable=wrong-import-position,import-error
# fmt: off
from ctsm_postprocessing.crops.cropcase import CropCase  # noqa: E402
from ctsm_postprocessing.crops.crop_case_list import CropCaseList  # noqa: E402
from ctsm_postprocessing.crops.extra_area_prod_yield_etc import MATURITY_LEVELS  # noqa: E402
from ctsm_postprocessing.utils import ungrid  # noqa: E402
# fmt: on


def process_case(
    cft_ds: xr.Dataset,
    earthstat_data: earthstat.EarthStat,
    opts: dict,
) -> xr.Dataset:
    """For a case's cft_ds, get versions of CLM stats as if planted with EarthStat area"""

    for i, crop in enumerate(opts["crops_to_include"]):
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
        crop_area_es_expanded *= 1e4 * 1e6
        crop_area_es_expanded.attrs["units"] = "m2"
    else:
        raise NotImplementedError(
            (
                f"Conversion assumes CLM area in m2 (got {clm_units})"
                f" and EarthStat area in Mha (got {es_units})"
            ),
        )

    # Before saving, check alignment of all dims
    crop_area_es_expanded = earthstat.check_dim_alignment(crop_area_es_expanded, cft_ds)

    # Save to cft_ds, filling with NaN as necessary (e.g., if there are CLM years not in
    # EarthStat).
    cft_ds["crop_area_es"] = crop_area_es_expanded

    # Calculate production as if planted with EarthStat area
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

    # Save EarthStat time axis to avoid plotting years with no EarthStat data
    earthstat_time = crop_area_es_expanded["time"]
    earthstat_time = earthstat_time.rename({"time": "earthstat_time_coord"})
    cft_ds["earthstat_time"] = earthstat_time

    # Get failed/immature as if using EarthStat areas
    crop_area_var = "crop_area_es"
    if "gridcell" in cft_ds[crop_area_var].dims:
        crop_area_es = (
            cft_ds[crop_area_var].rename({"gridcell": "pft"}).set_index(pft="pft")
        )
    else:
        crop_area_es = cft_ds[crop_area_var]
    for imm_or_fail in opts["imm_fail_list"]:
        frac_ds = cft_ds[f"crop_harv_area_{imm_or_fail}"] / cft_ds["crop_harv_area"]
        cft_ds[f"crop_area_es_{imm_or_fail}"] = frac_ds * crop_area_es

    return cft_ds


def process_caselist(
    case_list: CropCaseList,
    earthstat_data: earthstat.EarthStat,
    opts: dict,
) -> CropCaseList:
    """For each case in case list, get versions of CLM stats as if planted with EarthStat area"""
    case: CropCase

    for case in case_list:
        case.cft_ds = process_case(case.cft_ds, earthstat_data, opts)

    return case_list
