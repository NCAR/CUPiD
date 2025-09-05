"""
A module for plotting utilties shared amongst the lnd/ Python
"""

from __future__ import annotations

from matplotlib import pyplot as plt
import numpy as np
import cartopy.crs as ccrs
import xarray as xr


def cut_off_antarctica(da, antarctica_border=-60):
    """
    Cut off the bottom of the map, from latitude antarctica_border south
    """
    da = da.sel(lat=slice(antarctica_border, 90))
    return da


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


class ResultsMaps:
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
