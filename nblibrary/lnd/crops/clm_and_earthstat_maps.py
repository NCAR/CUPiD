"""
Functions for creating CLM and EarthStat comparison maps.

This module provides functionality for generating map visualizations comparing
CLM (Community Land Model) crop output with EarthStat observational data. It
supports creating maps for yield, production, and area statistics, as well as
difference maps between model and observations.

Main Functions:
    - clm_and_earthstat_maps_1crop: Generate comparison maps for a single crop

Helper Functions:
    - _get_clm_map: Extract and process CLM crop statistics
    - _get_obsdiff_map: Calculate difference between CLM and EarthStat
    - _mask_where_neither_has_area: Apply masking based on crop area
    - _get_fig_path: Generate output file paths for figures
"""

from __future__ import annotations

import os
from typing import Any

import xarray as xr

from externals.ctsm_postprocessing import utils
from externals.ctsm_postprocessing.crops.cropcase import CropCase
from .bokeh_html_utils import sanitize_filename
from .earthstat import EarthStat
from .parallelizable_plot_loop import get_figpath_with_keycase
from .plotting_utils import get_difference_map
from .plotting_utils import get_instxn_time_slice_of_ds
from .plotting_utils import get_key_case
from .plotting_utils import get_maturity_level_from_stat
from .plotting_utils import get_mean_map
from .plotting_utils import handle_exception
from .results_maps import ResultsMaps

TARGET_UNITS = {
    "prod": "Mt",
    "area": "Mha",
    "yield": "tonnes/ha",
}


def _get_clm_map(case: CropCase, stat_input: str) -> Any:
    """Extract and process a crop statistics map from CLM output.

    This function retrieves crop yield, production, or area data from CLM model
    output, applies necessary unit conversions, and returns a gridded map ready
    for visualization or comparison.

    Parameters
    ----------
    case : CropCase
        Case object containing CLM crop functional type dataset (cft_ds).
        Must have a cft_ds attribute with crop statistics variables.
    stat_input : str
        Type of statistic to extract. Can be:
        - 'yield' or 'yield_{matlev}': Crop yield
        - 'prod' or 'prod_{matlev}': Crop production
        - 'area' or 'area_{matlev}': Harvested area
        Maturity level suffixes (_mature, etc.) are automatically parsed.

    Returns
    -------
    xr.DataArray
        Gridded map of the requested statistic with:
        - Converted units (t/ha for yield, Mt for production, Mha for area)
        - Longitude converted from 0:360 to -180:180 format so that 0° longitude
          is in the middle of the map (better for land-focused maps)
        - Appropriate masking applied (e.g., production masked where area is 0)
        - Name and units attributes set

    Raises
    ------
    NotImplementedError
        If stat_input is not one of 'yield', 'prod', or 'area' (with optional
        maturity suffix).

    Notes
    -----
    Unit conversions applied:
    - Yield: g/m² → t/ha (multiply by 1e-6 * 1e4)
    - Production: g → Mt (multiply by 1e-6 * 1e-6)
    - Area: m² → Mha (multiply by 1e-4 * 1e-6)

    Production values are masked where crop_area is 0 to avoid spurious values.
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
    case: CropCase,
    *,
    stat_input: str,
    earthstat_data: EarthStat,
    crop: str,
    do_debug: bool,
) -> Any | None:
    """Calculate difference map between CLM and EarthStat observations.

    This function computes the difference (CLM minus EarthStat) for a given
    crop statistic, applying appropriate masking to ensure fair comparison
    only where both datasets have crop area.

    Parameters
    ----------
    case : CropCase
        Case object containing CLM crop functional type dataset.
    stat_input : str
        Type of statistic to compare ('yield', 'prod', or 'area').
        Can include maturity suffix (_mature, etc.).
    earthstat_data : EarthStat
        EarthStat data object containing observational crop statistics.
        Must support get_map() method and indexing by resolution.
    crop : str
        Name of the crop to process (e.g., 'corn', 'wheat', 'soy').
    do_debug : bool
        If True, print debug information and raise exceptions.
        If False, suppress detailed error messages.

    Returns
    -------
    xr.DataArray or None
        Difference map (CLM minus EarthStat) with same units as input statistic.
        Returns None if EarthStat data is not available for this crop/resolution.
        Map is masked to show differences only where at least one dataset has
        non-zero crop area.

    Notes
    -----
    The masking strategy ensures fair comparison:
    1. Both CLM and EarthStat maps are filled with 0 for missing values
    2. A mask is created where either CLM or EarthStat has crop area > 0
    3. The difference is calculated only for masked regions

    This prevents spurious differences in regions where neither dataset
    indicates crop presence.
    """
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
    crop: str,
    case: CropCase,
    earthstat_data: EarthStat,
    map_clm: xr.DataArray,
    map_obs: xr.DataArray,
    debug: bool,
) -> tuple[xr.DataArray, xr.DataArray]:
    """Mask maps to show data only where at least one dataset has crop area.

    This function creates a combined mask based on crop area (HarvestArea) from
    both CLM and EarthStat datasets, ensuring that comparisons are only made in
    regions where at least one dataset indicates crop presence.

    Parameters
    ----------
    crop : str
        Name of the crop being processed.
    case : CropCase
        Case object containing CLM crop functional type dataset.
    earthstat_data : EarthStat
        EarthStat data object containing observational crop statistics.
    map_clm : xr.DataArray
        CLM map to be masked (any statistic: yield, production, or area).
    map_obs : xr.DataArray
        EarthStat map to be masked (same statistic as map_clm).
    debug : bool
        If True, raise exceptions when CLM area data is unavailable.
        If False, silently skip CLM area masking on error.

    Returns
    -------
    tuple of (xr.DataArray, xr.DataArray)
        Masked versions of (map_clm, map_obs) where values are preserved only
        in regions where either CLM or EarthStat has crop area > 0.

    Notes
    -----
    The masking process:
    1. Retrieves area maps from both EarthStat and CLM
    2. Creates mask where area > 0 in either dataset (logical OR)
    3. Applies mask to both input maps
    4. Handles cases where CLM area data is unavailable gracefully

    This ensures fair comparison by excluding regions where neither dataset
    indicates crop cultivation.
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


