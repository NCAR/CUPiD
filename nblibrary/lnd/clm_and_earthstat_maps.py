"""
clm_and_earthstat_maps() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

import os
import sys
from types import ModuleType

from bokeh_html_utils import sanitize_filename
from earthstat import EarthStat
from plotting_utils import get_difference_map
from results_maps import ResultsMaps

# from plotting_utils import get_key_case

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)
# pylint: disable=import-error
from ctsm_postprocessing.timing import Timing  # noqa: E402
from ctsm_postprocessing.crops.crop_case_list import CropCaseList  # noqa: E402


def _get_clm_map(cft_ds, stat_input, utils):
    """
    Get yield map from CLM
    """

    # Define some things based on what map we want
    if stat_input == "yield":
        units = "tons / ha"
        conversion_factor = 1e-6 * 1e4  # Convert g/m2 to t/ha
        name = "Yield"
    elif stat_input == "prod":
        units = "Mt"
        conversion_factor = 1e-6 * 1e-6  # Convert g to Mt
        name = "Production"
    elif stat_input == "area":
        units = "Mha"
        conversion_factor = 1e-4 * 1e-6  # Convert m2 to Mha
        name = "Area"
    else:
        raise NotImplementedError(
            f"_get_clm_map() doesn't work for stat_input='{stat_input}'",
        )

    # Extract the data
    ds = cft_ds.mean(dim="time")
    ds["result"] = ds["crop_" + stat_input]
    if stat_input == "prod":
        ds["result"] = ds["result"].where(ds["crop_area"] > 0)

    # Grid the data
    map_clm = utils.grid_one_variable(ds, "result")
    map_clm = utils.lon_pm2idl(map_clm)

    # Mask (this extra step is only needed for area)
    if stat_input == "area":
        map_clm = map_clm.where(map_clm > 0)

    # Finish up
    map_clm *= conversion_factor
    map_clm.name = name
    map_clm.attrs["units"] = units

    return map_clm


def _get_obsdiff_map(
    cft_ds,
    *,
    stat_input,
    earthstat_data,
    utils,
    crop,
    map_clm,
):
    # Get observed map
    earthstat_ds = earthstat_data[cft_ds.attrs["resolution"]]
    map_obs = earthstat_ds.get_map(
        stat_input,
        crop,
    )
    if map_obs is None:
        return map_obs
    map_obs = utils.lon_pm2idl(map_obs)

    # Mask where neither CLM nor EarthStat have area (HarvestArea)
    # 1. Fill all missing values with 0
    map_clm_for_obsdiff = map_clm.fillna(0)
    map_obs = map_obs.fillna(0)
    # 2. Mask
    map_clm_for_obsdiff, map_obs = _mask_where_neither_has_area(
        utils=utils,
        crop=crop,
        cft_ds=cft_ds,
        earthstat_ds=earthstat_ds,
        map_clm=map_clm_for_obsdiff,
        map_obs=map_obs,
    )

    # Get difference map
    map_obsdiff = get_difference_map(
        map_obs,
        map_clm_for_obsdiff,
        name=f"{map_clm_for_obsdiff.name} difference, CLM minus EarthStat",
        units=map_clm_for_obsdiff.units,
    )

    return map_obsdiff


def _mask_where_neither_has_area(
    *,
    utils,
    crop,
    cft_ds,
    earthstat_ds,
    map_clm,
    map_obs,
):
    """
    Given maps from CLM and EarthStat, mask where neither has area (HarvestArea)
    """
    stat_input = "area"
    area_clm = _get_clm_map(cft_ds, stat_input, utils)
    area_obs = earthstat_ds.get_map(
        stat_input,
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


def _get_fig_path(img_dir, crop, clm_or_obsdiff, stat):
    """
    Get filenames to which figures will be saved. Members of join_list
    must first be any dropdown menu members and then any radio button
    group members, in the orders given in dropdown_specs and radio_specs,
    respectively.
    """
    join_list = [crop, clm_or_obsdiff, stat]
    fig_basename = sanitize_filename("_".join(join_list))
    fig_basename += ".png"
    fig_path = os.path.join(img_dir, fig_basename)
    return fig_path


def clm_and_earthstat_maps_1crop(
    *,
    stat_strings,
    case_list,
    case_legend_list,
    earthstat_data,
    utils,
    verbose,
    timer,
    crop,
    key_case_dict,
    clm_or_obsdiff_list,
):
    """
    For a crop, make two figures:
    1. With subplots showing mean CLM map for each case
    2. With subplots showing difference between mean CLM and EarthStat maps for each case
    """
    timer.start()
    if verbose:
        print(crop)

    # Parse top-level options
    stat, stat_input = stat_strings
    # Where figure files will be saved
    img_dir = os.path.join("Global_crop_yield_compare_obs", "maps_yieldprodarea")
    os.makedirs(img_dir, exist_ok=True)

    # Some code below assumes that None (i.e., pure CLM results) is the first in this list
    assert clm_or_obsdiff_list[0] == "None"
    results_clm = ResultsMaps()

    for obs_input in clm_or_obsdiff_list:
        if verbose:
            print(f"    {obs_input}")

        # Parse obs_input-level options
        fig_path = _get_fig_path(img_dir, crop, obs_input, stat)
        if obs_input == "None":
            symmetric_0 = False
        else:
            symmetric_0 = True

        # Initialize things ahead of results generation
        results = ResultsMaps(symmetric_0=symmetric_0)

        # Get maps and colorbar min/max (the latter should cover total range across ALL cases)
        suptitle = None
        for key_case_key, key_case_value in key_case_dict.items():
            # Get key case, if needed
            # key_case = get_key_case(case_legend_list, key_case_value, case_list)
            for c, case in enumerate(case_list):
                case_legend = case_legend_list[c]

                if obs_input == "None":
                    map_clm = _get_clm_map(
                        case.cft_ds,
                        stat_input,
                        utils,
                    )
                    results[case_legend] = map_clm
                    # Difference map iterations need to "remember" CLM value; this is why we have
                    # the assumption above that the first member of clm_or_obsdiff_list is "None".
                    results_clm[case_legend] = map_clm
                else:
                    map_obsdiff = _get_obsdiff_map(
                        case.cft_ds,
                        stat_input=stat_input,
                        earthstat_data=earthstat_data,
                        utils=utils,
                        crop=crop,
                        map_clm=results_clm[case_legend],
                    )
                    if map_obsdiff is None:
                        continue
                    results[case_legend] = map_obsdiff

                # Get plot suptitle
                if suptitle is None:
                    suptitle = f"{results[case_legend].name}: {crop}"

            # Update figure path with keycase, if needed
            fig_path_key = _get_figpath_with_keycase(
                fig_path,
                key_case_key,
                key_case_dict,
            )

            # Plot
            if key_case_value is None:
                key_plot = None
            else:
                key_plot = key_case_value  # + "DONE"
            one_colorbar = key_case_value is None
            key_diff_abs_error = ((key_case_value is not None),)
            results.plot(
                subplot_title_list=case_legend_list,
                suptitle=suptitle,
                one_colorbar=one_colorbar,
                fig_path=fig_path_key,
                key_plot=key_plot,
                key_diff_abs_error=key_diff_abs_error,
            )

    timer.end(crop, verbose)


def clm_and_earthstat_maps(
    *,
    stat_strings: tuple,
    case_list: CropCaseList,
    earthstat_data: EarthStat,
    utils: ModuleType,
    opts: dict,
    fig_path_clm: str = None,
    fig_path_diff_earthstat: str = None,
    key_case_dict: dict = None,
    clm_or_obsdiff_list: list = None,
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
            stat_strings=stat_strings,
            case_list=case_list.sel(crop=crop),
            case_legend_list=opts["case_legend_list"],
            earthstat_data=earthstat_data,
            utils=utils,
            verbose=verbose,
            timer=timer,
            crop=crop,
            key_case_dict=key_case_dict,
            clm_or_obsdiff_list=clm_or_obsdiff_list,
        )

    timer.end_all("Maps", verbose)
