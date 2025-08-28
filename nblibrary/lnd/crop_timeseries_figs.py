"""
For making timeseries figures of CLM crop outputs
"""
from __future__ import annotations

from time import time

from matplotlib import pyplot as plt

EARTHSTAT_RES_TO_PLOT = "f09"


def main(earthstat_data, case_list, fao_yield, opts):
    """
    For making timeseries figures of CLM crop outputs
    """

    if opts["verbose"]:
        start = time()

    # Get figure layout info
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

    fao_yield_world = fao_yield.query("Area == 'World'")

    earthstat_ds_to_plot = earthstat_data[EARTHSTAT_RES_TO_PLOT]

    for i, crop in enumerate(opts["crops_to_include"]):
        ax = axes.ravel()[i]
        plt.sca(ax)

        # Plot case data
        for c, case in enumerate(case_list):

            # Do NOT use crop_cft_yield here, because you need to sum across cft and pft before doing the division
            crop_prod_ts = (
                case.cft_ds["crop_cft_prod"].sel(crop=crop).sum(dim=["cft", "pft"])
            )
            crop_area_ts = (
                case.cft_ds["crop_cft_area"].sel(crop=crop).sum(dim=["cft", "pft"])
            )
            crop_yield_ts = crop_prod_ts / crop_area_ts

            # Plot data
            # TODO: Increase robustness of unit conversion: Check that it really is
            # g/m2 to start with.
            crop_yield_ts *= 1e-6 * 1e4  # Convert g/m2 to tons/ha
            crop_yield_ts.name = "Yield"
            ctsm_units = "t/ha"
            crop_yield_ts.attrs["units"] = ctsm_units

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

        # Plot FAOSTAT data
        faostat_units = fao_yield_world["Unit"].iloc[0]
        if faostat_units != ctsm_units:
            raise RuntimeError(
                f"CTSM units ({ctsm_units}) do not match FAOSTAT units ({faostat_units})",
            )
        fao_yield_world_thiscrop = fao_yield_world.query(f"Crop == '{crop}'")
        ax.plot(
            crop_yield_ts.time,
            fao_yield_world_thiscrop["Value"].values,
            "-k",
        )

        # Plot EarthStat data
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

        # Finish plot
        ax.set_title(crop)
        plt.xlabel("")

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

    if opts["verbose"]:
        end = time()
        print(f"Time series plots took {int(end - start)} s")
