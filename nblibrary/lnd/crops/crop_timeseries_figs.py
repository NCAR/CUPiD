"""
For making timeseries figures of CLM crop outputs
"""

from __future__ import annotations

from typing import Any

import os
import warnings

import numpy as np
import pandas as pd
import xarray as xr
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from externals.ctsm_postprocessing.crops.cropcase import CropCase
from externals.ctsm_postprocessing.crops.crop_case_list import CropCaseList

from .bokeh_html_utils import create_static_html
from .bokeh_html_utils import sanitize_filename
from .earthstat import EarthStat, align_time
from .plotting_utils import get_dummy_timeseries
from .plotting_utils import get_maturity_level_from_stat
from .plotting_utils import handle_exception

EARTHSTAT_RES_TO_PLOT = "f09"
OBS_DUMMY_LINECOLOR = "obs not in dict"

# When printing a Pandas DataFrame, don't wrap it
pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", None)
pd.set_option("display.expand_frame_repr", False)

# Dictionary whose keys will be used as dropdown menu options and whose values
# will be used for the use_earthstat_area arg in crop_timeseries_figs(). At the
# moment this could work as radio buttons, but I'd like to eventually add a few
# more observational data sources.
AREA_SOURCE_DICT = {
    "CLM": False,
    "EarthStat": True,
}


def get_line_plot_kwargs(opts: dict, c: int) -> dict[str, Any]:
    """
    Given options and a case index, return a dict to be used as kwargs for plot().

    Parameters
    ----------
    opts : dict
        Options dictionary containing 'case_name_list' and optionally 'line_colors'.
    c : int
        Case index.

    Returns
    -------
    dict[str, Any]
        Dictionary with plot kwargs including 'linestyle' and optionally 'color'.
    """
    plot_kwargs = {}

    # Change line style for one line that overlaps another for some crops
    # TODO: Optionally define linestyle for each case in config.yml
    if "clm6_crop_032_nomaxlaitrig" in opts["case_name_list"] and opts[
        "case_name_list"
    ][c].endswith("clm6_crop_032_nmlt_phaseparams"):
        linestyle = "--"
    else:
        linestyle = "-"
    plot_kwargs["linestyle"] = linestyle

    # Change line color, if requested
    if opts["line_colors"] is not None:
        plot_kwargs["color"] = opts["line_colors"][c]

    return plot_kwargs


def setup_fig(opts: dict) -> tuple[dict[str, Any], Figure, np.ndarray]:
    """
    Set up figure and axes for timeseries plots.

    Parameters
    ----------
    opts : dict
        Options dictionary containing 'crops_to_plot'.

    Returns
    -------
    tuple[dict[str, Any], matplotlib.figure.Figure, numpy.ndarray]
        Tuple containing:
        - fig_opts: Dictionary with 'hspace' and 'wspace' spacing parameters
        - fig: Matplotlib Figure object
        - axes: Array of Axes objects
    """
    fig_opts = {}

    # Things that probably need to be optimized based on number of crops
    n_crops_to_plot = len(opts["crops_to_plot"])
    ncols = 3
    nrows = int(np.ceil(n_crops_to_plot / ncols))
    height = 4.5 * nrows + 1.5
    width = 15
    fig_opts["hspace"] = 0.25
    fig_opts["wspace"] = 0.35
    if not 5 <= n_crops_to_plot <= 6:
        warnings.warn(f"Figure layout only tested for 5-6 crops, not {n_crops_to_plot}")

    # Set up figure
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(width, height))
    return fig_opts, fig, axes


def _norm(data: xr.DataArray | pd.Series) -> xr.DataArray | pd.Series:
    """
    Normalize timeseries by dividing by its mean.

    Parameters
    ----------
    data : xarray.DataArray | pandas.Series
        Timeseries data to normalize.

    Returns
    -------
    xarray.DataArray | pandas.Series
        Normalized data (same type as input).
    """
    if isinstance(data, xr.DataArray):
        return data / data.mean().values
    return data / data.mean()


