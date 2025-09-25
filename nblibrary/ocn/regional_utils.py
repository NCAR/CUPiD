from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from cartopy import crs as ccrs
from cartopy import feature as cfeature
from matplotlib.animation import FuncAnimation
from matplotlib.colors import BoundaryNorm
from matplotlib.colors import ListedColormap
from matplotlib.colors import LogNorm
from matplotlib.ticker import MaxNLocator

# import xarray as xr

# from mom6_tools.MOM6grid import MOM6grid
# from mom6_tools.m6plot import (
#     chooseColorLevels,
#     chooseColorMap,
#     boundaryStats,
#     myStats,
#     label,
# )

# The above functions are duplicated below so these utilities can run without
# access to mom6-tools, this will be updated in the future and these utilities
# will likely be migrated to mom6-tools.


def chooseColorMap(sMin, sMax, difference=None):
    """
    Based on the min/max extremes of the data, choose a colormap that fits the data.
    """
    if difference is True:
        return "dunnePM"
    elif sMin < 0 and sMax > 0:
        return "dunnePM"
    # elif sMax>0 and sMin<0.1*sMax: return 'hot'
    # elif sMin<0 and sMax>0.1*sMin: return 'hot_r'
    else:
        return "dunneRainbow"


def chooseColorLevels(
    sMin,
    sMax,
    colorMapName,
    clim=None,
    nbins=None,
    steps=[1, 2, 2.5, 5, 10],
    extend=None,
    logscale=False,
    autocenter=False,
):
    """
    If nbins is a positive integer, choose sensible color levels with nbins colors.
    If clim is a 2-element tuple, create color levels within the clim range
    or if clim is a vector, use clim as contour levels.
    If clim provides more than 2 color interfaces, nbins must be absent.
    If clim is absent, the sMin,sMax are used as the color range bounds.
    If autocenter is True and clim is None then the automatic color levels are centered.

    Returns cmap, norm and extend.
    """
    if nbins is None and clim is None:
        raise Exception("At least one of clim or nbins is required.")
    if clim is not None:
        if len(clim) < 2:
            raise Exception("clim must be at least 2 values long.")
        if nbins is None and len(clim) == 2:
            raise Exception(
                "nbins must be provided when clims specifies a color range.",
            )
        if nbins is not None and len(clim) > 2:
            raise Exception(
                "nbins cannot be provided when clims specifies color levels.",
            )
    if clim is None:
        if autocenter:
            levels = MaxNLocator(nbins=nbins, steps=steps).tick_values(
                min(sMin, -sMax),
                max(sMax, -sMin),
            )
        else:
            levels = MaxNLocator(nbins=nbins, steps=steps).tick_values(sMin, sMax)
    elif len(clim) == 2:
        levels = MaxNLocator(nbins=nbins, steps=steps).tick_values(clim[0], clim[1])
    else:
        levels = clim

    # nColors = len(levels) - 1
    if extend is None:
        if sMin < levels[0] and sMax > levels[-1]:
            extend = "both"  # ; eColors=[1,1]
        elif sMin < levels[0] and sMax <= levels[-1]:
            extend = "min"  # ; eColors=[1,0]
        elif sMin >= levels[0] and sMax > levels[-1]:
            extend = "max"  # ; eColors=[0,1]
        else:
            extend = "neither"  # ; eColors=[0,0]
    eColors = [0, 0]
    if extend in ["both", "min"]:
        eColors[0] = 1
    if extend in ["both", "max"]:
        eColors[1] = 1

    cmap = plt.get_cmap(colorMapName)  # ,lut=nColors+eColors[0]+eColors[1])
    # cmap0 = cmap(0.)
    # cmap1 = cmap(1.)
    # cmap = ListedColormap(cmap(range(eColors[0],nColors+1-eColors[1]+eColors[0])))#, N=nColors)
    # if eColors[0]>0: cmap.set_under(cmap0)
    # if eColors[1]>0: cmap.set_over(cmap1)
    if logscale:
        norm = LogNorm(vmin=levels[0], vmax=levels[-1])
    else:
        norm = BoundaryNorm(levels, ncolors=cmap.N)
    return cmap, norm, extend


