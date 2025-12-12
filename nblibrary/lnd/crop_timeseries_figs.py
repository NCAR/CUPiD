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

EARTHSTAT_RES_TO_PLOT = "f09"
LINECOLOR_FAOSTAT = "black"
LINECOLOR_EARTHSTAT = "0.5"  # gray

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
):
    for c, case in enumerate(case_list):

        crop_data_ts = var_details["function"](crop, case, use_earthstat_area)
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


def _get_clm_yield(crop, case, use_earthstat_area):
    if use_earthstat_area:
        this_area = "crop_area_es"
        this_prod = "crop_prod_es"
    else:
        this_area = "crop_area"
        this_prod = "crop_prod"

    da_prod = case.cft_ds[this_prod].sel(crop=crop)
    da_area = case.cft_ds[this_area].sel(crop=crop)
    crop_prod_ts = da_prod.sum(dim=[dim for dim in da_prod.dims if dim != "time"])
    crop_area_ts = da_area.sum(dim=[dim for dim in da_area.dims if dim != "time"])
    crop_yield_ts = crop_prod_ts / crop_area_ts

    return crop_yield_ts


def _get_clm_prod(crop, case, use_earthstat_area):
    if use_earthstat_area:
        this_var = "crop_prod_es"
    else:
        this_var = "crop_prod"
    da = case.cft_ds[this_var].sel(crop=crop)
    return da.sum(dim=[dim for dim in da.dims if dim != "time"])


def _get_clm_area(crop, case, use_earthstat_area):
    if use_earthstat_area:
        da = case.cft_ds["crop_area_es"].sel(crop=crop)
    else:
        da = case.cft_ds["crop_area"].sel(crop=crop)
    return da.sum(dim=[dim for dim in da.dims if dim != "time"])


def get_legend_labels(opts, incl_obs=True):
    labels = opts["case_legend_list"].copy()
    if incl_obs:
        labels += ["FAOSTAT", f"EarthStat {EARTHSTAT_RES_TO_PLOT}"]
    return labels


def finish_fig(opts, fig_opts, fig, *, incl_obs=True):
    plt.subplots_adjust(wspace=fig_opts["wspace"], hspace=fig_opts["hspace"])
    labels = get_legend_labels(opts, incl_obs)
    fig.legend(
        labels=labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=3,
        bbox_transform=fig.transFigure,
    )
    fig.suptitle(fig_opts["title"], fontsize="x-large", fontweight="bold")


def _plot_faostat(fao_yield_world, crop, ax, time_da, ctsm_units, do_normdetrend):
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
        LINECOLOR_FAOSTAT,
    )


def _plot_earthstat(which, earthstat_data, crop, ax, target_time, do_normdetrend):
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
        LINECOLOR_EARTHSTAT,
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
        fao_data_world["Value"] = fao_data_world["Value"] * 1e-6
        fao_data_world["Unit"] = "Mt"
    elif which == "area":
        var_details["da_name"] = "Area"
        var_details["ctsm_units"] = "Mha"
        var_details["conversion_factor"] = 1e-4 * 1e-6  # Convert m2 to Mha
        var_details["function"] = _get_clm_area
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
    opts,
    *,
    use_earthstat_area=False,
    fig_file=None,
):

    # Get figure layout info
    fig_opts, fig, axes = setup_fig(opts)

    # This .copy() prevents spooky side effects from operational persistence
    fao_data_world = fao_data.copy().query("Area == 'World'")

    # Set up for the variable we want
    # TODO: Increase robustness of unit conversion: Check that it really is, e.g., g/m2 to start
    # with.
    var_details = _get_var_details(which, fao_data_world)
    fig_opts["title"] = "Global " + var_details["da_name"].lower()
    if do_normdetrend:
        fig_opts["title"] += " (normalized, detrended)"

    # Modify figure options
    if use_earthstat_area:
        fig_opts["title"] += " (if CLM used EarthStat areas)"

    std_dict = {}
    for i, crop in enumerate(opts["crops_to_include"]):
        ax = axes.ravel()[i]
        plt.sca(ax)

        # Plot case data
        _plot_clm_cases(
            case_list,
            opts,
            var_details,
            crop,
            use_earthstat_area,
            do_normdetrend,
        )

        # Plot FAOSTAT data
        _plot_faostat(
            fao_data_world,
            crop,
            ax,
            case_list[0].cft_ds["time"],
            var_details["ctsm_units"],
            do_normdetrend,
        )

        # Plot EarthStat data
        _plot_earthstat(
            which,
            earthstat_data,
            crop,
            ax,
            case_list[0].cft_ds["time"],
            do_normdetrend,
        )

        # Finish plot
        ax.set_title(crop)
        plt.xlabel("")

        # Get standard deviation
        std_dict[crop] = []
        for line in ax.lines:
            std_dict[crop].append(np.nanstd(line.get_ydata()))

    finish_fig(opts, fig_opts, fig)
    if fig_file is None:
        plt.show()
    else:
        plt.savefig(fig_file, dpi=150)
        plt.savefig(fig_file.replace("png", "pdf"))
        plt.close()

    return std_dict


def main(stat_dict, img_dir, earthstat_data, case_list, fao_dict, opts):
    """
    For making timeseries figures of CLM crop outputs
    """

    # Make sure output dir exists
    os.makedirs(img_dir, exist_ok=True)

    for stat, stat_input in stat_dict.items():

        # Handle request for detrending via stat_input
        suffix = "_normdetrend"
        do_normdetrend = suffix in stat_input
        if do_normdetrend:
            stat_input = stat_input.replace(suffix, "")

        for area_source, use_earthstat_area in AREA_SOURCE_DICT.items():
            # Get filename to which figure will be saved. Members of join_list
            # must first be any dropdown menu members and then any radio button
            # group members, in the orders given in dropdown_specs and radio_specs,
            # respectively.
            join_list = [area_source, stat]
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
                std_dict = _one_fig(
                    do_normdetrend,
                    stat_input,
                    earthstat_data,
                    case_list,
                    fao_dict[stat_input],
                    opts,
                    use_earthstat_area=use_earthstat_area,
                    fig_file=fig_path,
                )

            # Print standard deviation table
            if do_normdetrend:
                legend_labels = get_legend_labels(opts)
                index_colname = "legend_labels"
                std_table_dict = {index_colname: legend_labels}
                for crop in opts["crops_to_include"]:
                    std_table_dict[crop] = [np.round(x, 3) for x in std_dict[crop]]
                df = pd.DataFrame(std_table_dict)
                df = df.set_index(index_colname)
                df.index.name = None
                print(f"Standard deviation (CLM runs assuming {area_source} areas)")
                print(df)
                print("\n")

    # Build dropdown specs
    dropdown_specs = [
        {
            "title": "Area source",
            "options": list(AREA_SOURCE_DICT.keys()),
        },
    ]

    # Build radio specs
    radio_specs = [
        {
            "title": "Statistic",
            "options": list(stat_dict.keys()),
        },
    ]

    # Display in notebook
    bokeh_html_utils.create_static_html(
        dropdown_specs=dropdown_specs,
        radio_specs=radio_specs,
        output_dir=img_dir,
        show_in_notebook=True,
    )