def _detrend(data: xr.DataArray | pd.Series) -> xr.DataArray | pd.Series:
    """
    Detrend using a 5-year rolling mean.

    After Müller et al. (2017; doi:10.5194/gmd-10-1403-2017).

    Parameters
    ----------
    data : xarray.DataArray | pandas.Series
        Timeseries data to detrend.

    Returns
    -------
    xarray.DataArray | pandas.Series
        Detrended data (same type as input).
    """
    window_width = 5  # years

    # xarray DataArray
    if isinstance(data, xr.DataArray):
        if "earthstat_time_coord" in data.dims:
            smoothed = data.rolling(
                earthstat_time_coord=window_width,
                center=True,
            ).mean()
        else:
            smoothed = data.rolling(time=window_width, center=True).mean()
    # Other (hopefully it's a pandas object)
    else:
        smoothed = data.rolling(window_width, center=True).mean()

    return data - smoothed


def _normdetrend(data: xr.DataArray | pd.Series) -> xr.DataArray | pd.Series:
    """
    Normalize and detrend timeseries data.

    Applies normalization followed by detrending using a 5-year rolling mean.

    Parameters
    ----------
    data : xarray.DataArray | pandas.Series
        Timeseries data to process.

    Returns
    -------
    xarray.DataArray | pandas.Series
        Normalized and detrended data (same type as input).
    """
    return _detrend(_norm(data))


def _plot_clm_cases(
    case_list: CropCaseList,
    opts: dict,
    var_details: dict[str, Any],
    crop: str,
    use_earthstat_area: bool,
    do_normdetrend: bool,
    maturity: str,
) -> None:
    """
    Plot CLM data for all cases.

    Parameters
    ----------
    case_list : CropCaseList
        List of CropCase objects to plot.
    opts : dict
        Options dictionary containing 'case_legend_list', 'debug', and optionally 'line_colors'.
    var_details : dict[str, Any]
        Dictionary with variable details including 'function', 'da_name', 'conversion_factor',
        and 'ctsm_units'.
    crop : str
        Name of the crop to plot.
    use_earthstat_area : bool
        Whether to use EarthStat area for calculations.
    do_normdetrend : bool
        Whether to normalize and detrend the data.
    maturity : str
        Maturity level (e.g., 'any', 'marketable', 'mature').
    """
    for c, case in enumerate(case_list):

        # Get the data from this case.
        this_fn = var_details["function"]
        skip_msg = (
            f'Skipping {crop} {var_details["da_name"]} for case {case.name} '
            f'({opts["case_legend_list"][c]}) because '
        )
        # Define default value here so we only have one command under "try"
        crop_data_ts = None
        try:
            crop_data_ts = this_fn(crop, case, use_earthstat_area, maturity)
        except Exception as e:  # pylint: disable=broad-exception-caught
            skip_msg = f"Skipping {this_fn.__name__}() for {case.name} due to"
            handle_exception(opts["debug"], e, skip_msg)
        if isinstance(crop_data_ts, list):
            print(skip_msg + f"required variable(s) missing: {crop_data_ts}")
            crop_data_ts = None

        # If we don't have data for this case, make a dummy timeseries with all NaNs. This ensures
        # that there is still a spot for this case in the legend, which makes it obvious in the
        # figure that we didn't just forget to plot it. It also makes it easier to have the right
        # colors in the legend for the lines that we did plot.
        if crop_data_ts is None:
            crop_data_ts = get_dummy_timeseries(case.cft_ds)

        # If we do have data for this case, do some extra processing.
        else:
            if use_earthstat_area:
                crop_data_ts = crop_data_ts.sel(time=case.cft_ds["earthstat_time"])

            # Apply conversion factor
            crop_data_ts *= var_details["conversion_factor"]

            # Normalize/detrend, if doing so
            if do_normdetrend:
                crop_data_ts = _normdetrend(crop_data_ts)

        # Plot data
        crop_data_ts.name = var_details["da_name"]
        if do_normdetrend:
            crop_data_ts.attrs["units"] = "unitless"
        else:
            crop_data_ts.attrs["units"] = var_details["ctsm_units"]

        # Plot
        plot_kwargs = get_line_plot_kwargs(opts, c)
        crop_data_ts.plot(**plot_kwargs)


