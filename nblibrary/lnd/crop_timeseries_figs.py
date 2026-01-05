"""
For making timeseries figures of CLM crop outputs
"""
from __future__ import annotations

import os
import warnings

import bokeh_html_utils
import numpy as np
import pandas as pd
import xarray as xr
from earthstat import align_time
from matplotlib import pyplot as plt
from plotting_utils import get_dummy_timeseries
from plotting_utils import get_maturity_level_from_stat
from plotting_utils import handle_exception

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


def get_line_plot_kwargs(opts, c):
    """
    Given options and a case index, return a dict to be used as kwargs for plot()
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


def setup_fig(opts):
    fig_opts = {}
    n_crops_to_include = len(opts["crops_to_include"])
    if 5 <= n_crops_to_include <= 6:
        nrows = 2
        ncols = 3
        height = 10.5
        width = 15
        fig_opts["hspace"] = 0.25
        fig_opts["wspace"] = 0.35
    else:
        raise RuntimeError(f"Specify figure layout for Ncrops=={n_crops_to_include}")
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(width, height))
    return fig_opts, fig, axes


def _norm(data):
    """
    Normalize timeseries by dividing by its mean
    """
    if isinstance(data, xr.DataArray):
        return data / data.mean().values
    return data / data.mean()


def _detrend(data):
    """
    Detrend using a 5-year rolling mean, after Müller et al. (2017; doi:10.5194/gmd-10-1403-2017)
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


def _normdetrend(data):
    return _detrend(_norm(data))


def _plot_clm_cases(
    case_list,
    opts,
    var_details,
    crop,
    use_earthstat_area,
    do_normdetrend,
    maturity,
):
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


def _get_clm_yield(crop, case, use_earthstat_area, maturity):
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


def _get_clm_prod(crop, case, use_earthstat_area, maturity):
    if use_earthstat_area:
        this_var = f"crop_prod_{maturity}_es"
    else:
        this_var = f"crop_prod_{maturity}"

    if this_var not in case.cft_ds:
        return [this_var]

    da = case.cft_ds[this_var].sel(crop=crop)
    return da.sum(dim=[dim for dim in da.dims if dim != "time"])


def _get_clm_area(crop, case, use_earthstat_area, *args):
    if use_earthstat_area:
        this_var = "crop_area_es"
    else:
        this_var = "crop_area"

    if this_var not in case.cft_ds:
        return [this_var]

    da = case.cft_ds[this_var].sel(crop=crop)
    return da.sum(dim=[dim for dim in da.dims if dim != "time"])


def get_legend_labels(opts, *, incl_faostat=True, incl_earthstat=True):
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


def finish_fig(opts, fig_opts, fig, *, incl_faostat=True, incl_earthstat=True):
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
    fao_yield_world,
    crop,
    ax,
    time_da,
    ctsm_units,
    do_normdetrend,
    line_color,
):
    faostat_units = fao_yield_world["Unit"].iloc[0]
    if faostat_units != ctsm_units:
        raise RuntimeError(
            f"CTSM units ({ctsm_units}) do not match FAOSTAT units ({faostat_units})",
        )
    fao_yield_world_thiscrop = fao_yield_world.query(f"Crop == '{crop}'")

    # Only include years of overlap between FAO and CLM data
    fao_years = (
        fao_yield_world_thiscrop.index.get_level_values("Year").unique().tolist()
    )
    clm_start = time_da.time.values[0].year
    clm_end = time_da.time.values[-1].year
    fao_start = min(fao_years)
    fao_end = max(fao_years)
    start = max(clm_start, fao_start)
    end = min(clm_end, fao_end)
    assert start <= end

    time_slice = slice(f"{start}-01-01", f"{end}-12-31")
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
    which,
    earthstat_data,
    crop,
    ax,
    target_time,
    do_normdetrend,
    line_color,
):
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


def _get_var_details(which, fao_data_world):
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
    do_normdetrend,
    which,
    earthstat_data,
    case_list,
    fao_data,
    maturity,
    opts,
    *,
    use_earthstat_area=False,
    fig_file=None,
):

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
    for i, crop in enumerate(opts["crops_to_include"]):
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


def main(stat_dict, img_dir, earthstat_data, case_list, fao_dict, opts):
    """
    For making timeseries figures of CLM crop outputs
    """

    # Make sure output dir exists
    os.makedirs(img_dir, exist_ok=True)

    # Make a local copy of this, deleting EarthStat if not available
    this_area_source_dict = AREA_SOURCE_DICT.copy()
    if earthstat_data is None:
        del this_area_source_dict["EarthStat"]

    for stat, stat_input in stat_dict.items():

        # Handle request for detrending via stat_input
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
            # Get filename to which figure will be saved. Members of join_list
            # must first be any dropdown menu members and then any radio button
            # group members, in the orders given in dropdown_specs and radio_specs,
            # respectively.
            join_list = [stat, area_source]
            fig_basename = bokeh_html_utils.sanitize_filename("_".join(join_list))
            fig_basename += ".png"
            fig_path = os.path.join(img_dir, fig_basename)

            with warnings.catch_warnings():
                # This suppresses some very annoying warnings when
                # use_earthstat_area=True. I'd like to eventually resolve this
                # properly, which will probably requiring compute()ing some of
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
                index_colname = "legend_labels"
                std_table_dict = {index_colname: legend_labels}
                for crop in opts["crops_to_include"]:
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
    bokeh_html_utils.create_static_html(
        dropdown_specs=dropdown_specs,
        radio_specs=radio_specs,
        output_dir=img_dir,
        show_in_notebook=True,
    )