def myStats(s, area, debug=False):
    """
    Calculates mean, standard deviation and root-mean-square of s.
    """
    sMin = np.ma.min(s)
    sMax = np.ma.max(s)
    if debug:
        print("myStats: min(s) =", sMin)
    if debug:
        print("myStats: max(s) =", sMax)
    if area is None:
        return sMin, sMax, None, None, None
    weight = area.copy()
    if debug:
        print("myStats: sum(area) =", np.ma.sum(weight))
    if not np.ma.getmask(s).any() == np.ma.nomask:
        weight[s.mask] = 0.0
    sumArea = np.ma.sum(weight)
    if debug:
        print("myStats: sum(area) =", sumArea, "after masking")
    if debug:
        print("myStats: sum(s) =", np.ma.sum(s))
    if debug:
        print("myStats: sum(area*s) =", np.ma.sum(weight * s))
    mean = np.ma.sum(weight * s) / sumArea
    std = math.sqrt(np.ma.sum(weight * ((s - mean) ** 2)) / sumArea)
    rms = math.sqrt(np.ma.sum(weight * (s**2)) / sumArea)
    if debug:
        print("myStats: mean(s) =", mean)
    if debug:
        print("myStats: std(s) =", std)
    if debug:
        print("myStats: rms(s) =", rms)
    return sMin, sMax, mean, std, rms


def label(label, units):
    """
    Combines a label string and units string together in the form 'label [units]'
    unless one of the other is empty.
    """
    string = r"" + label
    if len(units) > 0:
        string = string + " [" + units + "]"
    return string


def plot_2D_latlon_field_plot(
    field,
    grid,
    lon_var="geolon",
    lat_var="geolat",
    area_var=None,
    xlabel=None,
    xunits=None,
    ylabel=None,
    yunits=None,
    title="",
    suptitle="",
    clim=None,
    colormap=None,
    norm=None,
    extend=None,
    centerlabels=False,
    nbins=None,
    axis=None,
    add_cbar=True,
    cbar_label=None,
    figsize=[16, 9],
    dpi=150,
    sigma=2.0,
    annotate=True,
    ignore=None,
    save=None,
    debug=False,
    show=False,
    logscale=False,
    projection=None,
    coastlines=True,
    res=None,
    coastcolor=[0, 0, 0],
    landcolor=[0.75, 0.75, 0.75],
    coast_linewidth=0.5,
    fontsize=22,
    gridlines=False,
):
    # Preplotting
    plt.rc("font", size=fontsize)

    # Mask ignored values
    if ignore is not None:
        maskedField = np.ma.masked_array(field, mask=[field == ignore])
    else:
        maskedField = np.ma.masked_array(
            field,
            mask=np.isnan(field),
        )  # maskedField = field.copy()

    # Diagnose statistics
    if area_var is None:
        area_cell = grid["areacello"].to_numpy()
    else:
        area_cell = grid[area_var].to_numpy()
    sMin, sMax, sMean, sStd, sRMS = myStats(maskedField, area_cell, debug=debug)

    # Choose colormap
    if nbins is None and (clim is None or len(clim) == 2):
        nbins = 35
    if colormap is None:
        colormap = chooseColorMap(sMin, sMax)
        if clim is None and sStd is not None:
            lower = sMean - sigma * sStd
            upper = sMean + sigma * sStd
            if lower < sMin:
                lower = sMin
            if upper > sMax:
                upper = sMax
            cmap, norm, extend = chooseColorLevels(
                lower,
                upper,
                colormap,
                clim=clim,
                nbins=nbins,
                extend=extend,
                logscale=logscale,
            )
        else:
            cmap, norm, extend = chooseColorLevels(
                sMin,
                sMax,
                colormap,
                clim=clim,
                nbins=nbins,
                extend=extend,
                logscale=logscale,
            )
    else:
        cmap = colormap

    # Set up figure and axis
    if projection is None:
        central_longitude = float(
            (grid[lon_var].max().values + grid[lon_var].min().values) / 2,
        )
        projection = ccrs.Robinson(central_longitude=central_longitude)
    created_own_axis = False
    if axis is None:
        created_own_axis = True
        fig = plt.figure(dpi=dpi, figsize=figsize)
        axis = fig.add_subplot(1, 1, 1, projection=projection)

    # Plot Color Mesh
    pm = axis.pcolormesh(
        grid[lon_var],
        grid[lat_var],
        field,
        cmap=cmap,
        norm=norm,
        transform=ccrs.PlateCarree(),
    )

    # Add Land and Coastlines
    if res is None:
        res = "50m"  # can be adjusted to estimate a best res between 10m, 50m, and 110m, also use other methods
    if coastlines:
        axis.coastlines(
            resolution=res,
            color=coastcolor,
            linewidth=coast_linewidth,
        )
    axis.set_facecolor(landcolor)

    # Add the fancy bits
    if add_cbar:
        # Get position of the axis
        bbox = axis.get_position()
        fig = axis.figure  # Get the figure the axis belongs to

        # Create new axes for the colorbar, scaled to axis size
        cbar_width = 0.01  # width as fraction of figure
        cbar_padding = 0.01
        cbar_ax = fig.add_axes(
            [
                bbox.x1 + cbar_padding,  # left
                bbox.y0,  # bottom
                cbar_width,  # width
                bbox.height,  # height
            ],
        )
        cb = plt.colorbar(pm, cax=cbar_ax, extend=extend)
        if cbar_label is not None:
            cb.set_label(cbar_label)
    if centerlabels and len(clim) > 2:
        if not add_cbar:
            raise ValueError(
                "Argument Mismatch: add_cbar must be true if you also specify centerlabels to be true.",
            )
        cb.set_ticks(0.5 * (clim[:-1] + clim[1:]))

    axis.set_facecolor(landcolor)
    # axis.set_xlim( xLims )
    # axis.set_ylim( yLims )

    if annotate:
        axis.annotate(
            f"max={sMax:.5g}\nmin={sMin:.5g}",
            xy=(0.0, 1.01),
            xycoords="axes fraction",
            verticalalignment="bottom",
        )
        if area_cell is not None:
            axis.annotate(
                f"mean={sMean:.5g}\nrms={sRMS:.5g}",
                xy=(1.0, 1.01),
                xycoords="axes fraction",
                verticalalignment="bottom",
                horizontalalignment="right",
            )
            axis.annotate(
                " sd=%.5g\n" % (sStd),
                xy=(1.0, 1.01),
                xycoords="axes fraction",
                verticalalignment="bottom",
                horizontalalignment="left",
            )

    if xlabel and xunits:
        if len(xlabel + xunits) > 0:
            axis.set_xlabel(label(xlabel, xunits))
    if ylabel and yunits:
        if len(ylabel + yunits) > 0:
            axis.set_ylabel(label(ylabel, yunits))
    if len(title) > 0:
        axis.set_title(title, fontsize=fontsize * 1.5)
    if len(suptitle) > 0:
        if annotate:
            plt.suptitle(suptitle, y=1.01)
        else:
            plt.suptitle(suptitle)

    if gridlines:
        gl = axis.gridlines(
            draw_labels=True,
            lw=0.5,
            color="gray",
            alpha=0.5,
        )
        gl.top_labels = False
        gl.right_labels = False

    # Only show if we created our own axis
    if created_own_axis and show:
        plt.show(block=False)
    elif created_own_axis:
        plt.show(block=True)
    if save is not None:
        plt.savefig(save)
        plt.close()

    return pm


