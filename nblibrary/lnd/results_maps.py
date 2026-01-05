"""
Container class for managing multiple map DataArrays with consistent visualization.
"""
from __future__ import annotations

import warnings

import cartopy.crs as ccrs
import matplotlib
import numpy as np
import xarray as xr
from matplotlib.figure import Figure

# Default colormaps for different plot types
DEFAULT_CMAP_SEQ = "viridis"
DEFAULT_CMAP_DIV = "coolwarm"
DEFAULT_CMAP_DIV_DIFFOFDIFF = "PiYG_r"

DEFAULT_MPL_BACKEND = matplotlib.rcParams["backend"]

DEFAULT_NO_VRANGE = (None, None)


def _cut_off_antarctica(da, antarctica_border=-60):
    """
    Remove Antarctica from a map by cutting off latitudes south of a threshold.

    This internal function restricts the latitude range of a DataArray to exclude
    Antarctica, which can improve visualization of global patterns. It automatically
    handles both ascending and descending latitude ordering.

    Parameters
    ----------
    da : xr.DataArray
        Input DataArray with a 'lat' coordinate.
    antarctica_border : float, optional
        Latitude threshold (in degrees) below which data is excluded.
        Default is -60 degrees.

    Returns
    -------
    da : xr.DataArray
        DataArray with Antarctica removed (latitudes >= antarctica_border).

    Notes
    -----
    The function automatically detects whether latitudes are in ascending or
    descending order and adjusts the slice accordingly.
    """
    # Determine latitude ordering (ascending or descending)
    first = da["lat"].isel(lat=0)
    last = da["lat"].isel(lat=-1)

    # Create appropriate slice based on latitude ordering
    if first < last:
        # Ascending latitudes (e.g., -90 to 90)
        lat_slice = slice(antarctica_border, 90)
    else:
        # Descending latitudes (e.g., 90 to -90)
        lat_slice = slice(90, antarctica_border)

    # Apply the latitude selection
    da = da.sel(lat=lat_slice)
    return da


def _mapfig_finishup(*, fig, im, da, suptitle, layout, one_colorbar):
    """
    Finalize a multi-panel map figure with title and colorbar.

    This internal function adds the final touches to a figure containing map
    subplots, including the super title and optional shared colorbar.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure object to finalize.
    im : matplotlib.image.AxesImage
        The image object from the last subplot (used for colorbar).
    da : xr.DataArray
        DataArray containing units information for colorbar label.
    suptitle : str
        Super title for the entire figure.
    layout : dict
        Dictionary containing layout parameters (subplot adjustments, colorbar position).
    one_colorbar : bool
        If True, add a single shared colorbar for all subplots.
        If False, each subplot has its own colorbar.

    Notes
    -----
    When one_colorbar is True, the function adjusts subplot spacing to make
    room for a horizontal colorbar at the bottom of the figure.
    """
    # Add super title to the figure
    fig.suptitle(suptitle, fontsize="x-large", fontweight="bold")

    if one_colorbar:
        # Adjust subplot spacing to accommodate shared colorbar
        fig.subplots_adjust(
            top=layout["subplots_adjust_colorbar_top"] - 0.04,
            bottom=layout["subplots_adjust_colorbar_bottom"],
        )
        # Create axes for the colorbar
        cbar_ax = fig.add_axes(rect=layout["cbar_ax_rect"])
        # Add horizontal colorbar with units label
        assert "units" in da.attrs, "Results map missing units attribute"
        fig.colorbar(
            im,
            cax=cbar_ax,
            orientation="horizontal",
            label=da.attrs["units"],
        )
    else:
        # Minimal adjustment when each subplot has its own colorbar
        fig.subplots_adjust(top=0.96)


def _check_vrange_is_2elem_tuple(vrange):
    msg = "ResultsMaps.vrange must be a two-element tuple"
    assert isinstance(vrange, tuple) and len(vrange) == 2, msg


