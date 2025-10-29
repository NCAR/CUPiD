"""
A module for plotting utilties shared amongst the lnd/ Python
"""
from __future__ import annotations

import cartopy.crs as ccrs
import numpy as np
import xarray as xr
from matplotlib import pyplot as plt


def get_difference_map(da0, da1):
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


def _cut_off_antarctica(da, antarctica_border=-60):
    """
    Cut off the bottom of the map, from latitude antarctica_border south
    """
    da = da.sel(lat=slice(antarctica_border, 90))
    return da


def _mapfig_finishup(fig, im, da, crop, layout):
    """
    Finish up a figure with map subplots
    """
    suptitle = f"{da.name}: {crop}"
    fig.suptitle(suptitle, fontsize="x-large", fontweight="bold")
    fig.subplots_adjust(
        top=layout["subplots_adjust_colorbar_top"] - 0.04,
        bottom=layout["subplots_adjust_colorbar_bottom"],
    )
    cbar_ax = fig.add_axes(rect=layout["cbar_ax_rect"])
    fig.colorbar(
        im,
        cax=cbar_ax,
        orientation="horizontal",
        label=da.attrs["units"],
    )
    fig.show()


class ResultsMaps:
    """
    For holding a dict of map DataArrays, plus some ancillary information and functions
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        *,
        symmetric_0=False,
        vrange=None,
        cut_off_antarctica=True,
    ):
        self.result_dict = {}
        self.cut_off_antarctica = cut_off_antarctica

        # Default color map
        self.cmap = "viridis"

        # Empty figure layout stuff
        self.layout = {}
        self.axes = None
        self.fig = None

        # If vrange isn't provided, it will be calculated automatically
        self._vrange = vrange
        if not self._vrange:
            self.vmin = np.inf
            self.vmax = -np.inf
            self.symmetric_0 = symmetric_0
            if self.symmetric_0:
                self.cmap = "coolwarm"

        # Per-plot vranges will override self._vrange if any is ever provided
        self.plot_vranges = {}

    def __getitem__(self, key):
        """instance[key] syntax should return corresponding value in result_dict"""
        return self.result_dict[key]

    def __setitem__(self, key: str, value: xr.DataArray):
        """instance[key]=value syntax should set corresponding key=value in result_dict"""
        if not self._vrange:
            self.vmin = min(self.vmin, np.nanmin(value.values))
            self.vmax = max(self.vmax, np.nanmax(value.values))
        self.result_dict[key] = value
        self.plot_vranges[key] = None

    def __len__(self):
        return len(self.result_dict)

    def _get_mapfig_layout(self):
        """
        Get map figure layout info
        """

        self.layout["nrows"] = int(np.ceil(len(self) / 2))
        self.layout["subplots_adjust_colorbar_top"] = 0.95
        self.layout["subplots_adjust_colorbar_bottom"] = 0.2
        self.layout["cbar_ax_rect"] = (0.2, 0.15, 0.6, 0.03)

        height = 3.75 * self.layout["nrows"]
        width = 15
        self.layout["figsize"] = (width, height)
        self.layout["ncols"] = 2
        self.layout["hspace"] = 0
        self.layout["wspace"] = 0

    def vrange(self):
        """
        Return list representing colorbar range
        """
        if self._vrange:
            return self._vrange

        vmin = self.vmin
        vmax = self.vmax

        # Set upper and lower to same value, with lower the opposite left of zero
        if self.symmetric_0:
            vmax = max(abs(vmin), abs(vmax))
            vmin = -vmax

        return [vmin, vmax]

    def plot(self, *, subplot_title_list: list, crop: str):
        """
        Fill out figure with all subplots, colorbar, etc.
        """
        self._get_mapfig_layout()

        self.fig, self.axes = plt.subplots(
            nrows=self.layout["nrows"],
            ncols=self.layout["ncols"],
            figsize=self.layout["figsize"],
            subplot_kw={"projection": ccrs.PlateCarree()},
        )

        for i, ax in enumerate(self.axes.ravel()):
            try:
                this_subplot = subplot_title_list[i]
            except IndexError:
                ax.set_visible(False)
                continue

            # Use per-plot color range (or entire plot color range) if any is provided
            if any(v is None for v in self.plot_vranges.values()):
                if self.plot_vranges[this_subplot]:
                    vrange = self.plot_vranges[this_subplot]
                else:
                    vrange = [None, None]
            else:
                vrange = self.vrange

            im = self._map_subplot(
                ax,
                this_subplot,
                vrange,
            )

        _mapfig_finishup(self.fig, im, self[this_subplot], crop, self.layout)

    def _map_subplot(self, ax, case_name, vrange):
        """
        Plot a map in a subplot
        """

        da = self[case_name].copy()

        if self.cut_off_antarctica:
            da = _cut_off_antarctica(da)

        plt.sca(ax)
        im = da.plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            vmin=vrange[0],
            vmax=vrange[1],
            add_colorbar=False,
            cmap=self.cmap,
        )
        ax.coastlines(linewidth=0.5)
        plt.title(case_name)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")

        return im
