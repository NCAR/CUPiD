"""
clm_and_earthstat_maps() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

from time import time
from types import ModuleType

from caselist import CaseList
from earthstat import EarthStat
from plotting_utils import cut_off_antarctica, ResultsMaps


class Timing:
    """
    For holding, calculating, and printing info about clm_and_earthstat_maps() timing
    """

    def __init__(self):
        self._start_all = time()
        self._start = None

    def start(self):
        """
        Start timer for one loop
        """
        self._start = time()

    def end(self, crop, verbose):
        """
        End timer for one loop
        """
        end = time()
        if verbose:
            print(f"{crop} took {end - self._start} s")

    def end_all(self, verbose):
        """
        End timer across all loops
        """
        end_all = time()
        if verbose:
            print(f"Maps took {int(end_all - self._start_all)} s.")


def _get_difference_map(da0, da1):
    """
    Get difference between two maps (da1-da0), ensuring sizes/coordinates match
    """
    if not all(da1.sizes[d] == da0.sizes[d] for d in da1.dims):
        raise RuntimeError(
            f"Size mismatch between da1 ({da1.sizes}) and da0 ({da0.sizes})",
        )
    da_diff = da1 - da0
    if not all(da1.sizes[d] == da_diff.sizes[d] for d in da1.dims):
        raise RuntimeError(
            f"Size mismatch between da1 ({da1.sizes}) and map_diff ({da_diff.sizes})",
        )
    return da_diff


def _get_clm_map(which, utils, crop, case):
    """
    Get yield map from CLM
    """

    # Define some things based on what map we want
    if which == "yield":
        units = "tons / ha"
        conversion_factor = 1e-6 * 1e4  # Convert g/m2 to t/ha
        name = "Yield"
    elif which == "prod":
        units = "Mt"
        conversion_factor = 1e-6 * 1e-6  # Convert g to Mt
        name = "Production"
    elif which == "area":
        units = "Mha"
        conversion_factor = 1e-4 * 1e-6  # Convert m2 to Mha
        name = "Area"
    else:
        raise NotImplementedError(
            f"_get_clm_map() doesn't work for which='{which}'",
        )

    # Extract the data
    ds = case.cft_ds.sel(crop=crop).mean(dim="time")
    ds["result"] = ds["crop_" + which]
    if which == "prod":
        ds["result"] = ds["result"].where(ds["crop_area"] > 0)

    # Grid the data
    map_clm = utils.grid_one_variable(ds, "result")
    map_clm = utils.lon_pm2idl(map_clm)

    # Finish up
    map_clm *= conversion_factor
    map_clm.name = name
    map_clm.attrs["units"] = units

    return map_clm


def _mask_where_neither_has_area(
    *,
    utils,
    crop,
    case,
    earthstat_ds,
    map_clm,
    map_obs,
):
    """
    Given maps from CLM and EarthStat, mask where neither has area (HarvestArea)
    """
    which = "area"
    area_clm = cut_off_antarctica(_get_clm_map(which, utils, crop, case))
    area_obs = earthstat_ds.get_map(
        which,
        crop,
    )
    area_obs = utils.lon_pm2idl(area_obs)

    mask = (area_clm > 0) | (area_obs > 0)

    return map_clm.where(mask), map_obs.where(mask)


def clm_and_earthstat_maps(
    *,
    which: str,
    case_list: CaseList,
    earthstat_data: EarthStat,
    utils: ModuleType,
    opts: dict,
):
    """
    For each crop, make two figures:
    1. With subplots showing mean CLM map for each case
    2. With subplots showing difference between mean CLM and EarthStat maps for each case
    """
    crops_to_include = opts["crops_to_include"]
    verbose = opts["verbose"]

    timer = Timing()
    for crop in crops_to_include:
        timer.start()
        if verbose:
            print(crop)

        # Set up for maps of CLM
        results_clm = ResultsMaps(case_list.mapfig_layout)

        # Set up for maps of CLM minus EarthStat
        results_diff = ResultsMaps(case_list.mapfig_layout, symmetric_0=True)

        # Get maps and colorbar min/max (the latter should cover total range across ALL cases)
        for case in case_list:

            # Get CLM map
            results_clm[case.name] = cut_off_antarctica(
                _get_clm_map(which, utils, crop, case),
            )
            if which == "area":
                results_clm[case.name] = results_clm[case.name].where(
                    results_clm[case.name] > 0,
                )

            # Get observed map
            earthstat_ds = earthstat_data[case.cft_ds.attrs["resolution"].name]
            map_obs = earthstat_ds.get_map(
                which,
                crop,
            )
            if map_obs is None:
                continue
            map_obs = utils.lon_pm2idl(map_obs)

            # Mask where neither CLM nor EarthStat have area (HarvestArea)
            # 1. Fill all missing values with 0
            results_clm[case.name] = results_clm[case.name].fillna(0)
            map_obs = map_obs.fillna(0)
            # 2. Mask
            results_clm[case.name], map_obs = _mask_where_neither_has_area(
                utils=utils,
                crop=crop,
                case=case,
                earthstat_ds=earthstat_ds,
                map_clm=results_clm[case.name],
                map_obs=map_obs,
            )

            # Get difference map
            results_diff[case.name] = _get_difference_map(
                map_obs,
                results_clm[case.name],
            )
            results_diff[
                case.name
            ].name = f"{results_clm[case.name].name} difference, CLM minus EarthStat"
            results_diff[case.name].attrs["units"] = results_clm[case.name].units

        # Plot
        results_clm.plot(case_name_list=case_list.names, crop=crop)
        results_diff.plot(case_name_list=case_list.names, crop=crop)

        timer.end(crop, verbose)

    timer.end_all(verbose)
