"""
clm_and_earthstat_maps() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

import os
import sys
from types import ModuleType

from bokeh_html_utils import sanitize_filename
from caselist import CaseList
from earthstat import EarthStat
from plotting_utils import get_difference_map
from plotting_utils import ResultsMaps

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)
from ctsm_postprocessing.timing import Timing  # noqa: E402


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
    area_clm = _get_clm_map(which, utils, crop, case)
    area_obs = earthstat_ds.get_map(
        which,
        crop,
    )
    area_obs = utils.lon_pm2idl(area_obs)

    mask = (area_clm > 0) | (area_obs > 0)

    return map_clm.where(mask), map_obs.where(mask)


def _get_figpath_with_keycase(fig_path, key_case, key_case_dict):
    if len(key_case_dict) == 1:
        return fig_path
    dirname = os.path.dirname(fig_path)
    basename = os.path.basename(fig_path)
    root, ext = os.path.splitext(basename)
    root += "_" + key_case
    root = sanitize_filename(root)
    basename = root + ext
    fig_path = os.path.join(dirname, basename)
    return fig_path


def clm_and_earthstat_maps_1crop(
    *,
    which,
    case_list,
    case_legend_list,
    earthstat_data,
    utils,
    verbose,
    timer,
    crop,
    fig_path_clm,
    fig_path_diff_earthstat,
    key_case_dict,
):
    """
    For a crop, make two figures:
    1. With subplots showing mean CLM map for each case
    2. With subplots showing difference between mean CLM and EarthStat maps for each case
    """
    timer.start()
    if verbose:
        print(crop)

    # Set up for maps of CLM
    results_clm = ResultsMaps()

    # Set up for maps of CLM minus EarthStat
    results_diff = ResultsMaps(symmetric_0=True)

    # Get maps and colorbar min/max (the latter should cover total range across ALL cases)
    suptitle_clm = None
    suptitle_diff = None
    for c, case in enumerate(case_list):
        case_legend = case_legend_list[c]
        # Get CLM map
        results_clm[case_legend] = _get_clm_map(which, utils, crop, case)
        if which == "area":
            results_clm[case_legend] = results_clm[case_legend].where(
                results_clm[case_legend] > 0,
            )

        # Get observed map
        earthstat_ds = earthstat_data[case.cft_ds.attrs["resolution"]]
        map_obs = earthstat_ds.get_map(
            which,
            crop,
        )
        if map_obs is None:
            continue
        map_obs = utils.lon_pm2idl(map_obs)

        # Mask where neither CLM nor EarthStat have area (HarvestArea)
        # 1. Fill all missing values with 0
        results_clm[case_legend] = results_clm[case_legend].fillna(0)
        map_obs = map_obs.fillna(0)
        # 2. Mask
        results_clm[case_legend], map_obs = _mask_where_neither_has_area(
            utils=utils,
            crop=crop,
            case=case,
            earthstat_ds=earthstat_ds,
            map_clm=results_clm[case_legend],
            map_obs=map_obs,
        )

        # Get difference map
        results_diff[case_legend] = get_difference_map(
            map_obs,
            results_clm[case_legend],
        )
        results_diff[
            case_legend
        ].name = f"{results_clm[case_legend].name} difference, CLM minus EarthStat"
        results_diff[case_legend].attrs["units"] = results_clm[case_legend].units

        # Get plot suptitles
        if suptitle_clm is None:
            suptitle_clm = f"{results_clm[case_legend].name}: {crop}"
        if suptitle_diff is None:
            suptitle_diff = f"{results_diff[case_legend].name}: {crop}"

    for key_case, key_case_input in key_case_dict.items():

        fig_path_clm_key = _get_figpath_with_keycase(
            fig_path_clm,
            key_case,
            key_case_dict,
        )
        fig_path_diff_earthstat_key = _get_figpath_with_keycase(
            fig_path_diff_earthstat,
            key_case,
            key_case_dict,
        )

        # Plot
        one_colorbar = key_case_input is None
        results_clm.plot(
            subplot_title_list=case_legend_list,
            suptitle=suptitle_clm,
            one_colorbar=one_colorbar,
            fig_path=fig_path_clm_key,
            key_plot=key_case_input,
        )
        results_diff.plot(
            subplot_title_list=case_legend_list,
            suptitle=suptitle_diff,
            one_colorbar=one_colorbar,
            fig_path=fig_path_diff_earthstat_key,
            key_plot=key_case_input,
        )

    timer.end(crop, verbose)


def clm_and_earthstat_maps(
    *,
    which: str,
    case_list: CaseList,
    earthstat_data: EarthStat,
    utils: ModuleType,
    opts: dict,
    fig_path_clm: str = None,
    fig_path_diff_earthstat: str = None,
    key_case_dict: dict = None,
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
        clm_and_earthstat_maps_1crop(
            which=which,
            case_list=case_list,
            case_legend_list=opts["case_legend_list"],
            earthstat_data=earthstat_data,
            utils=utils,
            verbose=verbose,
            timer=timer,
            crop=crop,
            fig_path_clm=fig_path_clm,
            fig_path_diff_earthstat=fig_path_diff_earthstat,
            key_case_dict=key_case_dict,
        )

    timer.end_all("Maps", verbose)
