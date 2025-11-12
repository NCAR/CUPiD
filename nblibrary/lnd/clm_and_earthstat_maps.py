"""
clm_and_earthstat_maps_1crop() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

import os
import sys

from bokeh_html_utils import sanitize_filename
from plotting_utils import get_difference_map
from plotting_utils import get_key_case
from plotting_utils import get_mean_map
from results_maps import ResultsMaps

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)
# pylint: disable=wrong-import-position,import-error
from ctsm_postprocessing import (  # noqa: E402
    utils,
)


def _get_clm_map(case, stat_input):
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
    ds = case.cft_ds.mean(dim="time")
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

    # Clean up intermediate dataset
    del ds

    return map_clm


def _get_obsdiff_map(
    case,
    *,
    stat_input,
    earthstat_data,
    crop,
):
    # Get CLM map
    map_clm = _get_clm_map(case, stat_input)

    # Get observed map
    earthstat_ds = earthstat_data[case.cft_ds.attrs["resolution"]]
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
        crop=crop,
        case=case,
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

    # Clean up intermediate variables
    del map_clm_for_obsdiff
    del map_obs
    del earthstat_ds

    return map_obsdiff


def _mask_where_neither_has_area(
    *,
    crop,
    case,
    earthstat_ds,
    map_clm,
    map_obs,
):
    """
    Given maps from CLM and EarthStat, mask where neither has area (HarvestArea)
    """
    stat_input = "area"
    area_clm = _get_clm_map(case, stat_input)
    area_obs = earthstat_ds.get_map(
        stat_input,
        crop,
    )
    area_obs = utils.lon_pm2idl(area_obs)

    mask = (area_clm > 0) | (area_obs > 0)

    result = map_clm.where(mask), map_obs.where(mask)

    # Clean up intermediate variables
    del area_clm
    del area_obs
    del mask

    return result


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
    verbose,
    crop,
    key_case_dict,
    clm_or_obsdiff_list,
    img_dir,
):
    """
    For a crop, make two figures:
    1. With subplots showing mean CLM map for each case
    2. With subplots showing difference between mean CLM and EarthStat maps for each case
    """

    # Parse top-level options
    stat, stat_input = stat_strings

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
            key_case = get_key_case(case_legend_list, key_case_value, case_list)

            map_keycase_dict_io = None
            for c, case in enumerate(case_list):
                case_legend = case_legend_list[c]

                key_diff_abs_error = key_case_value is not None and obs_input != "None"
                if obs_input == "None":
                    special_mean = _get_clm_map
                    special_mean_args = [stat_input]
                    special_mean_kwargs = {}
                else:
                    special_mean = _get_obsdiff_map
                    special_mean_args = []
                    special_mean_kwargs = {
                        "stat_input": stat_input,
                        "earthstat_data": earthstat_data,
                        "crop": crop,
                    }

                (
                    _,
                    map_clm,
                    _,
                    _,
                    map_keycase_dict_io,
                ) = get_mean_map(
                    case,
                    key_case,
                    key_diff_abs_error,
                    special_mean,
                    *special_mean_args,
                    map_keycase_dict_io=map_keycase_dict_io,
                    **special_mean_kwargs,
                )

                if obs_input != "None" and map_clm is None:
                    raise RuntimeError(
                        "This was a continue condition before using get_mean_map; how to handle?",
                    )

                # Save to ResultsMaps
                results[case_legend] = map_clm

                # Clean up intermediate reference
                del map_clm

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
                key_plot = key_case_value + "DONE"
            one_colorbar = key_case_value is None
            results.plot(
                subplot_title_list=case_legend_list,
                suptitle=suptitle,
                one_colorbar=one_colorbar,
                fig_path=fig_path_key,
                key_plot=key_plot,
                key_diff_abs_error=key_diff_abs_error,
            )

        # Clean up results object after plotting
        del results

    result = f"{crop.capitalize()} {stat}"
    print(result)
    return result
