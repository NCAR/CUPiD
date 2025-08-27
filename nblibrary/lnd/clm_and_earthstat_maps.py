"""
clm_and_earthstat_maps() function intended for (re)use in Global_crop_yield_compare_obs.ipynb
"""
from __future__ import annotations

from time import time
from types import ModuleType

import cartopy.crs as ccrs
import numpy as np
import xarray as xr
from caselist import CaseList
from earthstat import EarthStat
from matplotlib import pyplot as plt
from plotting_utils import cut_off_antarctica


class Results:
    """
    For holding a dict of map DataArrays, plus some ancillary information and functions
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, layout, *, symmetric_0=False):
        self.result_dict = {}
        self.vmin = np.inf
        self.vmax = -np.inf

        self.layout = layout
        self.symmetric_0 = symmetric_0
        if self.symmetric_0:
            self.cmap = "coolwarm"
        else:
            self.cmap = "viridis"

        self.fig, self.axes = plt.subplots(
            nrows=self.layout["nrows"],
            ncols=self.layout["ncols"],
            figsize=self.layout["figsize"],
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

    def vrange(self):
        """
        Return list representing colorbar range
        """
        vmin = self.vmin
        vmax = self.vmax

        # Set upper and lower to same value, with lower the opposite left of zero
        if self.symmetric_0:
            vmax = max(abs(vmin), abs(vmax))
            vmin = -vmax

        return [vmin, vmax]

    def plot(self, *, case_name_list: list, crop: str):
        """
        Fill out figure with all subplots, colorbar, etc.
        """
        for i, ax in enumerate(self.axes.ravel()):
            try:
                case_name = case_name_list[i]
            except IndexError:
                ax.set_visible(False)
                continue

            im = _map_subplot(
                self[case_name],
                ax,
                self.vrange(),
                case_name,
                cmap=self.cmap,
            )

        _mapfig_finishup(self.fig, im, self[case_name], crop, self.layout)


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


def _get_clm_ds_result_yield(ds):
    cft_var = ds["YIELD_ANN"].mean(dim="time")
    ds = ds.mean(dim="time")
    ds["result"] = cft_var.weighted(ds["pfts1d_wtgcell"]).mean(
        dim="cft",
    )
    return ds


def _get_clm_ds_result_prod(ds):
    cft_area = ds["pfts1d_gridcellarea"] * ds["pfts1d_wtgcell"]
    cft_area *= 1e6  # Convert km2 to m2
    cft_prod = ds["YIELD_ANN"] * cft_area
    ds["result"] = cft_prod.sum(dim="cft").mean(dim="time")
    return ds


def _get_clm_map(which, utils, crop, case):
    """
    Get yield map from CLM
    """

    # Define some things based on what map we want
    if which == "yield":
        get_clm_ds_result = _get_clm_ds_result_yield
        units = "tons / ha"
        conversion_factor = 1e-6 * 1e4  # Convert g/m2 to t/ha
        name = "Yield"
    elif which == "prod":
        get_clm_ds_result = _get_clm_ds_result_prod
        units = "Mt"
        conversion_factor = 1e-6 * 1e-6  # Convert g to Mt
        name = "Production"
    else:
        raise NotImplementedError(
            f"_get_clm_map() doesn't work for which='{which}'",
        )

    # Extract the data
    ds = case.cft_ds.sel(cft=case.crop_list[crop].pft_nums)
    ds = ds.drop_vars(["date_written", "time_written"])
    ds = get_clm_ds_result(ds)

    # Grid the data
    map_clm = utils.grid_one_variable(ds, "result")
    map_clm = utils.lon_pm2idl(map_clm)

    # Finish up
    map_clm *= conversion_factor
    map_clm.name = name
    map_clm.attrs["units"] = units

    return map_clm


def clm_and_earthstat_maps(
    *,
    which: str,
    case_list: CaseList,
    earthstat_data: EarthStat,
    crops_to_include: list,
    utils: ModuleType,
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

        # Set up for maps of CLM
        results_clm = Results(case_list.mapfig_layout)

        # Set up for maps of CLM minus EarthStat
        results_diff = Results(case_list.mapfig_layout, symmetric_0=True)

        # Get maps and colorbar min/max (the latter should cover total range across ALL cases)
        for i, case in enumerate(case_list):
            case_name = case_list.names[i]

            # Get CLM map
            results_clm[case_name] = cut_off_antarctica(
                _get_clm_map(which, utils, crop, case),
            )

            # Get observed map
            map_obs = earthstat_data.get_map(
                which,
                case.cft_ds.attrs["resolution"].name,
                crop,
                case_name,
            )
            if map_obs is None:
                continue

            # Get difference map
            map_obs = utils.lon_pm2idl(map_obs)
            results_diff[case_name] = _get_difference_map(
                map_obs,
                results_clm[case_name],
            )
            results_diff[
                case_name
            ].name = f"{results_clm[case_name].name} difference, CLM minus EarthStat"
            results_diff[case_name].attrs["units"] = results_clm[case_name].units

        # Plot
        results_clm.plot(case_name_list=case_list.names, crop=crop)
        results_diff.plot(case_name_list=case_list.names, crop=crop)

        timer.end(crop, verbose)

    timer.end_all(verbose)