def _get_clm_yield(
    crop: str,
    case: CropCase,
    use_earthstat_area: bool,
    maturity: str,
) -> xr.DataArray | list[str]:
    """
    Get CLM yield timeseries for a crop.

    Parameters
    ----------
    crop : str
        Name of the crop.
    case : CropCase
        CropCase object containing the data.
    use_earthstat_area : bool
        Whether to use EarthStat area for calculations.
    maturity : str
        Maturity level (e.g., 'any', 'marketable', 'mature').

    Returns
    -------
    xarray.DataArray | list[str]
        Yield timeseries DataArray, or list of missing variable names if data unavailable.
    """
    if use_earthstat_area:
        this_area = "crop_area_es"
        this_prod = f"crop_prod_{maturity}_es"
    else:
        this_area = "crop_area"
        this_prod = f"crop_prod_{maturity}"

    missing_vars = [var for var in [this_area, this_prod] if var not in case.cft_ds]
    if missing_vars:
        return missing_vars

    da_prod = case.cft_ds[this_prod].sel(crop=crop)
    da_area = case.cft_ds[this_area].sel(crop=crop)
    crop_prod_ts = da_prod.sum(dim=[dim for dim in da_prod.dims if dim != "time"])
    crop_area_ts = da_area.sum(dim=[dim for dim in da_area.dims if dim != "time"])
    crop_yield_ts = crop_prod_ts / crop_area_ts

    return crop_yield_ts


def _get_clm_prod(
    crop: str,
    case: CropCase,
    use_earthstat_area: bool,
    maturity: str,
) -> xr.DataArray | list[str]:
    """
    Get CLM production timeseries for a crop.

    Parameters
    ----------
    crop : str
        Name of the crop.
    case : CropCase
        CropCase object containing the data.
    use_earthstat_area : bool
        Whether to use EarthStat area for calculations.
    maturity : str
        Maturity level (e.g., 'any', 'marketable', 'mature').

    Returns
    -------
    xarray.DataArray | list[str]
        Production timeseries DataArray, or list of missing variable names if data unavailable.
    """
    if use_earthstat_area:
        this_var = f"crop_prod_{maturity}_es"
    else:
        this_var = f"crop_prod_{maturity}"

    if this_var not in case.cft_ds:
        return [this_var]

    da = case.cft_ds[this_var].sel(crop=crop)
    return da.sum(dim=[dim for dim in da.dims if dim != "time"])


def _get_clm_area(
    crop: str,
    case: CropCase,
    use_earthstat_area: bool,
    *args,  # pylint: disable=unused-argument
) -> xr.DataArray | list[str]:
    """
    Get CLM area timeseries for a crop.

    Parameters
    ----------
    crop : str
        Name of the crop.
    case : CropCase
        CropCase object containing the data.
    use_earthstat_area : bool
        Whether to use EarthStat area.
    *args
        Additional arguments (ignored).

    Returns
    -------
    xarray.DataArray | list[str]
        Area timeseries DataArray, or list of missing variable names if data unavailable.
    """
    if use_earthstat_area:
        this_var = "crop_area_es"
    else:
        this_var = "crop_area"

    if this_var not in case.cft_ds:
        return [this_var]

    da = case.cft_ds[this_var].sel(crop=crop)
    return da.sum(dim=[dim for dim in da.dims if dim != "time"])


