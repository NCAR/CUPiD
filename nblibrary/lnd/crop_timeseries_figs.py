"""
For making timeseries figures of CLM crop outputs
"""
from __future__ import annotations

from matplotlib import pyplot as plt

EARTHSTAT_RES_TO_PLOT = "f09"


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


def _plot_clm_cases(case_list, opts, var_details, crop):
    for c, case in enumerate(case_list):

        crop_data_ts = var_details["function"](crop, case)

        # Plot data
        crop_data_ts *= var_details["conversion_factor"]
        crop_data_ts.name = var_details["da_name"]
        crop_data_ts.attrs["units"] = var_details["ctsm_units"]

        # Change line style for one line that overlaps another for some crops
        # TODO: Optionally define linestyle for each case in config.yml
        if "clm6_crop_032_nomaxlaitrig" in opts["case_name_list"] and opts[
            "case_name_list"
        ][c].endswith("clm6_crop_032_nmlt_phaseparams"):
            linestyle = "--"
        else:
            linestyle = "-"

            # Plot
        crop_data_ts.plot(linestyle=linestyle)


def _get_clm_yield(crop, case):
    # Do NOT use crop_cft_yield here, because you need to sum across cft and pft before
    # doing the division
    crop_prod_ts = case.cft_ds["crop_cft_prod"].sel(crop=crop).sum(dim=["cft", "pft"])
    crop_area_ts = case.cft_ds["crop_cft_area"].sel(crop=crop).sum(dim=["cft", "pft"])
    crop_yield_ts = crop_prod_ts / crop_area_ts
    return crop_yield_ts


def _get_clm_prod(crop, case):
    return case.cft_ds["crop_cft_prod"].sel(crop=crop).sum(dim=["cft", "pft"])


def _get_clm_area(crop, case):
    return case.cft_ds["crop_cft_area"].sel(crop=crop).sum(dim=["cft", "pft"])


def finish_fig(opts, fig_opts, fig, *, incl_obs=True):
    plt.subplots_adjust(wspace=fig_opts["wspace"], hspace=fig_opts["hspace"])
    labels = opts["case_legend_list"].copy()
    if incl_obs:
        labels += ["FAOSTAT", f"EarthStat {EARTHSTAT_RES_TO_PLOT}"]
    fig.legend(
        labels=labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=3,
        bbox_transform=fig.transFigure,
    )
    fig.suptitle(fig_opts["title"], fontsize="x-large", fontweight="bold")
    plt.show()


def _plot_faostat(fao_yield_world, crop, ax, time_da, ctsm_units):
    faostat_units = fao_yield_world["Unit"].iloc[0]
    if faostat_units != ctsm_units:
        raise RuntimeError(
            f"CTSM units ({ctsm_units}) do not match FAOSTAT units ({faostat_units})",
        )
    fao_yield_world_thiscrop = fao_yield_world.query(f"Crop == '{crop}'")
    ax.plot(
        time_da,
        fao_yield_world_thiscrop["Value"].values,
        "-k",
    )


def _plot_earthstat(which, earthstat_data, crop, ax):
    if which == "yield":
        earthstat_prod = earthstat_data[EARTHSTAT_RES_TO_PLOT].get_data("prod", crop)
        earthstat_area = earthstat_data[EARTHSTAT_RES_TO_PLOT].get_data("area", crop)
        if earthstat_prod is None or earthstat_area is None:
            return
        earthstat_var = earthstat_prod.sum(dim=["lat", "lon"]) / earthstat_area.sum(
            dim=["lat", "lon"],
        )
    else:
        earthstat_var = earthstat_data[EARTHSTAT_RES_TO_PLOT].get_data(which, crop)
        if earthstat_var is None:
            return
        earthstat_var = earthstat_var.sum(dim=["lat", "lon"])

    ax.plot(
        earthstat_var["time"],
        earthstat_var.values,
        "0.5",  # gray
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


def main(which, earthstat_data, case_list, fao_data, opts):
    """
    For making timeseries figures of CLM crop outputs
    """

    # Get figure layout info
    fig_opts, fig, axes = setup_fig(opts)

    # This .copy() prevents spooky side effects from operational persistence
    fao_data_world = fao_data.copy().query("Area == 'World'")

    # Set up for the variable we want
    # TODO: Increase robustness of unit conversion: Check that it really is, e.g., g/m2 to start
    # with.
    var_details = _get_var_details(which, fao_data_world)
    fig_opts["title"] = "Global " + var_details["da_name"].lower()

    for i, crop in enumerate(opts["crops_to_include"]):
        ax = axes.ravel()[i]
        plt.sca(ax)

        # Plot case data
        _plot_clm_cases(case_list, opts, var_details, crop)

        # Plot FAOSTAT data
        _plot_faostat(
            fao_data_world,
            crop,
            ax,
            case_list[0].cft_ds["time"],
            var_details["ctsm_units"],
        )

        # Plot EarthStat data
        _plot_earthstat(which, earthstat_data, crop, ax)

        # Finish plot
        ax.set_title(crop)
        plt.xlabel("")

    finish_fig(opts, fig_opts, fig)