def _check_vrange_ok_for_key_plot(vrange):
    msg = (
        "If you want to show differences from a key plot (key_plot is not falsy), plot() will"
        " also include the key plot itself with a sequential colorbar. Because of how colorbar"
        " handling is implemented, it is not possible to also request a default colorbar range"
        " unless vmin (first value in vrange tuple) is 0. In that case vrange would be applied to"
        " key plot and (-vmax, vmax) would be applied to other plots."
    )
    vmin, vmax = vrange
    if vrange != DEFAULT_NO_VRANGE and not (vmin == 0 and vmax is not None):
        raise NotImplementedError(msg)


class ResultsMaps:
    """
    Container for managing multiple map DataArrays with consistent visualization.

    This class facilitates the creation of multi-panel map figures with consistent
    colorbars, projections, and formatting. It can handle both absolute values and
    differences from a reference case, with automatic colorbar scaling and optional
    symmetric color ranges.

    Attributes
    ----------
    result_dict : dict
        Dictionary mapping case names (str) to DataArrays containing map data.
    cut_off_antarctica : bool
        If True, exclude Antarctica (latitudes < -60°) from plots.
    cmap : str
        Matplotlib colormap name to use for plots.
    layout : dict
        Dictionary containing figure layout parameters.
    axes : np.ndarray
        Array of matplotlib axes objects for subplots.
    fig : matplotlib.figure.Figure
        The figure object containing all subplots.
    symmetric_0 : bool
        If True, use symmetric colorbar centered on zero.
    plot_vranges : dict
        Dictionary mapping case names to custom color ranges.

    Parameters
    ----------
    symmetric_0 : bool, optional
        If True, use a diverging colormap with symmetric range around zero.
        Default is False.
    vrange : tuple of float, optional
        Explicit (vmin, vmax) for colorbar. Values will be passed to DataArray.plot(), but they may
        be overridden later depending on other settings. Default is (None, None).
    cut_off_antarctica : bool, optional
        If True, exclude Antarctica from plots. Default is True.
    incl_yrs_range: list, optional
        First and last years requested for plots in this figure. Individual subplots might only have
        a subset of these, or even none.

    Notes
    -----
    - When symmetric_0=True, the colorbar will be centered on zero with equal
      positive and negative ranges.
    - The class automatically tracks min/max values across all added DataArrays
      to determine appropriate color ranges.
    - Supports both single shared colorbar and individual colorbars per subplot.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        *,
        symmetric_0=False,
        vrange=DEFAULT_NO_VRANGE,
        cut_off_antarctica=True,
        incl_yrs_range=None,
    ):
        """Initialize ResultsMaps with specified colorbar and display options."""

        # Save inputs
        self.symmetric_0 = symmetric_0
        self.vrange = vrange
        self.cut_off_antarctica = cut_off_antarctica
        self.incl_yrs_range = incl_yrs_range

        # Initialize dictionary of results. This will contain xarray DataArrays as values, with keys
        # corresponding to subplot titles.
        self.result_dict = {}

        # Colormap to be applied to all subplots if ResultsMaps.plot(..., key_plot=None). If
        # symmetric_0, use diverging colormap; otherwise use sequential. Not that this will be
        # overridden if key plot is given, in which case it will get the sequential colormap, and
        # others will get the diverging colormap.
        self.cmap = DEFAULT_CMAP_DIV if self.symmetric_0 else DEFAULT_CMAP_SEQ

        # Empty figure layout stuff
        self.layout = {}
        self.axes = None
        self.fig = None

        # Per-plot vranges will override self.vrange if any is ever provided.
        self.plot_vranges = {}

        # Checks
        _check_vrange_is_2elem_tuple(self.vrange)

    def __getitem__(self, key):
        """
        Enable dictionary-style access to result_dict.

        Parameters
        ----------
        key : str
            Case name to retrieve.

        Returns
        -------
        xr.DataArray
            The DataArray associated with the given key.
        """
        return self.result_dict[key]

    def __setitem__(self, key: str, value: xr.DataArray):
        """
        Enable dictionary-style assignment to result_dict.

        Parameters
        ----------
        key : str
            Case name for the DataArray.
        value : xr.DataArray
            Map data to store.
        """
        self.result_dict[key] = value

    def __len__(self):
        """
        Return the number of maps stored.

        Returns
        -------
        int
            Number of DataArrays in result_dict.
        """
        return len(self.result_dict)

    def _get_mapfig_layout(self, one_colorbar):
        """
        Calculate figure layout parameters based on number of subplots.

        This internal method determines the grid layout (rows and columns),
        figure size, and colorbar positioning based on the number of maps
        to display.

        Parameters
        ----------
        one_colorbar : bool
            If True, adjust layout to accommodate a shared colorbar.

        Notes
        -----
        The layout uses a 2-column grid with as many rows as needed.
        Figure height scales with the number of rows.
        """
        # Use 2 columns for subplot grid
        self.layout["ncols"] = 2
        # Calculate required number of rows
        self.layout["nrows"] = int(np.ceil(len(self) / self.layout["ncols"]))

        if one_colorbar:
            # Reserve space at bottom for shared colorbar
            self.layout["subplots_adjust_colorbar_top"] = 0.95
            self.layout["subplots_adjust_colorbar_bottom"] = 0.2
            # Position for colorbar axes [left, bottom, width, height]
            self.layout["cbar_ax_rect"] = (0.2, 0.15, 0.6, 0.03)
            height = 3.75 * self.layout["nrows"]
        else:
            # Less vertical space needed when each subplot has its own colorbar
            height = 4.85 * self.layout["nrows"]

        width = 15
        self.layout["figsize"] = (width, height)

    def plot(
        self,
        *,
        subplot_title_list: list,
        suptitle: str,
        one_colorbar: bool = False,
        fig_path: str = None,
        key_plot: str = None,
        key_diff_abs_error: bool = False,
        case_incl_yr_dict: dict = None,
    ):
        """
        Create a multi-panel map figure with all stored DataArrays.

        This method generates a complete figure with map subplots arranged in a grid,
        with options for shared or individual colorbars, and the ability to show
        differences from a reference case.

        Parameters
        ----------
        subplot_title_list : list of str
            List of case names (keys in result_dict) in the order they should appear.
        suptitle : str
            Super title for the entire figure.
        one_colorbar : bool, optional
            If True, use a single shared colorbar for all subplots.
            If False, each subplot gets its own colorbar. Default is False.
            Note: Ignored if key_plot is specified.
        fig_path : str, optional
            Path to save the figure. If None, the figure is displayed but not saved.
            Default is None.
        key_plot : str, optional
            Name of the reference case. If provided, all other subplots will show
            differences from this case. Default is None.
        key_diff_abs_error : bool, optional
            If True and key_plot is specified, show differences in absolute error
            (|da| - |da_key|) rather than simple differences. Default is False.

        Notes
        -----
        - When key_plot is specified, the reference case uses the default colormap
          while difference plots use a diverging colormap.
        - The method automatically handles grid interpolation if cases have different
          spatial resolutions.
        - Empty subplot positions (when number of cases is odd) are hidden.
        """

        msg = (
            "It doesn't make sense to request a key plot (key_plot is not falsy) when there's only"
            " one plot (subplot_title_list has only one member)."
        )
        assert not (key_plot and len(subplot_title_list) == 1), msg

        if fig_path is not None:
            # Ensure we're using a non-interactive backend for thread-safe plotting in Dask workers
            matplotlib.use("AGG")
        else:
            # Maybe unnecessary, but just in case matplotlib.use("AGG") above messes with things
            # in subsequent calls
            matplotlib.use(DEFAULT_MPL_BACKEND)

        # Calculate layout parameters
        self._get_mapfig_layout(one_colorbar)

        # Create figure with map projection for all subplots
        # Use Figure directly instead of plt.subplots() to avoid pyplot's figure manager
        # in Dask parallel contexts
        self.fig = Figure(figsize=self.layout["figsize"])
        self.axes = self.fig.subplots(
            nrows=self.layout["nrows"],
            ncols=self.layout["ncols"],
            subplot_kw={"projection": ccrs.PlateCarree()},
        )

        # Store image objects for each subplot (needed for colorbar updates)
        images = {}

        # Iterate through all subplot positions
        for i, ax in enumerate(self.axes.ravel()):
            try:
                this_subplot = subplot_title_list[i]
                if case_incl_yr_dict is not None:
                    case_incl_yr = case_incl_yr_dict[this_subplot]
                else:
                    case_incl_yr = None
            except IndexError:
                # Hide empty subplot positions
                ax.set_visible(False)
                continue

            # Create the map subplot
            im = self._map_subplot(
                ax=ax,
                case_name=this_subplot,
                one_colorbar=one_colorbar,
                key_case=key_plot,
                key_diff_abs_error=key_diff_abs_error,
                case_incl_yr=case_incl_yr,
            )

            # Store the image object for potential colorbar updates
            images[this_subplot] = im

        # Update colorbars?
        self._finish_colorbar_ranges(subplot_title_list, one_colorbar, key_plot, images)

        # Add title and colorbar to complete the figure
        last_subplot = subplot_title_list[-1]  # Any; doesn't matter
        _mapfig_finishup(
            fig=self.fig,
            im=images[last_subplot],
            da=self[last_subplot],
            suptitle=suptitle,
            layout=self.layout,
            one_colorbar=one_colorbar,
        )

        # Save or display the figure
        if fig_path is None:
            self.fig.show()
        else:
            self.fig.savefig(fig_path, dpi=150)
            self._figure_cleanup()

    def _finish_colorbar_ranges(
        self,
        subplot_title_list,
        one_colorbar,
        key_plot,
        images,
    ):

        _check_vrange_is_2elem_tuple(self.vrange)

        msg = (
            "If you want all plots to share a colorbar (one_colorbar=True), why did you ask for"
            " some of them to have special colorbar limits (plot_vranges isn't empty)?"
        )
        assert not (one_colorbar and self.plot_vranges), msg

        msg = (
            "If you want to show differences from a key plot (key_plot is not falsy), plot() will"
            " also include the key plot itself with a sequential colorbar, meaning that it's not"
            " possible as you requested to have all plots share a colorbar (one_colorbar is True)."
        )
        assert not (key_plot and one_colorbar), msg

        msg = (
            "Because of how plot colorbar handling is implemented, it is not possible to apply"
            " special colorbar limits as you requested (plot_vranges isn't empty) while also"
            " providing a key plot (key_plot is not falsy)."
        )
        if key_plot and self.plot_vranges:
            raise NotImplementedError(msg)

        if key_plot:
            _check_vrange_ok_for_key_plot(self.vrange)

        # TODO: Check that vmax >= vmin

        if self.plot_vranges:
            # If any plot has a special colorbar range provided, apply it.
            for this_subplot, vrange in self.plot_vranges.items():
                vmin, vmax = vrange
                im = images[this_subplot]
                self._update_image_colorbar_range(vmin, vmax, im)
        elif one_colorbar:
            if self.vrange == DEFAULT_NO_VRANGE:
                self._get_and_set_shared_colorbar_range(
                    subplot_title_list,
                    key_plot,
                    images,
                )
            else:
                # Apply the explicit vrange to all subplots
                vmin, vmax = self.vrange
                for this_subplot in subplot_title_list:
                    im = images[this_subplot]
                    self._update_image_colorbar_range(vmin, vmax, im)
        elif key_plot:
            if self.vrange != (None, None):
                for this_subplot in subplot_title_list:
                    vmin, vmax = self.vrange
                    if this_subplot != key_plot:
                        vmin = -vmax  # pylint: disable=invalid-unary-operand-type
                    im = images[this_subplot]
                    self._update_image_colorbar_range(vmin, vmax, im)
            else:
                # Will skip key plot
                self._get_and_set_shared_colorbar_range(
                    subplot_title_list,
                    key_plot,
                    images,
                )

    def _get_and_set_shared_colorbar_range(self, subplot_title_list, key_plot, images):
        # Get
        vrange = self._get_shared_colorbar_range(subplot_title_list, key_plot)
        # Apply
        self._set_shared_colorbar_range(subplot_title_list, key_plot, images, vrange)

    def _get_shared_colorbar_range(self, subplot_title_list, key_plot):
        """
        Get minimum and maximum values seen across all subplots, skipping the key plot if any.
        """
        vmin = np.inf
        vmax = -np.inf
        any_subplot_has_data = False
        for this_subplot in subplot_title_list:
            if key_plot is not None and this_subplot == key_plot:
                continue
            if self[this_subplot] is None:
                continue
            da_vals = self[this_subplot].values
            if not any_subplot_has_data and np.any(~np.isnan(da_vals)):
                any_subplot_has_data = True
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="All-NaN slice encountered",
                    category=RuntimeWarning,
                )
                vmin = min(vmin, np.nanmin(da_vals))
                vmax = max(vmax, np.nanmax(da_vals))

        if any_subplot_has_data and (np.isinf(vmin) or np.isinf(vmax)):
            raise RuntimeError("Failed to find vmin and/or vmax")
        if not any_subplot_has_data:
            vmin = -1.0
            vmax = 1.0

        return vmin, vmax

    def _set_shared_colorbar_range(self, subplot_title_list, key_plot, images, vrange):
        """
        Apply minimum and maximum colorbar values to all plots, skipping the key plot if any.
        """
        vmin, vmax = vrange
        if self.symmetric_0 or key_plot:
            vmax = max(abs(vmin), abs(vmax))
            vmin = -vmax
        for this_subplot in subplot_title_list:
            if this_subplot == key_plot:
                continue
            im = images[this_subplot]
            self._update_image_colorbar_range(vmin, vmax, im)

    def _update_image_colorbar_range(self, vmin, vmax, im):
        # Sense checks
        assert vmin <= vmax, f"vmin ({vmin}) > vmax ({vmax})"
        assert not np.isinf(vmin) and not np.isinf(
            vmax,
        ), f"Infinite vmin ({vmin}) / vmax ({vmax})"

        im.set_clim(vmin, vmax)

        # Update the colorbar, if it exists
        if hasattr(im, "colorbar") and im.colorbar is not None:
            im.colorbar.update_normal(im)

    def _figure_cleanup(self):
        """
        Clean up to release memory (important in parallel execution)
        """
        # Clear all axes to release references to data
        for ax in self.axes.ravel():
            ax.clear()
        # Clear the figure
        self.fig.clear()
        # Delete references
        del self.axes
        del self.fig

    def _map_subplot(
        self,
        *,
        ax,
        case_name,
        one_colorbar,
        key_case,
        key_diff_abs_error,
        case_incl_yr,
    ):
        """
        Create a single map subplot.

        This internal method handles the creation of an individual map subplot,
        including optional difference calculation from a reference case, Antarctica
        removal, and colorbar configuration.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes object to plot on.
        case_name : str
            Name of the case to plot.
        one_colorbar : bool
            If True, don't add individual colorbar to this subplot.
        key_case : str or None
            Name of reference case for difference calculation.
        key_diff_abs_error : bool
            If True, calculate difference in absolute error.

        Returns
        -------
        im : matplotlib.image.AxesImage
            The image object created by the plot.

        Notes
        -----
        - If key_case is provided and differs from case_name, the subplot shows
          the difference from the reference case.
        - Automatic grid interpolation is performed if grids don't match.
        - Coastlines are added for geographic context.
        """
        title = case_name
        cmap = self.cmap

        # If case's maps couldn't be made, make a dummy map with all NaN
        if self[case_name] is None:
            lon = np.arange(-180, 180, 1)
            lat = np.arange(-90, 91, 1)
            coords = {"lat": lat, "lon": lon}
            da = xr.DataArray(
                np.full((len(lat), len(lon)), np.nan),
                coords=coords,
                dims=coords.keys(),
            )
        else:

            # Create a copy to avoid modifying the original data
            da = self[case_name].copy()

            # By this point, we expect a DataArray with latitude and longitude dimensions. To be
            # maximally accepting, just check that it's 2-d.
            msg = f"Expected DataArray with 2 dimensions, got {da.ndim}: {da.dims}"
            assert da.ndim == 2, msg

            # Calculate difference from key case if applicable
            if key_case is not None and case_name != key_case:
                title, cmap, da = self._plotting_diff_from_key_case(
                    key_diff_abs_error=key_diff_abs_error,
                    da=da,
                    title=title,
                )

            # Remove Antarctica if requested
            if self.cut_off_antarctica:
                da = _cut_off_antarctica(da)

        # Configure colorbar based on one_colorbar setting
        if one_colorbar:
            cbar_kwargs = None
        else:
            cbar_kwargs = {"orientation": "horizontal", "location": "bottom"}

        # Create the map plot
        im = da.plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            add_colorbar=not one_colorbar,
            cmap=cmap,
            cbar_kwargs=cbar_kwargs,
        )

        # Hide map and colorbar if all data is NaN
        if np.all(np.isnan(da.values)):
            im.set_visible(False)
            ax.set_frame_on(False)
            if hasattr(im, "colorbar") and im.colorbar is not None:
                im.colorbar.ax.set_visible(False)

        # Otherwise, add coastlines
        else:
            # Add coastlines for geographic reference
            ax.coastlines(linewidth=0.5)

        # Set title and remove axis labels/ticks for cleaner appearance
        # Note subplots with missing data or years
        if np.all(np.isnan(da.values)):
            title += " (no data)"
        elif case_incl_yr is not None and case_incl_yr != self.incl_yrs_range:
            title += f" (only {case_incl_yr[0]}-{case_incl_yr[1]})"
        ax.set_title(title)  # Instead of plt.title, for parallelism
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")

        return im

    def _plotting_diff_from_key_case(
        self,
        *,
        key_diff_abs_error,
        da,
        title,
    ):
        """
        Update plot inputs for showing difference from reference ("key") case.

        Parameters
        ----------
        key_diff_abs_error : bool
            Whether the difference being plotted is absolute error.
        da : xr.DataArray
            DataArray for the current case.
        title : str
            Current subplot title (will be modified).

        Returns
        -------
        title : str
            Updated title indicating this is a difference plot.
        cmap : str
            Colormap name appropriate for difference plots.
        da : xr.DataArray
            DataArray with updated name.

        Notes
        -----
        - If grids don't match, nearest-neighbor interpolation is used.
        - The colormap is changed to a diverging scheme for difference plots.
        - If symmetric_0 is True, a special diff-of-diff colormap is used.
        """

        # TODO handle where this case and key case don't have same years included

        # Update data name and title to indicate this is a difference
        da_name = f"Diff. from key case in: {da.name}"
        title += " (diff. from key case)"

        # Select appropriate diverging colormap
        if self.symmetric_0:
            cmap = DEFAULT_CMAP_DIV_DIFFOFDIFF
        else:
            cmap = DEFAULT_CMAP_DIV

        # Update name and title to reflect absolute error difference
        if key_diff_abs_error:
            assert "from key case" in da_name
            da_name = da_name.replace(
                "from key case",
                "from key case in abs. error",
            )
            assert "from key case" in title
            title = title.replace("from key case", "from key case in abs. error")

        da.name = da_name
        return title, cmap, da