def get_legend_labels(
    opts: dict,
    *,
    incl_faostat: bool = True,
    incl_earthstat: bool = True,
) -> list[str]:
    """
    Get legend labels for the timeseries plot.

    Parameters
    ----------
    opts : dict
        Options dictionary containing 'case_legend_list' and 'obs_timeseries_linecolors'.
    incl_faostat : bool, optional
        Whether to include FAOSTAT in the legend. Default is True.
    incl_earthstat : bool, optional
        Whether to include EarthStat in the legend. Default is True.

    Returns
    -------
    list[str]
        List of legend labels.

    Raises
    ------
    ValueError
        If unrecognized keys are found in opts['obs_timeseries_linecolors'].
    """
    labels = opts["case_legend_list"].copy()
    if incl_faostat or incl_earthstat:
        obs_timeseries_linecolors = opts["obs_timeseries_linecolors"].copy()

        # Add FAOSTAT?
        line_color = obs_timeseries_linecolors.pop("faostat", OBS_DUMMY_LINECOLOR)
        if incl_faostat and line_color != OBS_DUMMY_LINECOLOR:
            labels += ["FAOSTAT"]

        # Add EarthStat?
        line_color = obs_timeseries_linecolors.pop("earthstat", OBS_DUMMY_LINECOLOR)
        if incl_earthstat and line_color != OBS_DUMMY_LINECOLOR:
            labels += ["EarthStat"]

        # Ensure no unrecognized obs datasets were requested. obs_to_include.pop() calls above
        # should have removed any processed obs datasets.
        if obs_timeseries_linecolors:
            raise ValueError(
                "Unexpected key(s) in opts['obs_timeseries_linecolors']: "
                + str(obs_timeseries_linecolors.keys()),
            )
    return labels


def finish_fig(
    opts: dict,
    fig_opts: dict,
    fig: Figure,
    *,
    incl_faostat: bool = True,
    incl_earthstat: bool = True,
) -> list[str]:
    """
    Finalize figure with legend and title.

    Parameters
    ----------
    opts : dict
        Options dictionary.
    fig_opts : dict
        Figure options dictionary containing 'wspace', 'hspace', and 'title'.
    fig : matplotlib.figure.Figure
        Figure object to finalize.
    incl_faostat : bool, optional
        Whether to include FAOSTAT in the legend. Default is True.
    incl_earthstat : bool, optional
        Whether to include EarthStat in the legend. Default is True.

    Returns
    -------
    list[str]
        List of legend labels that were added.
    """
    plt.subplots_adjust(wspace=fig_opts["wspace"], hspace=fig_opts["hspace"])
    legend_labels = get_legend_labels(
        opts,
        incl_faostat=incl_faostat,
        incl_earthstat=incl_earthstat,
    )
    fig.legend(
        labels=legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=3,
        bbox_transform=fig.transFigure,
    )
    fig.suptitle(fig_opts["title"], fontsize="x-large", fontweight="bold")
    return legend_labels


def _plot_faostat(
    fao_yield_world: pd.DataFrame,
    crop: str,
    ax: plt.Axes,
    time_da: xr.DataArray,
    ctsm_units: str,
    do_normdetrend: bool,
    line_color: str,
) -> None:
    """
    Plot FAOSTAT data for a crop.

    Parameters
    ----------
    fao_yield_world : pandas.DataFrame
        FAOSTAT data for all crops.
    crop : str
        Name of the crop to plot.
    ax : matplotlib.axes.Axes
        Axes object to plot on.
    time_da : xarray.DataArray
        Time coordinate DataArray for alignment.
    ctsm_units : str
        Units expected from CTSM (must match FAOSTAT units).
    do_normdetrend : bool
        Whether to normalize and detrend the data.
    line_color : str
        Color for the plot line.

    Raises
    ------
    RuntimeError
        If CTSM units don't match FAOSTAT units.
    """
    faostat_units = fao_yield_world["Unit"].iloc[0]
    if faostat_units != ctsm_units:
        raise RuntimeError(
            f"CTSM units ({ctsm_units}) do not match FAOSTAT units ({faostat_units})",
        )
    fao_yield_world_thiscrop = fao_yield_world.query(f"Crop == '{crop}'")

    # We may want to use this with time_da DataArrays that are a DateTime type. Otherwise we'll
    # assume that the values are just numeric years.
    target_time_is_dt_type = hasattr(time_da.values[0], "year")

    # Only include years of overlap between FAO and CLM data
    fao_years = (
        fao_yield_world_thiscrop.index.get_level_values("Year").unique().tolist()
    )
    clm_start = time_da.time.values[0]
    clm_end = time_da.time.values[-1]
    if target_time_is_dt_type:
        clm_start = clm_start.year
        clm_end = clm_end.year
    fao_start = min(fao_years)
    fao_end = max(fao_years)
    start = max(clm_start, fao_start)
    end = min(clm_end, fao_end)
    assert start <= end

    if target_time_is_dt_type:
        time_slice = slice(f"{start}-01-01", f"{end}-12-31")
    else:
        time_slice = slice(start, end)
    ydata = fao_yield_world_thiscrop.query(f"(Year >= {start}) & (Year <= {end})")
    if do_normdetrend:
        ydata["Value"] = _normdetrend(ydata["Value"])
    ydata = ydata["Value"].values
    ax.plot(
        time_da.sel(time=time_slice),
        ydata,
        line_color,
    )


