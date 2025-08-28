"""
For making timeseries figures of CLM crop outputs
"""
from __future__ import annotations

from matplotlib import pyplot as plt

EARTHSTAT_RES_TO_PLOT = "f09"


def _setup_fig(opts):
    n_crops_to_include = len(opts["crops_to_include"])
    if 5 <= n_crops_to_include <= 6:
        nrows = 2
        ncols = 3
        height = 10.5
        width = 15
        hspace = 0.25
        wspace = 0.35
    else:
        raise RuntimeError(f"Specify figure layout for Ncrops=={n_crops_to_include}")
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(width, height))
    return hspace, wspace, fig, axes


def _plot_clm_cases(case_list, opts, var_details, crop):
    for c, case in enumerate(case_list):
        # Do NOT use crop_cft_yield here, because you need to sum across cft and pft before
        # doing the division
        crop_prod_ts = (
            case.cft_ds["crop_cft_prod"].sel(crop=crop).sum(dim=["cft", "pft"])
        )
        crop_area_ts = (
            case.cft_ds["crop_cft_area"].sel(crop=crop).sum(dim=["cft", "pft"])
        )
        crop_yield_ts = crop_prod_ts / crop_area_ts

        # Plot data
        crop_yield_ts *= var_details["conversion_factor"]
        crop_yield_ts.name = var_details["da_name"]
        crop_yield_ts.attrs["units"] = var_details["ctsm_units"]

        # Change line style for one line that overlaps another for some crops
        # TODO: Optionally define linestyle for each case in config.yml
        if "clm6_crop_032_nomaxlaitrig" in opts["case_name_list"] and opts[
            "case_name_list"
        ][c].endswith("clm6_crop_032_nmlt_phaseparams"):
            linestyle = "--"
        else:
            linestyle = "-"

            # Plot
        crop_yield_ts.plot(linestyle=linestyle)


def _finish_fig(opts, hspace, wspace, fig):
    plt.subplots_adjust(wspace=wspace, hspace=hspace)
    fig.legend(
        labels=opts["case_legend_list"]
        + ["FAOSTAT", f"EarthStat {EARTHSTAT_RES_TO_PLOT}"],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=3,
        bbox_transform=fig.transFigure,
    )
    fig.suptitle("Global yield", fontsize="x-large", fontweight="bold")
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


def _plot_earthstat(earthstat_data, earthstat_ds_to_plot, crop, ax):
    earthstat_crop_idx = None
    try:
        earthstat_crop_idx = earthstat_data.crops.index(crop)
    except ValueError:
        print(f"{crop} not in EarthStat res {EARTHSTAT_RES_TO_PLOT}; skipping")
    if earthstat_crop_idx is not None:
        earthstat_crop_ds = earthstat_ds_to_plot.isel(crop=earthstat_crop_idx)
        earthstat_area_da_tyx = earthstat_crop_ds["HarvestArea"]
        earthstat_prod_da_tyx = earthstat_crop_ds["Production"]
        earthstat_prod_da_t = earthstat_prod_da_tyx.sum(dim=["lat", "lon"])
        earthstat_area_da_t = earthstat_area_da_tyx.sum(dim=["lat", "lon"])
        earthstat_yield_da_t = earthstat_prod_da_t / earthstat_area_da_t
        ax.plot(
            earthstat_yield_da_t["time"],
            earthstat_yield_da_t.values,
            "0.5",  # gray
        )


def main(earthstat_data, case_list, fao_yield, opts):
    """
    For making timeseries figures of CLM crop outputs
    """

    # Get figure layout info
    hspace, wspace, fig, axes = _setup_fig(opts)

    fao_yield_world = fao_yield.query("Area == 'World'")

    earthstat_ds_to_plot = earthstat_data[EARTHSTAT_RES_TO_PLOT]

    var_details = {}
    var_details["da_name"] = "Yield"
    var_details["ctsm_units"] = "t/ha"
    # TODO: Increase robustness of unit conversion: Check that it really is g/m2 to start with.
    var_details["conversion_factor"] = 1e-6 * 1e4  # Convert g/m2 to tons/ha

    for i, crop in enumerate(opts["crops_to_include"]):
        ax = axes.ravel()[i]
        plt.sca(ax)

        # Plot case data
        _plot_clm_cases(case_list, opts, var_details, crop)

        # Plot FAOSTAT data
        _plot_faostat(
            fao_yield_world,
            crop,
            ax,
            case_list[0].cft_ds["time"],
            var_details["ctsm_units"],
        )

        # Plot EarthStat data
        _plot_earthstat(earthstat_data, earthstat_ds_to_plot, crop, ax)

        # Finish plot
        ax.set_title(crop)
        plt.xlabel("")

    _finish_fig(opts, hspace, wspace, fig)