def _get_fig_path(
    img_dir: str,
    crop: str,
    clm_or_obsdiff: str,
    stat: str,
    yr_range_str: str,
) -> str:
    """Generate output file path for a figure.

    Constructs a standardized filename for saving figures based on the
    visualization parameters. The filename components are ordered to match
    the Bokeh HTML viewer's dropdown and radio button specifications.

    Parameters
    ----------
    img_dir : str
        Directory where the figure will be saved.
    crop : str
        Name of the crop (e.g., 'corn', 'wheat', 'soy').
    clm_or_obsdiff : str
        Type of map: 'None' for CLM-only maps, or other value for
        CLM-EarthStat difference maps.
    stat : str
        Statistic being plotted ('yield', 'prod', or 'area').
    yr_range_str : str
        String representation of the year range (e.g., '2000-2010').

    Returns
    -------
    str
        Full path to the output PNG file.

    Notes
    -----
    The filename components are joined in a specific order that must match
    the order of controls in the Bokeh HTML viewer:
    1. First: dropdown menu options (in order of dropdown_specs)
    2. Then: radio button options (in order of radio_specs)

    Each component is sanitized using sanitize_filename() to ensure
    valid Unix filenames.
    """
    join_list = [stat, crop, clm_or_obsdiff, yr_range_str]
    fig_basename = sanitize_filename("_".join(join_list))
    fig_basename += ".png"
    fig_path = os.path.join(img_dir, fig_basename)
    return fig_path


def clm_and_earthstat_maps_1crop(
    *,
    stat_strings: tuple[str, str],
    case_list: list[CropCase],
    case_legend_list: list[str],
    earthstat_data: EarthStat,
    crop: str,
    key_case_dict: dict[str, str],
    clm_or_obsdiff_list: list[str],
    img_dir: str,
    incl_yrs_plot_items: tuple[list, str, slice | None],
    debug: bool,
) -> str:
    """Generate comparison maps between CLM and EarthStat for a single crop.

    This is the main function for creating map visualizations comparing CLM
    crop model output with EarthStat observational data. It generates maps
    for each case in the case list, supporting both CLM-only maps and
    CLM-EarthStat difference maps.

    Parameters
    ----------
    stat_strings : tuple of (str, str)
        Tuple of (display_name, variable_name) for the statistic.
        E.g., ('Yield', 'yield') or ('Production', 'prod').
    case_list : list of CropCase
        List of CropCase objects, each containing CLM crop output data.
        Each case must have a cft_ds attribute with crop statistics.
    case_legend_list : list of str
        List of legend labels for each case, in same order as case_list.
    earthstat_data : EarthStat
        EarthStat data object containing observational crop statistics.
        Must support indexing by resolution and sel() for time slicing.
    crop : str
        Name of the crop to process (e.g., 'corn', 'wheat', 'soy').
    key_case_dict : dict
        Dictionary mapping key case identifiers to case values for
        creating difference-from-reference plots. Must have at least
        one entry. Value None results in a figure sans key case comparison.
    clm_or_obsdiff_list : list of str
        List specifying which map types to create:
        - 'None': CLM-only maps
        - Other values: CLM-EarthStat difference maps
    img_dir : str
        Directory where output PNG files will be saved.
    incl_yrs_plot_items : tuple
        Tuple of (years_range_object, year_range_string, time_slice)
        specifying the time period to analyze.
    debug : bool
        If True, raise exceptions and print detailed error messages.
        If False, skip problematic cases with warning messages.

    Returns
    -------
    str
        Status message indicating completion, formatted as:
        "{Crop} {statistic} {year_range}"

    Notes
    -----
    The function performs the following steps for each map type:
    1. Determines time overlap between CLM, EarthStat, and key case (if any)
    2. Extracts or calculates the requested statistic for each case
    3. Handles key case comparisons if specified
    4. Creates multi-panel maps using ResultsMaps class
    5. Saves figures to disk with standardized filenames

    Map types:
    - CLM-only: Shows mean CLM values for each case
    - CLM-EarthStat difference: Shows (CLM - EarthStat) for each case
    - Key case difference: Shows difference from a reference case. Can be applied
      to either of the above types.

    The function handles missing data gracefully, skipping cases where
    required variables are unavailable.

    Examples
    --------
    >>> result = clm_and_earthstat_maps_1crop(
    ...     stat_strings=('Yield', 'yield'),
    ...     case_list=[case1, case2],
    ...     case_legend_list=['Case 1', 'Case 2'],
    ...     earthstat_data=earthstat_obj,
    ...     crop='corn',
    ...     key_case_dict={"Values": None},
    ...     clm_or_obsdiff_list=['None', 'obsdiff'],
    ...     img_dir='./figures',
    ...     incl_yrs_plot_items=([2000, 2010], '2000-2010', slice(2000, 2010)),
    ...     debug=False
    ... )
    >>> print(result)
    'Corn Yield 2000-2010'
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