def _plot_earthstat(
    which: str,
    earthstat_data: EarthStat,
    crop: str,
    ax: plt.Axes,
    target_time: xr.DataArray,
    do_normdetrend: bool,
    line_color: str,
) -> None:
    """
    Plot EarthStat data for a crop.

    Parameters
    ----------
    which : str
        Which variable to plot ('yield', 'prod', or 'area').
    earthstat_data : EarthStat
        EarthStat object containing observed crop data.
    crop : str
        Name of the crop to plot.
    ax : matplotlib.axes.Axes
        Axes object to plot on.
    target_time : xarray.DataArray
        Time coordinate DataArray for alignment.
    do_normdetrend : bool
        Whether to normalize and detrend the data.
    line_color : str
        Color for the plot line.
    """
    target_units = {
        "prod": "Mt",
        "area": "Mha",
    }
    if which == "yield":
        earthstat_prod = earthstat_data.get_data(
            EARTHSTAT_RES_TO_PLOT,
            "prod",
            crop,
            target_units["prod"],
        )
        earthstat_area = earthstat_data.get_data(
            EARTHSTAT_RES_TO_PLOT,
            "area",
            crop,
            target_units["area"],
        )
        if earthstat_prod is None or earthstat_area is None:
            return
        earthstat_var = earthstat_prod.sum(dim=["lat", "lon"]) / earthstat_area.sum(
            dim=["lat", "lon"],
        )
    else:
        earthstat_var = earthstat_data.get_data(
            EARTHSTAT_RES_TO_PLOT,
            which,
            crop,
            target_units[which],
        )
        if earthstat_var is None:
            return
        earthstat_var = earthstat_var.sum(dim=["lat", "lon"])

    # Align EarthStat data with CLM time axis
    earthstat_var = align_time(earthstat_var, target_time)

    if do_normdetrend:
        earthstat_var = _normdetrend(earthstat_var)

    ax.plot(
        earthstat_var["time"],
        earthstat_var.values,
        line_color,
    )