def visualize_regional_domain(grd_xr, save=None):
    # Grab useful variables
    central_longitude = float(
        (grd_xr["geolon"].max().values + grd_xr["geolon"].min().values) / 2,
    )
    lon = grd_xr["geolon_c"].values
    lat = grd_xr["geolat_c"].values

    # Set up figure, need to add subplots individually because of projections
    fig = plt.figure(dpi=200, figsize=(14, 8))

    # -------------------------- #
    # Global Plot showing region #
    # -------------------------- #
    ax = fig.add_subplot(
        1,
        3,
        1,
        projection=ccrs.Mercator(central_longitude=central_longitude),
    )

    # Add coastlines and country borders
    ax.coastlines(linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.add_feature(cfeature.LAND, facecolor="lightgray")
    ax.add_feature(cfeature.OCEAN, facecolor="lightblue")

    # Get the boundary of the grid
    boundary_lon = np.concatenate(
        [
            lon[0, :],  # top
            lon[1:, -1],  # right
            lon[-1, -2::-1],  # bottom (reversed)
            lon[-2::-1, 0],  # left (reversed)
        ],
    )

    boundary_lat = np.concatenate(
        [lat[0, :], lat[1:, -1], lat[-1, -2::-1], lat[-2::-1, 0]],
    )

    ax.plot(boundary_lon, boundary_lat, color="red", transform=ccrs.PlateCarree())
    ax.set_global()
    ax.set_title("Regional Domain", fontsize=10)

    # --------------------------------------- #
    # Zoomed in showing relative grid density #
    # --------------------------------------- #
    ax1 = fig.add_subplot(
        1,
        3,
        2,
        projection=ccrs.PlateCarree(central_longitude=central_longitude),
    )

    ax1.coastlines(linewidth=0.5, resolution="50m")
    ax1.add_feature(cfeature.LAND, facecolor="lightgray")
    ax1.add_feature(cfeature.OCEAN, facecolor="lightblue")

    skip = 10

    for i in range(0, lon.shape[1], skip):
        ax1.plot(
            lon[:, i],
            lat[:, i],
            color="black",
            linewidth=0.5,
            transform=ccrs.PlateCarree(),
        )

    ax1.plot(
        lon[:, -1],
        lat[:, -1],
        color="black",
        linewidth=0.5,
        transform=ccrs.PlateCarree(),
    )

    for j in range(0, lat.shape[0], skip):
        ax1.plot(
            lon[j, :],
            lat[j, :],
            color="black",
            linewidth=0.5,
            transform=ccrs.PlateCarree(),
        )

    ax1.plot(
        lon[-1, :],
        lat[-1, :],
        color="red",
        linewidth=0.8,
        transform=ccrs.PlateCarree(),
    )
    ax1.plot(
        lon[0, :],
        lat[0, :],
        color="red",
        linewidth=0.8,
        transform=ccrs.PlateCarree(),
    )
    ax1.plot(
        lon[:, -1],
        lat[:, -1],
        color="red",
        linewidth=0.8,
        transform=ccrs.PlateCarree(),
    )
    ax1.plot(
        lon[:, 0],
        lat[:, 0],
        color="red",
        linewidth=0.8,
        transform=ccrs.PlateCarree(),
    )

    ax1.set_title("Approx. Grid (~1/10th Density)", fontsize=10)
    gl = ax1.gridlines(
        draw_labels=True,
        lw=0.5,
        color="gray",
        alpha=0.5,
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 8}
    gl.ylabel_style = {"size": 8}

    # ----------------------------- #
    # Final plot with land-sea mask #
    # ----------------------------- #

    ax2 = fig.add_subplot(
        1,
        3,
        3,
        projection=ccrs.PlateCarree(central_longitude=central_longitude),
    )
    plot_2D_latlon_field_plot(
        field=grd_xr["wet"],
        grid=grd_xr,
        axis=ax2,
        annotate=False,
        colormap=ListedColormap(["tan", "cornflowerblue"]),
        coast_linewidth=0.2,
        add_cbar=False,
    )
    pm = ax2.set_title("Land/Ocean Mask", fontsize=10)
    pm.sticky_edges.x[:] = []
    pm.sticky_edges.y[:] = []
    ax2.margins(x=0.05, y=0.05)
    # ax2.legend([color = '')

    fig.subplots_adjust(wspace=0.2)

    if save is not None:
        plt.savefig(save)
        plt.close()


def create_2d_field_animation(
    da,
    grid,
    time_dim="time",
    interval=200,
    verbose=False,
    **kwargs,
):

    plot_kwargs = kwargs.copy()
    base_title = da.long_name

    field_t0 = da.isel({time_dim: 0}).to_numpy()
    pm = plot_2D_latlon_field_plot(
        field=field_t0,
        grid=grid,
        show=False,
        **plot_kwargs,
    )

    fig = pm.figure
    axis = pm.axes

    plt.close()

    def update(i):
        field_at_time_i = da.isel({time_dim: i}).to_numpy()

        pm.set_array(field_at_time_i.ravel())

        try:
            import pandas as pd

            time_step = da[time_dim].isel({time_dim: i})
            time_str = pd.to_datetime(str(time_step.values)).strftime("%Y-%m-%d")
        except (ImportError, ValueError):
            time_str = f"Frame {i}"

        axis.set_title(
            f"{base_title}\n{time_str}",
            fontsize=plot_kwargs.get("fontsize", 22) * 1.5,
        )

        if verbose:
            print(f"Processing frame {i+1}/{len(da[time_dim])}", end="\r")

        return (pm,)

    num_frames = len(da[time_dim])
    anim = FuncAnimation(
        fig,
        update,
        frames=num_frames,
        interval=interval,
        blit=False,
    )

    if verbose:
        print("\nAnimation object created successfully.")
    return anim


def plot_area_averaged_timeseries(sfc_data, static_data, variables):

    valid_variables = [v for v in variables if v in sfc_data]
    if not valid_variables:
        print("ERROR: None of the requested variables were found in the dataset.")
        return

    n_vars = len(valid_variables)

    fig, axes = plt.subplots(
        nrows=n_vars,
        ncols=1,
        figsize=(12, 4 * n_vars),
        sharex=True,
        squeeze=False,
    )

    weights = static_data["areacello"]
    if "time" in weights.dims:
        weights = weights.isel(time=0, drop=True)

    for i, var_name in enumerate(valid_variables):
        ax = axes[i, 0]
        da = sfc_data[var_name]

        spatial_dims = [dim for dim in da.dims if dim != "time"]
        area_avg_da = da.weighted(weights).mean(dim=spatial_dims)
        area_avg_da.plot(ax=ax)

        long_name = da.attrs.get("long_name", var_name)
        units = da.attrs.get("units", "unitless")

        ax.set_title(long_name, fontsize=14)
        ax.set_ylabel(units, fontsize=12)
        ax.set_xlabel("")
        ax.grid(True, linestyle="--", alpha=0.6)

    fig.suptitle("Area-Averaged Time Series", fontsize=18, y=1.02)
    axes[-1, 0].set_xlabel("Time", fontsize=12)

    plt.tight_layout(rect=[0, 0, 1, 1])
    plt.show()
