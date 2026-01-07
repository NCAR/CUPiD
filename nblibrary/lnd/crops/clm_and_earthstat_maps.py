"""
clm_and_earthstat_maps_1crop() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

import os
import sys

from .bokeh_html_utils import sanitize_filename
from .parallelizable_plot_loop import get_figpath_with_keycase
from .plotting_utils import get_difference_map
from .plotting_utils import get_instxn_time_slice_of_ds
from .plotting_utils import get_key_case
from .plotting_utils import get_maturity_level_from_stat
from .plotting_utils import get_mean_map
from .plotting_utils import handle_exception
from .results_maps import ResultsMaps

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)
# pylint: disable=wrong-import-position,import-error
from ctsm_postprocessing import (  # noqa: E402
    utils,
)

TARGET_UNITS = {
    "prod": "Mt",
    "area": "Mha",
    "yield": "tonnes/ha",
}


def _get_clm_map(case, stat_input):
    """
    Get yield map from CLM
    """

    # Handle requested maturity level
    stat_input, maturity = get_maturity_level_from_stat(stat_input)

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

    # Do we have the variable we need?
    var = f"crop_{stat_input}"
    if maturity is not None:
        var += f"_{maturity}"

    # Extract the data
    ds = case.cft_ds.mean(dim="time")
    ds["result"] = ds[var]
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
    do_debug,
):

    # Get CLM map
    map_clm = _get_clm_map(case, stat_input)

    # Get observed map
    stat_input, _ = get_maturity_level_from_stat(stat_input)
    map_obs = earthstat_data.get_map(
        case.cft_ds.attrs["resolution"],
        stat_input,
        crop,
        TARGET_UNITS[stat_input],
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
        earthstat_data=earthstat_data,
        map_clm=map_clm_for_obsdiff,
        map_obs=map_obs,
        debug=do_debug,
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

    return map_obsdiff


def _mask_where_neither_has_area(
    *,
    crop,
    case,
    earthstat_data,
    map_clm,
    map_obs,
    debug,
):
    """
    Given maps from CLM and EarthStat, mask where neither has area (HarvestArea)
    """
    stat_input = "area"

    # Mask based on observed area
    area_obs = earthstat_data.get_map(
        case.cft_ds.attrs["resolution"],
        stat_input,
        crop,
        TARGET_UNITS[stat_input],
    )
    area_obs = utils.lon_pm2idl(area_obs)
    mask = area_obs > 0

    # Mask based on CLM area, if possible
    area_clm = None
    try:
        area_clm = _get_clm_map(case, stat_input)
    except Exception as e:  # pylint: disable=broad-exception-caught
        skip_msg = f"Skipping CLM area mask for case {case.name} due to"
        handle_exception(debug, e, skip_msg)
    if area_clm is not None:
        mask = mask | (area_clm > 0)

    result = map_clm.where(mask), map_obs.where(mask)

    # Clean up intermediate variables
    del area_clm
    del area_obs
    del mask

    return result


def _get_fig_path(img_dir, crop, clm_or_obsdiff, stat, yr_range_str):
    """
    Get filenames to which figures will be saved. Members of join_list
    must first be any dropdown menu members and then any radio button
    group members, in the orders given in dropdown_specs and radio_specs,
    respectively.
    """
    join_list = [stat, crop, clm_or_obsdiff, yr_range_str]
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
    incl_yrs_plot_items,
    debug,
):
    """
    For a crop, make two figures:
    1. With subplots showing mean CLM map for each case
    2. With subplots showing difference between mean CLM and EarthStat maps for each case
    """

    # Parse top-level options
    stat, stat_input = stat_strings
    incl_yrs_range_input, yr_range_str, time_slice = incl_yrs_plot_items

    for obs_input in clm_or_obsdiff_list:

        # Parse obs_input-level options
        fig_path = _get_fig_path(img_dir, crop, obs_input, stat, yr_range_str)
        if obs_input == "None":
            symmetric_0 = False
        else:
            symmetric_0 = True

        # Initialize things ahead of results generation
        results = ResultsMaps(
            symmetric_0=symmetric_0,
            incl_yrs_range=incl_yrs_range_input,
        )

        # Get maps and colorbar min/max (the latter should cover total range across ALL cases)
        suptitle = None
        for key_case_key, key_case_value in key_case_dict.items():

            # Get key case, if needed
            key_case = get_key_case(case_legend_list, key_case_value, case_list)

            case_incl_yr_dict = {}
            map_keycase_dict_io = None
            for c, case in enumerate(case_list):
                case_legend = case_legend_list[c]

                # Get overlap of CLM and EarthStat years
                ds_to_overlap = [case.cft_ds]
                if obs_input != "None":
                    ds_to_overlap.append(
                        earthstat_data[case.cft_ds.attrs["resolution"]],
                    )
                if key_case is not None:
                    ds_to_overlap.append(key_case.cft_ds)
                time_slice_thiscase = get_instxn_time_slice_of_ds(
                    time_slice,
                    *ds_to_overlap,
                )
                earthstat_data_intsxn = None
                key_case_intsxn = None
                if time_slice_thiscase is not None:
                    case = case.sel(time=time_slice_thiscase)
                    earthstat_data_intsxn = None
                    if earthstat_data is not None:
                        earthstat_data_intsxn = earthstat_data.sel(
                            time=time_slice_thiscase,
                        )
                    if key_case is None:
                        key_case_intsxn = key_case
                    else:
                        key_case_intsxn = key_case.sel(time=time_slice_thiscase)

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
                        "earthstat_data": earthstat_data_intsxn,
                        "crop": crop,
                        "do_debug": debug,
                    }

                try:
                    (
                        n_timesteps,
                        map_clm,
                        case_first_yr,
                        case_last_yr,
                        map_keycase_dict_io,
                    ) = get_mean_map(
                        case,
                        key_case_intsxn,
                        key_diff_abs_error,
                        special_mean,
                        *special_mean_args,
                        map_keycase_dict_io=map_keycase_dict_io,
                        time_slice=time_slice_thiscase,
                        debug=debug,
                        **special_mean_kwargs,
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    skip_msg = f"Skipping {stat_input} for case {case.name} due to"
                    handle_exception(debug, e, skip_msg)
                    map_clm = None

                # Save to ResultsMaps
                results[case_legend] = map_clm

                # Clean up intermediate reference
                del map_clm

                # Get plot suptitle
                if suptitle is None:
                    _, maturity = get_maturity_level_from_stat(stat_input)
                    title_stat = results[case_legend].name
                    if maturity is not None:
                        title_stat += f" ({maturity})"
                    suptitle = f"{title_stat}: {crop} [{yr_range_str}]"

                # Save info about included years
                if n_timesteps == 0:
                    case_incl_yr_dict[case_legend] = None
                else:
                    case_incl_yr_dict[case_legend] = [case_first_yr, case_last_yr]

            # Update figure path with keycase, if needed
            fig_path_key = get_figpath_with_keycase(
                fig_path,
                key_case_key,
                key_case_dict,
            )

            # Plot
            one_colorbar = key_case_value is None
            results.plot(
                subplot_title_list=case_legend_list,
                suptitle=suptitle,
                one_colorbar=one_colorbar,
                fig_path=fig_path_key,
                key_plot=key_case_value,
                key_diff_abs_error=key_diff_abs_error,
                case_incl_yr_dict=case_incl_yr_dict,
            )

        # Clean up results object after plotting
        del results

    result = f"{crop.capitalize()} {stat} {yr_range_str}"
    print(result)
    return result