def _get_var_details(which: str, fao_data_world: pd.DataFrame | None) -> dict[str, Any]:
    """
    Get variable details for plotting including units and conversion factors.

    Parameters
    ----------
    which : str
        Which variable to get details for ('yield', 'prod', or 'area').
    fao_data_world : pandas.DataFrame | None
        FAOSTAT world data to modify in place, or None if not using FAOSTAT.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys 'da_name', 'ctsm_units', 'conversion_factor', and 'function'.

    Raises
    ------
    NotImplementedError
        If which is not 'yield', 'prod', or 'area'.
    """
    var_details = {}
    if which == "yield":
        var_details["da_name"] = "Yield"
        var_details["ctsm_units"] = "t/ha"
        var_details["conversion_factor"] = 1e-6 * 1e4  # Convert g/m2 to tons/ha
        var_details["function"] = _get_clm_yield
    elif which == "prod":
        var_details["da_name"] = "Production"
        var_details["ctsm_units"] = "Mt"
        var_details["conversion_factor"] = 1e-6 * 1e-6  # Convert g to Mt
        var_details["function"] = _get_clm_prod
        if fao_data_world is not None:
            fao_data_world["Value"] = fao_data_world["Value"] * 1e-6
            fao_data_world["Unit"] = "Mt"
    elif which == "area":
        var_details["da_name"] = "Area"
        var_details["ctsm_units"] = "Mha"
        var_details["conversion_factor"] = 1e-4 * 1e-6  # Convert m2 to Mha
        var_details["function"] = _get_clm_area
        if fao_data_world is not None:
            fao_data_world["Value"] *= 1e-6
            fao_data_world["Unit"] = "Mha"
    else:
        raise NotImplementedError(
            f"crop_timeseries_figs() not set up for which={which}",
        )

    return var_details


def _one_fig(
    do_normdetrend: bool,
    which: str,
    earthstat_data: EarthStat,
    case_list: CropCaseList,
    fao_data: pd.DataFrame | None,
    maturity: str,
    opts: dict,
    *,
    use_earthstat_area: bool = False,
    fig_file: str | None = None,
) -> None:
    """
    Create one timeseries figure for a specific variable and maturity level.

    Parameters
    ----------
    do_normdetrend : bool
        Whether to normalize and detrend the data.
    which : str
        Which variable to plot ('yield', 'prod', or 'area').
    earthstat_data : EarthStat
        EarthStat object containing observed crop data.
    case_list : CropCaseList
        List of CropCase objects to plot.
    fao_data : pandas.DataFrame | None
        FAOSTAT data, or None if not using FAOSTAT.
    maturity : str
        Maturity level (e.g., 'any', 'marketable', 'mature').
    opts : dict
        Options dictionary containing configuration settings.
    use_earthstat_area : bool, optional
        Whether to use EarthStat area for calculations. Default is False.
    fig_file : str | None, optional
        Path to save the figure, or None to not save. Default is None.
    """
    # Get figure layout info
    fig_opts, fig, axes = setup_fig(opts)

    # This .copy() prevents spooky side effects from operational persistence
    fao_data_world = None
    if fao_data is not None:
        fao_data_world = fao_data.copy().query("Area == 'World'")

    # Set up for the variable we want
    # TODO: Increase robustness of unit conversion: Check that it really is, e.g., g/m2 to start
    # with.
    var_details = _get_var_details(which, fao_data_world)
    fig_opts["title"] = "Global " + var_details["da_name"].lower() + f" ({maturity})"
    if do_normdetrend:
        fig_opts["title"] += " (normalized, detrended)"

    # Modify figure options
    if use_earthstat_area:
        fig_opts["title"] += " (if CLM used EarthStat areas)"

    std_dict = {}
    for i, crop in enumerate(opts["crops_to_plot"]):
        ax = axes.ravel()[i]
        plt.sca(ax)
        obs_timeseries_linecolors = opts["obs_timeseries_linecolors"].copy()

        # Plot case data
        _plot_clm_cases(
            case_list,
            opts,
            var_details,
            crop,
            use_earthstat_area,
            do_normdetrend,
            maturity,
        )

        # Plot FAOSTAT data
        line_color = obs_timeseries_linecolors.pop("faostat", OBS_DUMMY_LINECOLOR)
        incl_faostat = fao_data_world is not None
        if incl_faostat and line_color != OBS_DUMMY_LINECOLOR:
            _plot_faostat(
                fao_data_world,
                crop,
                ax,
                case_list[0].cft_ds["time"],
                var_details["ctsm_units"],
                do_normdetrend,
                line_color,
            )

        # Plot EarthStat data
        line_color = obs_timeseries_linecolors.pop("earthstat", OBS_DUMMY_LINECOLOR)
        incl_earthstat = earthstat_data is not None
        if incl_earthstat and line_color != OBS_DUMMY_LINECOLOR:
            _plot_earthstat(
                which,
                earthstat_data,
                crop,
                ax,
                case_list[0].cft_ds["time"],
                do_normdetrend,
                line_color,
            )

        # Finish plot
        ax.set_title(crop)
        plt.xlabel("")

        # Ensure no unrecognized obs datasets were requested. obs_to_include.pop() calls above
        # should have removed any processed obs datasets.
        if obs_timeseries_linecolors:
            raise ValueError(
                "Unexpected key(s) in opts['obs_timeseries_linecolors']: "
                + str(obs_timeseries_linecolors.keys()),
            )

        # Get standard deviation
        std_dict[crop] = []
        for line in ax.lines:
            ydata = line.get_ydata()
            if np.all(np.isnan(ydata)):
                std = None
            else:
                std = np.nanstd(ydata)
            std_dict[crop].append(std)

    legend_labels = finish_fig(
        opts,
        fig_opts,
        fig,
        incl_faostat=incl_faostat,
        incl_earthstat=incl_earthstat,
    )
    if fig_file is None:
        plt.show()
    else:
        plt.savefig(fig_file, dpi=150)
        plt.savefig(fig_file.replace("png", "pdf"))
        plt.close()

    return std_dict, legend_labels


