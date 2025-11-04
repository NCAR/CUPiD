"""
A module for plotting utilties shared amongst the lnd/ Python
"""
from __future__ import annotations

import warnings

import cartopy.crs as ccrs
import numpy as np
import xarray as xr
from matplotlib import pyplot as plt

DEFAULT_CMAP_SEQ = "viridis"
DEFAULT_CMAP_DIV = "coolwarm"
DEFAULT_CMAP_DIV_DIFFOFABSDIFF = "PiYG_r"


def check_grid_match(grid0, grid1, tol=0):
    """
    Check whether latitude or longitude values match
    """
    if grid0.shape != grid1.shape:
        return False, None

    if hasattr(grid0, "values"):
        grid0 = grid0.values
    if hasattr(grid1, "values"):
        grid1 = grid1.values

    abs_diff = np.abs(grid1 - grid0)
    if np.any(np.isnan(abs_diff)):
        if np.any(np.isnan(grid0) != np.isnan(grid1)):
            warnings.warn("NaN(s) in grid don't match", RuntimeWarning)
            return False, None
        warnings.warn("NaN(s) in grid", RuntimeWarning)

    max_abs_diff = np.nanmax(abs_diff)
    match = max_abs_diff < tol

    return match, max_abs_diff


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
    first = da["lat"].isel(lat=0)
    last = da["lat"].isel(lat=-1)
    if first < last:
        lat_slice = slice(antarctica_border, 90)
    else:
        lat_slice = slice(90, antarctica_border)
    da = da.sel(lat=lat_slice)
    return da


def _mapfig_finishup(*, fig, im, da, suptitle, layout, one_colorbar):
    """
    Finish up a figure with map subplots
    """
    fig.suptitle(suptitle, fontsize="x-large", fontweight="bold")

    if one_colorbar:
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
    else:
        fig.subplots_adjust(top=0.96)


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

        # Default color map is assumed to be sequential. This applies to all subplots if
        # ResultsMaps.plot(..., key_plot=None). Otherwise, applies only to the key plot;
        # other plots will get diverging colormap DEFAULT_CMAP_DIV.
        self.cmap = DEFAULT_CMAP_SEQ

        # Empty figure layout stuff
        self.layout = {}
        self.axes = None
        self.fig = None

        # If vrange isn't provided, it will be calculated automatically
        self._vrange = vrange
        self.symmetric_0 = symmetric_0
        if not self._vrange:
            self.vmin = np.inf
            self.vmax = -np.inf
            if self.symmetric_0:
                self.cmap = DEFAULT_CMAP_DIV

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

    def _get_mapfig_layout(self, one_colorbar):
        """
        Get map figure layout info
        """

        self.layout["ncols"] = 2
        self.layout["nrows"] = int(np.ceil(len(self) / self.layout["ncols"]))

        if one_colorbar:
            self.layout["subplots_adjust_colorbar_top"] = 0.95
            self.layout["subplots_adjust_colorbar_bottom"] = 0.2
            self.layout["cbar_ax_rect"] = (0.2, 0.15, 0.6, 0.03)
            height = 3.75 * self.layout["nrows"]
        else:
            height = 4.85 * self.layout["nrows"]

        width = 15
        self.layout["figsize"] = (width, height)

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

    def plot(
        self,
        *,
        subplot_title_list: list,
        suptitle: str,
        one_colorbar: bool = False,
        fig_path: str = None,
        key_plot: str = None,
    ):
        """
        Fill out figure with all subplots, colorbar, etc.
        """
        if one_colorbar and key_plot is not None:
            warnings.warn("Ignoring one_colorbar=True because key_plot is not None")
            one_colorbar = False

        self._get_mapfig_layout(one_colorbar)

        self.fig, self.axes = plt.subplots(
            nrows=self.layout["nrows"],
            ncols=self.layout["ncols"],
            figsize=self.layout["figsize"],
            subplot_kw={"projection": ccrs.PlateCarree()},
        )

        # Store image objects for each subplot
        images = {}

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
                ax=ax,
                case_name=this_subplot,
                vrange=vrange,
                one_colorbar=one_colorbar,
                key_case=key_plot,
            )

            # Store the image object
            images[this_subplot] = im

        _mapfig_finishup(
            fig=self.fig,
            im=im,
            da=self[this_subplot],
            suptitle=suptitle,
            layout=self.layout,
            one_colorbar=one_colorbar,
        )

        if key_plot is not None:
            # Make all non-key plot colorbars match
            self._update_non_key_colorbars(subplot_title_list, key_plot, images)

        if fig_path is None:
            self.fig.show()
        else:
            plt.savefig(fig_path, dpi=150)
            plt.close()

    def _update_non_key_colorbars(self, subplot_title_list, key_plot, images):
        """
        Make all non-key plot colorbars match
        """
        # Find the most extreme absolute value across all non-key plots
        max_abs_val = 0
        for this_subplot in subplot_title_list:
            if this_subplot == key_plot:
                continue
            da_vals = self[this_subplot].values
            max_abs_val = max(max_abs_val, np.nanmax(np.abs(da_vals)))

        # Update all non-key plot color limits
        for i, this_subplot in enumerate(subplot_title_list):
            if this_subplot == key_plot:
                continue
            # Update the image object's color limits
            if this_subplot in images:
                images[this_subplot].set_clim(-max_abs_val, max_abs_val)
                # Update the colorbar if it exists
                if (
                    hasattr(images[this_subplot], "colorbar")
                    and images[this_subplot].colorbar is not None
                ):
                    images[this_subplot].colorbar.update_normal(images[this_subplot])

    def _map_subplot(self, *, ax, case_name, vrange, one_colorbar, key_case):
        """
        Plot a map in a subplot
        """
        title = case_name
        cmap = self.cmap

        da = self[case_name].copy()

        # Get difference from key case
        if key_case is not None and case_name != key_case:
            da.name = f"Diff. from key case in: {da.name}"
            title += " (diff. from key case)"
            if self.symmetric_0:
                cmap = DEFAULT_CMAP_DIV_DIFFOFABSDIFF
            else:
                cmap = DEFAULT_CMAP_DIV
            da_key_case = self[key_case]
            lats_match = check_grid_match(da["lat"], da_key_case["lat"])
            lons_match = check_grid_match(da["lon"], da_key_case["lon"])
            if not (lats_match and lons_match):
                print(
                    f"Nearest-neighbor interpolating {key_case} to match {case_name} grid",
                )
                da_key_case = da_key_case.interp_like(da, method="nearest")
            da -= da_key_case

        if self.cut_off_antarctica:
            da = _cut_off_antarctica(da)

        plt.sca(ax)

        if one_colorbar:
            cbar_kwargs = None
        else:
            cbar_kwargs = {"orientation": "horizontal", "location": "bottom"}

        im = da.plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            vmin=vrange[0],
            vmax=vrange[1],
            add_colorbar=not one_colorbar,
            cmap=cmap,
            cbar_kwargs=cbar_kwargs,
        )
        ax.coastlines(linewidth=0.5)
        plt.title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")

        return im
