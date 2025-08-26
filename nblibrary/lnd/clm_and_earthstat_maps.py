"""
clm_and_earthstat_maps() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

from collections.abc import Callable
from time import time

import cartopy.crs as ccrs
import numpy as np
from matplotlib import pyplot as plt


def _cut_off_antarctica(da, antarctica_border=-60):
    """
    Cut off the bottom of the map, from latitude antarctica_border south
    """
    da = da.sel(lat=slice(antarctica_border, 90))
    return da


def _get_difference_map(da0, da1):
    """
    Get difference between two maps (da1-da0), ensuring sizes/coordinates match
    """
    if not all(da1.sizes[d] == da0.sizes[d] for d in da1.dims):
        raise RuntimeError(
            f"Size mismatch between da1 ({da1.sizes}) and da0 ({da0.sizes})",
        )
    da_diff = da1 - da0
    if not all(da1.sizes[d] == da_diff.sizes[d] for d in da1.dims):
        raise RuntimeError(
            f"Size mismatch between da1 ({da1.sizes}) and map_diff ({da_diff.sizes})",
        )
    return da_diff


def _map_subplot(da, ax, vrange, title, cmap="viridis"):
    """
    Plot a map in a subplot
    """
    plt.sca(ax)
    im = da.plot(
        ax=ax,
        transform=ccrs.PlateCarree(),
        vmin=vrange[0],
        vmax=vrange[1],
        add_colorbar=False,
        cmap=cmap,
    )
    ax.coastlines(linewidth=0.5)
    plt.title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")

    return im


def _mapfig_finishup(fig, im, da, crop, layout):
    """
    Finish up a figure with map subplots
    """
    fig.suptitle(crop, fontsize="x-large", fontweight="bold")
    fig.subplots_adjust(
        top=layout["subplots_adjust_colorbar_top"],
        bottom=layout["subplots_adjust_colorbar_bottom"],
    )
    cbar_ax = fig.add_axes(rect=layout["cbar_ax_rect"])
    fig.colorbar(
        im,
        cax=cbar_ax,
        orientation="horizontal",
        label=f"{da.name} ({da.attrs['units']})",
    )
    fig.show()


def clm_and_earthstat_maps(
    *,
    case_list: list,
    case_name_list: list,
    earthstat: dict,
    crops_to_include: list,
    earthstat_crop_list: list,
    layout: dict,
    grid_one_variable: Callable,
    lon_pm2idl: Callable,
    verbose: bool,
):
    """
    For each crop, make two figures:
    1. With subplots showing mean CLM map for each case
    2. With subplots showing difference between mean CLM and EarthStat maps for each case
    """
    start_all = time()
    for crop in crops_to_include:
        fig_clm, axes_clm = plt.subplots(
            nrows=layout["nrows"],
            ncols=layout["ncols"],
            figsize=layout["figsize"],
            subplot_kw={"projection": ccrs.PlateCarree()},
        )
        fig_diff, axes_diff = plt.subplots(
            nrows=layout["nrows"],
            ncols=layout["ncols"],
            figsize=layout["figsize"],
            subplot_kw={"projection": ccrs.PlateCarree()},
        )
        start = time()
        if verbose:
            print(crop)

        # Set up for maps of CLM yield
        vmin_clm = np.inf
        vmax_clm = -np.inf
        result_dict_clm = {}

        # Set up for maps of CLM minus EarthStat yield
        vmin_diff = np.inf
        vmax_diff = -np.inf
        result_dict_diff = {}

        # Get maps and colorbar min/max (the latter should cover total range across ALL cases)
        for i, case in enumerate(case_list):
            case_name = case_name_list[i]

            # Get CLM yield map
            ds = case.cft_ds.sel(cft=case.crop_list[crop].pft_nums)
            ds = ds.drop_vars(["date_written", "time_written"])
            cft_yield = ds["YIELD_ANN"].mean(dim="time")
            ds = ds.mean(dim="time")
            ds["wtd_yield_across_cfts"] = cft_yield.weighted(
                ds["pfts1d_wtgcell"],
            ).mean(
                dim="cft",
            )
            map_clm = grid_one_variable(ds, "wtd_yield_across_cfts")
            map_clm = lon_pm2idl(map_clm)
            map_clm *= 1e-6 * 1e4  # Convert g/m2 to t/ha
            map_clm.name = "Yield"
            map_clm.attrs["units"] = "tons / ha"

            # Save CLM yield map
            map_clm = _cut_off_antarctica(map_clm)
            result_dict_clm[case_name] = map_clm
            vmin_clm = min(vmin_clm, np.nanmin(map_clm.values))
            vmax_clm = max(vmax_clm, np.nanmax(map_clm.values))
            vrange_clm = [vmin_clm, vmax_clm]

            # Get observed yield map
            case_res = case.cft_ds.attrs["resolution"].name
            try:
                earthstat_crop_idx = earthstat_crop_list.index(crop)
            except ValueError:
                print(f"{crop} not in EarthStat res {case_res}; skipping")
                continue
            try:
                earthstat_ds = earthstat[case_res]
            except KeyError:
                print(f"{case_res} not in EarthStat; skipping {case_name}")
                continue
            map_obs = (
                earthstat_ds["Yield"].isel(crop=earthstat_crop_idx).mean(dim="time")
            )
            map_obs = _cut_off_antarctica(map_obs)

            # Get yield difference map
            map_diff = _get_difference_map(map_obs, map_clm)
            map_diff.name = "Yield difference, CLM minus EarthStat"
            map_diff.attrs["units"] = "tons / ha"

            # Save yield difference map
            result_dict_diff[case_name] = map_diff
            vmin_diff = min(vmin_diff, np.nanmin(map_diff.values))
            vmax_diff = max(vmax_diff, np.nanmax(map_diff.values))

        # Set upper and lower limits of difference colorbar to the same value
        vmax_diff = max(abs(vmin_diff), abs(vmax_diff))
        vmin_diff = -vmax_diff
        vrange_diff = [vmin_diff, vmax_diff]

        # Plot
        for i, ax_clm in enumerate(axes_clm.ravel()):
            try:
                case = case_list[i]
            except IndexError:
                ax_clm.set_visible(False)
                continue
            case_name = case_name_list[i]

            result_clm = result_dict_clm[case_name]
            im_clm = _map_subplot(result_clm, ax_clm, vrange_clm, case_name)

            ax_diff = axes_diff.ravel()[i]
            result_diff = result_dict_diff[case_name]
            im_diff = _map_subplot(
                result_diff,
                ax_diff,
                vrange_diff,
                case_name,
                cmap="coolwarm",
            )

        # Finish up
        _mapfig_finishup(fig_clm, im_clm, result_clm, crop, layout)
        _mapfig_finishup(fig_diff, im_diff, result_diff, crop, layout)
        if verbose:
            end = time()
            print(f"{crop} took {end - start} s")

    if verbose:
        end_all = time()
        print(f"Maps took {int(end_all - start_all)} s.")