def _print_stdev_table(
    opts: dict,
    maturity: str | None,
    area_source: str,
    std_dict: dict[str, list[float | None]],
    legend_labels: list[str],
) -> None:
    """
    Print a table of standard deviations for each crop and case.

    Parameters
    ----------
    opts : dict
        Options dictionary containing 'crops_to_plot'.
    maturity : str | None
        Maturity level (e.g., 'any', 'marketable', 'mature'), or None.
    area_source : str
        Area source name (e.g., 'CLM', 'EarthStat').
    std_dict : dict[str, list[float | None]]
        Dictionary mapping crop names to lists of standard deviation values.
    legend_labels : list[str]
        List of legend labels corresponding to the standard deviation values.
    """
    index_colname = "legend_labels"
    std_table_dict = {index_colname: legend_labels}
    for crop in opts["crops_to_plot"]:
        col_data = []
        for std in std_dict[crop]:
            if std is None:
                col_data.append("n.d.")  # "no data"
            else:
                col_data.append(np.round(std, 3))
        std_table_dict[crop] = col_data
    df = pd.DataFrame(std_table_dict)
    df = df.set_index(index_colname)
    df.index.name = None
    header = f"Standard deviation (CLM runs assuming {area_source} areas)"
    if maturity is not None:
        header = header.replace(")", f"; maturity '{maturity}')")
    print(header)
    print(df)
    print("\n")


