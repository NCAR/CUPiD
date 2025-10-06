from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from cartopy import crs as ccrs
from cartopy import feature as cfeature
from matplotlib.animation import FuncAnimation
from matplotlib.colors import BoundaryNorm
from matplotlib.colors import ListedColormap
from matplotlib.colors import LogNorm
from matplotlib.ticker import MaxNLocator

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


def chooseColorMap(var):
    """
    Based on the variable being plotted, choose variable.
    """
    try:
        import cmocean

        if var in ["thetao", "temp", "tos", "SST", "hfds"]:
            return cmocean.cm.thermal
        elif var in ["speed"]:
            return cmocean.cm.speed
        elif var in ["SSS", "sos", "salt", "so"]:
            return cmocean.cm.haline
        elif var in ["SSH", "ssh", "h", "e"]:
            return cmocean.cm.balance
        elif var in ["uo", "vo", "SSV", "SSU", "u", "v", "tauuo", "tauvo"]:
            return cmocean.cm.delta
        else:
            return cmocean.cm.balance
    except ImportError:
        return plt.get_cmap("gist_ncar")


def chooseColorLevels(
    sMin,
    sMax,
    colorMap,
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

    cmap = colorMap  # ,lut=nColors+eColors[0]+eColors[1])

    if logscale:
        norm = LogNorm(vmin=levels[0], vmax=levels[-1])
    else:
        norm = BoundaryNorm(levels, ncolors=cmap.N)
    return cmap, norm, extend


def oceanStats2D(
    field: xr.DataArray,
    area_weights: xr.DataArray = None,
    lsm_2D: xr.DataArray = None,
    lat_var: str = "latitude",
    lon_var: str = "longitude",
):
    """
    Compute area-weighted mean and standard deviation for an ocean field.
    """
    if lat_var in field.dims and lon_var in field.dims and len(field.dims) > 2:
        raise Exception(
            "Field must be 2D in lat and lon with no time variable. \
                        Select a time if field is 2D. If Field is 3D, \
                        select a level or use oceanStats3D.",
        )

    min = field.min(skipna=True).compute().item()
    max = field.max(skipna=True).compute().item()

    weighted_field = field.weighted(area_weights * lsm_2D)

    mean = weighted_field.mean(skipna=True).compute().item()
    std_dev = weighted_field.std(skipna=True).compute().item()

    stats = {"max": max, "min": min, "mean": mean, "std_dev": std_dev}

    return stats


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
    area_var="areacello",
    lsm_var="wet",
    lon_var="geolon",
    lat_var="geolat",
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
    save_fig=None,
    save_path=".",
    debug=False,
    show=True,
    logscale=False,
    projection=None,
    coastlines=True,
    res=None,
    coastcolor=[0, 0, 0],
    landcolor=[0.75, 0.75, 0.75],
    coast_linewidth=0.3,
    fontsize=22,
    gridlines=False,
    find_stats=True,
):
    # Preplotting
    plt.rc("font", size=fontsize)

    if find_stats:
        # Diagnose statistics
        area_cell = grid[area_var]
        lsm = grid[lsm_var]

        stats = oceanStats2D(field, area_cell, lsm)
        sMin, sMax, sMean, sStd = (
            stats["min"],
            stats["max"],
            stats["mean"],
            stats["std_dev"],
        )

    # Choose colormap
    if nbins is None and (clim is None or len(clim) == 2):
        nbins = 35
    if colormap is None:
        colormap = chooseColorMap(field.name)
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
        cb = fig.colorbar(pm, cax=cbar_ax, extend=extend)
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
        annotation = f"Max: {stats['max']:.3f}, Min: {stats['min']:.3f} \nMean: \
            {stats['mean']:.3f}, Std Dev: {stats['std_dev']:.3f}"
        axis.annotate(
            annotation,
            xy=(0.5, -0.05),
            xycoords="axes fraction",
            ha="center",
            va="top",
            fontsize=10,
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
    if save_fig:
        plt.savefig(os.path.join(save_path, f"field_plot_{field.name}.png"))
    plt.close()

    return pm


def visualize_regional_domain(
    grd_xr,
    save=None,
):
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
        find_stats=False,
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
    lat_var="geolat",
    lon_var="geolon",
    area_var="areacello",
    lsm_var="wet",
    time_dim="time",
    interval=200,
    verbose=False,
):

    base_title = da.long_name

    field_t0 = da.isel({time_dim: 0})
    pm = plot_2D_latlon_field_plot(
        field=field_t0,
        grid=grid,
        lat_var=lat_var,
        lon_var=lon_var,
        area_var=area_var,
        lsm_var=lsm_var,
        show=False,
        find_stats=True,
        add_cbar=False,
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
            fontsize=22,
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


def plot_area_averaged_timeseries(
    data,
    weights,
    variables,
    save_fig=False,
    save_path=".",
):

    valid_variables = [v for v in variables if v in data]
    if not valid_variables:
        print("ERROR: None of the requested variable(s) were found in the dataset.")
        return

    n_vars = len(valid_variables)

    fig, axes = plt.subplots(
        nrows=n_vars,
        ncols=1,
        figsize=(12, 4 * n_vars),
        sharex=True,
        squeeze=False,
    )

    for i, var_name in enumerate(valid_variables):
        ax = axes[i, 0]
        da = data[var_name]

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
    if save_fig:
        plt.savefig(os.path.join(save_path, "area_avg_timeseries.png"))
