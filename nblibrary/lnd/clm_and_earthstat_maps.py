"""
clm_and_earthstat_maps() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

from collections.abc import Callable
from time import time

import cartopy.crs as ccrs
import numpy as np
import xarray as xr
from matplotlib import pyplot as plt


class Results:
    """
    For holding a dict of map DataArrays and some ancillary information
    """

    def __init__(self, layout):
        self.result_dict = {}
        self.vmin = np.inf
        self.vmax = -np.inf

        self.fig, self.axes = plt.subplots(
            nrows=layout["nrows"],
            ncols=layout["ncols"],
            figsize=layout["figsize"],
            subplot_kw={"projection": ccrs.PlateCarree()},
        )

    def __getitem__(self, key):
        """instance[key] syntax should return corresponding value in result_dict"""
        return self.result_dict[key]

    def __setitem__(self, key: str, value: xr.DataArray):
        """instance[key]=value syntax should set corresponding key=value in result_dict"""
        self.vmin = min(self.vmin, np.nanmin(value.values))
        self.vmax = max(self.vmax, np.nanmax(value.values))
        self.result_dict[key] = value

    def vrange(self, *, symmetric_0=False):
        """
        Return list representing colorbar range
        """
        vmin = self.vmin
        vmax = self.vmax

        # Set upper and lower to same value, with lower the opposite left of zero
        if symmetric_0:
            vmax = max(abs(vmin), abs(vmax))
            vmin = -vmax

        return [vmin, vmax]


class Timing:
    """
    For holding, calculating, and printing info about clm_and_earthstat_maps() timing
    """

    def __init__(self):
        self._start_all = time()
        self._start = None

    def start(self):
        """
        Start timer for one loop
        """
        self._start = time()

    def end(self, crop, verbose):
        """
        End timer for one loop
        """
        end = time()
        if verbose:
            print(f"{crop} took {end - self._start} s")

    def end_all(self, verbose):
        """
        End timer across all loops
        """
        end_all = time()
        if verbose:
            print(f"Maps took {int(end_all - self._start_all)} s.")


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


def _get_clm_yield_map(grid_one_variable, lon_pm2idl, crop, case):
    """
    Get yield map from CLM
    """
    ds = case.cft_ds.sel(cft=case.crop_list[crop].pft_nums)
    ds = ds.drop_vars(["date_written", "time_written"])
    cft_yield = ds["YIELD_ANN"].mean(dim="time")
    ds = ds.mean(dim="time")
    ds["wtd_yield_across_cfts"] = cft_yield.weighted(ds["pfts1d_wtgcell"]).mean(
        dim="cft",
    )
    map_clm = grid_one_variable(ds, "wtd_yield_across_cfts")
    map_clm = lon_pm2idl(map_clm)
    map_clm *= 1e-6 * 1e4  # Convert g/m2 to t/ha
    map_clm.name = "Yield"
    map_clm.attrs["units"] = "tons / ha"
    return map_clm


def _get_earthstat_yield_map(case, earthstat_crop_list, earthstat, crop, case_name):
    """
    Get yield map from EarthStat
    """
    case_res = case.cft_ds.attrs["resolution"].name
    map_obs = None
    try:
        earthstat_crop_idx = earthstat_crop_list.index(crop)
    except ValueError:
        print(f"{crop} not in EarthStat res {case_res}; skipping")
        return map_obs
    try:
        earthstat_ds = earthstat[case_res]
    except KeyError:
        print(f"{case_res} not in EarthStat; skipping {case_name}")
        return map_obs
    map_obs = earthstat_ds["Yield"].isel(crop=earthstat_crop_idx).mean(dim="time")
    map_obs = _cut_off_antarctica(map_obs)
    return map_obs


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
    timer = Timing()
    for crop in crops_to_include:
        timer.start()
        if verbose:
            print(crop)

        # Set up for maps of CLM yield
        results_clm = Results(layout)

        # Set up for maps of CLM minus EarthStat yield
        results_diff = Results(layout)

        # Get maps and colorbar min/max (the latter should cover total range across ALL cases)
        for i, case in enumerate(case_list):
            case_name = case_name_list[i]

            # Get CLM yield map
            results_clm[case_name] = _cut_off_antarctica(
                _get_clm_yield_map(grid_one_variable, lon_pm2idl, crop, case),
            )

            # Get observed yield map
            map_obs = _get_earthstat_yield_map(
                case,
                earthstat_crop_list,
                earthstat,
                crop,
                case_name,
            )
            if map_obs is None:
                continue

            # Get yield difference map
            results_diff[case_name] = _get_difference_map(
                map_obs,
                results_clm[case_name],
            )
            results_diff[case_name].name = "Yield difference, CLM minus EarthStat"
            results_diff[case_name].attrs["units"] = "tons / ha"

        # Plot
        for i, ax_clm in enumerate(results_clm.axes.ravel()):
            try:
                case_name = case_name_list[i]
            except IndexError:
                ax_clm.set_visible(False)
                continue

            im_clm = _map_subplot(
                results_clm[case_name],
                ax_clm,
                results_clm.vrange(),
                case_name,
            )

            im_diff = _map_subplot(
                results_diff[case_name],
                results_diff.axes.ravel()[i],
                results_diff.vrange(symmetric_0=True),
                case_name,
                cmap="coolwarm",
            )

        # Finish up
        _mapfig_finishup(results_clm.fig, im_clm, results_clm[case_name], crop, layout)
        _mapfig_finishup(
            results_diff.fig,
            im_diff,
            results_diff[case_name],
            crop,
            layout,
        )
        timer.end(crop, verbose)

    timer.end_all(verbose)