def _one_stat(
    *,
    img_dir: str,
    earthstat_data: EarthStat | None,
    case_list: CropCaseList,
    fao_dict: dict[str, pd.DataFrame] | None,
    opts: dict,
    this_area_source_dict: dict[str, bool],
    stat: str,
    stat_input: str,
) -> None:
    """
    Process and plot one statistic across all area sources.

    Creates timeseries figures for a single statistic (e.g., 'yield', 'prod_normdetrend') using
    different area sources (CLM, EarthStat).

    Parameters
    ----------
    img_dir : str
        Directory path where output images will be saved.
    earthstat_data : EarthStat | None
        EarthStat object containing observed crop data, or None if not available.
    case_list : CropCaseList
        List of CropCase objects to plot.
    fao_dict : dict[str, pandas.DataFrame] | None
        Dictionary mapping statistic names to FAOSTAT DataFrames, or None if not available.
    opts : dict
        Options dictionary containing configuration settings.
    this_area_source_dict : dict[str, bool]
        Dictionary mapping area source names to whether to use EarthStat area.
    stat : str
        Statistic name (e.g., 'yield', 'prod_normdetrend').
    stat_input : str
        Statistic specification string.
    """
    # pylint: disable=too-many-arguments, too-many-locals

    suffix = "_normdetrend"
    do_normdetrend = suffix in stat_input
    if do_normdetrend:
        stat_input = stat_input.replace(suffix, "")

    # Handle requested maturity level
    stat_input, maturity = get_maturity_level_from_stat(stat_input)

    # Get FAO data, if available
    fao_data = None
    if fao_dict is not None:
        fao_data = fao_dict[stat_input]

    for area_source, use_earthstat_area in this_area_source_dict.items():
        # Get filename to which figure will be saved. Members of join_list must first be any
        # dropdown menu members and then any radio button group members, in the orders given in
        # dropdown_specs and radio_specs,respectively.
        join_list = [stat, area_source]
        fig_basename = sanitize_filename("_".join(join_list))
        fig_basename += ".png"
        fig_path = os.path.join(img_dir, fig_basename)

        with warnings.catch_warnings():
            # This suppresses some very annoying warnings when use_earthstat_area=True. I'd like to
            # eventually resolve this properly, which will probably requiring compute()ing some of
            # the metadata variables in the cft_ds Datasets.
            warnings.filterwarnings(
                "ignore",
                message="Sending large graph.*",
                category=UserWarning,
            )
            std_dict, legend_labels = _one_fig(
                do_normdetrend,
                stat_input,
                earthstat_data,
                case_list,
                fao_data,
                maturity,
                opts,
                use_earthstat_area=use_earthstat_area,
                fig_file=fig_path,
            )

        # Print standard deviation table
        if do_normdetrend:
            _print_stdev_table(opts, maturity, area_source, std_dict, legend_labels)


def main(
    *,
    stat_dict: dict[str, str],
    img_dir: str,
    earthstat_data: EarthStat | None,
    case_list: CropCaseList,
    fao_dict: dict[str, pd.DataFrame] | None,
    opts: dict,
) -> None:
    # pylint: disable=too-many-arguments
    """
    Create timeseries figures of CLM crop outputs.

    Generates timeseries plots comparing CLM crop statistics (yield, production, area) against
    observational datasets (FAOSTAT, EarthStat) for multiple crops and cases.

    Parameters
    ----------
    stat_dict : dict[str, str]
        Dictionary mapping statistic names to their specifications (e.g., 'yield',
        'prod_normdetrend').
    img_dir : str
        Directory path where output images will be saved.
    earthstat_data : EarthStat | None
        EarthStat object containing observed crop data, or None if not available.
    case_list : CropCaseList
        List of CropCase objects to plot.
    fao_dict : dict[str, pandas.DataFrame] | None
        Dictionary mapping statistic names to FAOSTAT DataFrames, or None if not available.
    opts : dict
        Options dictionary containing configuration settings including 'crops_to_plot',
        'case_legend_list', 'obs_timeseries_linecolors', and 'debug'.
    """
    # Make sure output dir exists
    os.makedirs(img_dir, exist_ok=True)

    # Make a local copy of this, deleting EarthStat if not available
    this_area_source_dict = AREA_SOURCE_DICT.copy()
    if earthstat_data is None:
        del this_area_source_dict["EarthStat"]

    for stat, stat_input in stat_dict.items():

        # Handle request for detrending via stat_input
        _one_stat(
            img_dir=img_dir,
            earthstat_data=earthstat_data,
            case_list=case_list,
            fao_dict=fao_dict,
            opts=opts,
            this_area_source_dict=this_area_source_dict,
            stat=stat,
            stat_input=stat_input,
        )

    # Build dropdown specs
    dropdown_specs = [
        {
            "title": "Statistic",
            "options": list(stat_dict.keys()),
        },
        {
            "title": "Area source",
            "options": list(this_area_source_dict.keys()),
        },
    ]

    # Build radio specs
    radio_specs = []

    # Display in notebook
    create_static_html(
        dropdown_specs=dropdown_specs,
        radio_specs=radio_specs,
        output_dir=img_dir,
        show_in_notebook=True,
    )
