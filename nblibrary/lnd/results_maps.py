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
from plotting_utils import get_key_diff
from plotting_utils import interp_key_case_grid

# Default colormaps for different plot types
DEFAULT_CMAP_SEQ = "viridis"
DEFAULT_CMAP_DIV = "coolwarm"
DEFAULT_CMAP_DIV_DIFFOFDIFF = "PiYG_r"

DEFAULT_MPL_BACKEND = matplotlib.rcParams["backend"]


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
        fig.colorbar(
            im,
            cax=cbar_ax,
            orientation="horizontal",
            label=da.attrs["units"],
        )
    else:
        # Minimal adjustment when each subplot has its own colorbar
        fig.subplots_adjust(top=0.96)


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
    vrange : list of float, optional
        Explicit [vmin, vmax] for colorbar. If None, calculated automatically.
        Default is None.
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
        vrange=None,
        cut_off_antarctica=True,
        incl_yrs_range=None,
    ):
        """Initialize ResultsMaps with specified colorbar and display options."""
        self.result_dict = {}
        self.cut_off_antarctica = cut_off_antarctica
        self.incl_yrs_range = incl_yrs_range

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
            # Initialize with extreme values for tracking min/max
            self.vmin = np.inf
            self.vmax = -np.inf
            if self.symmetric_0:
                # Use diverging colormap for symmetric ranges
                self.cmap = DEFAULT_CMAP_DIV

        # Per-plot vranges will override self._vrange if any is ever provided
        self.plot_vranges = {}

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

        When a DataArray is added, the class automatically updates the global
        min/max values for colorbar scaling (unless an explicit vrange was provided).

        Parameters
        ----------
        key : str
            Case name for the DataArray.
        value : xr.DataArray
            Map data to store.
        """
        # Update global min/max if automatic ranging is enabled
        if not self._vrange:
            self.vmin = min(self.vmin, np.nanmin(value.values))
            self.vmax = max(self.vmax, np.nanmax(value.values))

        # Store the DataArray and initialize its custom vrange to None
        self.result_dict[key] = value
        self.plot_vranges[key] = None

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

    def vrange(self):
        """
        Calculate and return the colorbar value range.

        Returns
        -------
        list of float
            [vmin, vmax] for colorbar limits.

        Notes
        -----
        If an explicit vrange was provided at initialization, that is returned.
        Otherwise, the range is calculated from the min/max values of all
        DataArrays. If symmetric_0=True, the range is made symmetric around zero.
        """
        # Return explicit range if provided
        if self._vrange:
            return self._vrange

        vmin = self.vmin
        vmax = self.vmax

        # Set upper and lower to same absolute value, centered on zero
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
        # Disable one_colorbar if key_plot is specified (incompatible options)
        if one_colorbar and key_plot is not None:
            warnings.warn("Ignoring one_colorbar=True because key_plot is not None")
            one_colorbar = False

        if fig_path is not None:
            # Ensure we're using a non-interactive backend for thread-safe plotting in Dask workers
            matplotlib.use("AGG")
        else:
            # Maybe unnecessary, but just in case matplotlib.use("AGG") above messes with things
            # in subsequent calls
            matplotlib.use(DEFAULT_MPL_BACKEND)

        # Calculate layout parameters
        self._get_mapfig_layout(one_colorbar)

        # TODO: Remove this once all map figures have been updated with new key case behavior
        key_plot_done = key_plot is not None and "DONE" in key_plot
        if key_plot_done:
            key_plot = key_plot.replace("DONE", "")

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

            # Determine color range for this subplot
            # Use per-plot color range (or entire plot color range) if any is provided
            msg = f"'{suptitle}': {one_colorbar} {key_plot}: "
            if any(v is None for v in self.plot_vranges.values()):
                if self.plot_vranges[this_subplot]:
                    warnings.warn(msg + "a", UserWarning)
                    vrange = self.plot_vranges[this_subplot]
                else:
                    warnings.warn(msg + "b", UserWarning)
                    vrange = [None, None]
            else:
                warnings.warn(msg + "c", UserWarning)
                vrange = self.vrange
                raise RuntimeError(
                    "Is this just never reached? It should be self.vrange()!!",
                )

            # Create the map subplot
            im = self._map_subplot(
                ax=ax,
                case_name=this_subplot,
                vrange=vrange,
                one_colorbar=one_colorbar,
                key_case=key_plot,
                key_plot_done=key_plot_done,
                key_diff_abs_error=key_diff_abs_error,
                case_incl_yr=case_incl_yr,
            )

            # Store the image object for potential colorbar updates
            images[this_subplot] = im

        # Add title and colorbar to complete the figure
        _mapfig_finishup(
            fig=self.fig,
            im=im,
            da=self[this_subplot],
            suptitle=suptitle,
            layout=self.layout,
            one_colorbar=one_colorbar,
        )

        # Synchronize colorbars for difference plots when using key_plot
        if key_plot is not None:
            # Make all non-key plot colorbars match
            self._update_non_key_colorbars(subplot_title_list, key_plot, images)

        # Save or display the figure
        if fig_path is None:
            self.fig.show()
        else:
            self.fig.savefig(fig_path, dpi=150)
            self._figure_cleanup()

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

    def _update_non_key_colorbars(self, subplot_title_list, key_plot, images):
        """
        Synchronize colorbar ranges for all difference plots.

        When comparing multiple cases to a reference, this method ensures all
        difference plots use the same symmetric colorbar range, making visual
        comparison easier.

        Parameters
        ----------
        subplot_title_list : list of str
            List of all subplot case names.
        key_plot : str
            Name of the reference case (excluded from updates).
        images : dict
            Dictionary mapping case names to their image objects.

        Notes
        -----
        The method finds the maximum absolute value across all difference plots
        and applies a symmetric range [-max, +max] to all of them.
        """
        # Find the most extreme absolute value across all non-key plots
        max_abs_val = 0
        for this_subplot in subplot_title_list:
            if this_subplot == key_plot:
                continue
            da_vals = self[this_subplot].values
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    "All-NaN slice encountered",
                )
                max_abs_val = max(max_abs_val, np.nanmax(np.abs(da_vals)))

        # Update all non-key plot color limits to use symmetric range
        for this_subplot in subplot_title_list:
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

    def _map_subplot(
        self,
        *,
        ax,
        case_name,
        vrange,
        one_colorbar,
        key_case,
        key_plot_done,
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
        vrange : list of float
            [vmin, vmax] for colorbar limits.
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

        # Create a copy to avoid modifying the original data
        da = self[case_name].copy()

        # Calculate difference from key case if applicable
        if key_case is not None and case_name != key_case:
            title, cmap, da = self._get_diff_from_key_case(
                case_name=case_name,
                key_case=key_case,
                key_diff_abs_error=key_diff_abs_error,
                da=da,
                title=title,
                key_plot_done=key_plot_done,
            )

        # Note subplots with missing data or years
        if np.all(np.isnan(da.values)):
            title += " (no data)"
        elif case_incl_yr is not None and case_incl_yr != self.incl_yrs_range:
            title += f" (only {case_incl_yr[0]}-{case_incl_yr[1]})"

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
            vmin=vrange[0],
            vmax=vrange[1],
            add_colorbar=not one_colorbar,
            cmap=cmap,
            cbar_kwargs=cbar_kwargs,
        )

        # Add coastlines for geographic reference
        ax.coastlines(linewidth=0.5)

        # Set title and remove axis labels/ticks for cleaner appearance
        ax.set_title(title)  # Instead of plt.title, for parallelism
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")

        return im

    def _get_diff_from_key_case(
        self,
        *,
        case_name,
        key_case,
        key_diff_abs_error,
        da,
        title,
        key_plot_done,
    ):
        """
        Calculate difference from a reference case.

        This internal method computes the difference between the current case
        and a reference case, handling grid mismatches through interpolation
        and supporting both simple differences and differences in absolute error.

        Parameters
        ----------
        case_name : str
            Name of the current case.
        key_case : str
            Name of the reference case.
        key_diff_abs_error : bool
            If True, calculate |da| - |da_key| instead of da - da_key.
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
            DataArray containing the difference values.

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

        # Calculate difference (absolute error or simple difference)
        if not key_plot_done:
            # Get reference case data
            da_key_case = self[key_case]

            # Interpolate key case to match grid, if needed
            da_key_case = interp_key_case_grid(
                case_name,
                key_case,
                da,
                da_key_case,
            )

            da = get_key_diff(key_diff_abs_error, da, da_key_case)

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
