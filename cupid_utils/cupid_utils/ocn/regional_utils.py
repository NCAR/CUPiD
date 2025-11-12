from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from cartopy import crs as ccrs
from cartopy import feature as cfeature
from matplotlib.animation import FuncAnimation

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

plt.rcParams["figure.dpi"] = 200
plt.rcParams["savefig.dpi"] = 300


def chooseGeoCoords(dimensions):
    if "xh" in dimensions and "yh" in dimensions:
        lon_var = "geolon"
        lat_var = "geolat"
    elif "xq" in dimensions and "yq" in dimensions:
        lon_var = "geolon_c"
        lat_var = "geolat_c"
    elif "xq" in dimensions and "yh" in dimensions:
        lon_var = "geolon_u"
        lat_var = "geolat_u"
    elif "xh" in dimensions and "yq" in dimensions:
        lon_var = "geolon_v"
        lat_var = "geolat_v"
    else:
        raise ValueError(f"Could not determine geocoords for dims: {dimensions}")
    return {"longitude": lon_var, "latitude": lat_var}


def chooseAreacello(dimensions):
    if "xh" in dimensions and "yh" in dimensions:
        area_var = "areacello"
    elif "xq" in dimensions and "yq" in dimensions:
        area_var = "areacello_bu"
    elif "xq" in dimensions and "yh" in dimensions:
        area_var = "areacello_cu"
    elif "xh" in dimensions and "yq" in dimensions:
        area_var = "areacello_cv"
    else:
        raise ValueError(f"Could not determine areacello for dims: {dimensions}")
    return area_var


def chooseWetMask(dimensions):
    if "xh" in dimensions and "yh" in dimensions:
        wet_var = "wet"
    elif "xq" in dimensions and "yq" in dimensions:
        wet_var = "wet_c"
    elif "xq" in dimensions and "yh" in dimensions:
        wet_var = "wet_u"
    elif "xh" in dimensions and "yq" in dimensions:
        wet_var = "wet_v"
    else:
        raise ValueError(f"Could not determine wet mask for dims: {dimensions}")
    return wet_var


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


def chooseColorLevels(sMin, sMax, sMean=None, sStd=None, sigma_cbar=True):
    """
    Choose color levels for plotting based on min, max, mean, and std dev.
    sigma_cbar: if True, uses [mean - 2*std, mean + 2*std] as bounds, clipped to [min, max].
    Returns levels (numpy array).
    """
    if sMean is None or sStd is None:
        levels = np.linspace(sMin, sMax, 35)
        return levels
    if sigma_cbar:
        lower = max(sMin, sMean - 2 * sStd)
        upper = min(sMax, sMean + 2 * sStd)
        levels = np.linspace(lower, upper, 35)
    else:
        levels = np.linspace(sMin, sMax, 35)
    return levels


def oceanStats2D(
    field: xr.DataArray,
    area_weights: xr.DataArray = None,
):
    """
    Compute area-weighted mean and standard deviation for an ocean field.
    """
    if len(field.dims) > 2:
        raise Exception(
            "Field must be 2D in lat and lon with no time variable. \
                        Select a time if field is 2D. If Field is 3D, \
                        select a level or use oceanStats3D.",
        )

    min = field.min(skipna=True).compute().item()
    max = field.max(skipna=True).compute().item()

    # MOM6 output puts NaNs over land, which mean automatically ignores
    weighted_field = field.weighted(area_weights)

    mean = weighted_field.mean().compute().item()
    std_dev = weighted_field.std().compute().item()

    stats = {"max": max, "min": min, "mean": mean, "std_dev": std_dev}

    return stats


def oceanStats3D(
    field: xr.DataArray,
    volume_weights: xr.DataArray = None,
):
    if len(field.dims) > 3:
        raise Exception(
            "Field must be 3D with lat, lon, and levels with no time variable.",
        )

    min = field.min(skipna=True).compute().item()
    max = field.max(skipna=True).compute().item()

    weighted_field = field.weighted(volume_weights)

    mean = weighted_field.mean(skipna=True).compute().item()
    std_dev = weighted_field.std(skipna=True).compute().item()

    stats = {"max": max, "min": min, "mean": mean, "std_dev": std_dev}

    return stats


def statsToAnnotation(stats: dict):
    """
    Convert stats dictionary to annotation string.

    Args:
        stats (dict): Dictionary containing statistical information.

    Returns:
        str: Formatted annotation string.
    """
    annotation = f"Max: {stats['max']:.3f}, Min: {stats['min']:.3f} \n"
    annotation += f"Mean: {stats['mean']:.3f}, Std Dev: {stats['std_dev']:.3f}"
    return annotation


def plotLatLonField(
    field: xr.DataArray,
    latitude: xr.DataArray,
    longitude: xr.DataArray,
    stats: bool = False,
    area_weights: xr.DataArray = None,
    projection: ccrs.Projection = ccrs.PlateCarree(),
    levels: np.linspace = None,
    ax: plt.Axes = None,
    show: bool = True,
    save: bool = False,
    save_path: str = None,
):
    """
    Wrap basic xr.DataArray.plot functionality with projection options and stats.

    Args:
        field (xr.DataArray): _description_
        lat (xr.DataArray): _description_
        lon (xr.DataArray): _description_
        stats (bool, optional): _description_. Defaults to False.
        area_weights (xr.DataArray, optional): _description_. Defaults to None.
        projection (_type_, optional): _description_. Defaults to ccrs.PlateCarree().
    """
    # Assign lat lon as coords to field_plot
    field_plot = field.assign_coords(latitude=latitude, longitude=longitude)

    # Colorbar Selection
    cmap = chooseColorMap(field.name)
    if levels is None:
        levels = chooseColorLevels(
            field.min().compute().item(),
            field.max().compute().item(),
        )

    # Check if we want to calculate stats
    if stats:
        if area_weights is None:
            raise Exception("Area weights must be provided to calculate stats.")
        field_stats = oceanStats2D(field, area_weights)
        annotation = statsToAnnotation(field_stats)

    # Set up subplot_kws
    if ax is None:
        subplot_kws = {"projection": projection, "facecolor": "lightgray"}
    else:
        subplot_kws = None

    # Create the plot
    p = field_plot.plot(
        x="longitude",
        y="latitude",
        ax=ax,
        cmap=cmap,
        levels=levels,
        add_colorbar=True,
        transform=ccrs.PlateCarree(),
        subplot_kws=subplot_kws,
    )

    # Apply annotations
    if stats:
        p.axes.annotate(
            annotation,
            xy=(0.5, -0.07),
            xycoords="axes fraction",
            ha="center",
            va="top",
            fontsize=10,
        )

    # Add coastlines, gridlines, and suptitle
    p.axes.coastlines(resolution="50m", color="black", linewidth=0.3)

    gl = p.axes.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 8}
    gl.ylabel_style = {"size": 8}

    long_name = field.long_name if "long_name" in field.attrs else field.name
    if len(long_name) > 50:
        suptitle = field.name
    else:
        suptitle = long_name
    suptitle += f" [{field.units}]" if "units" in field.attrs else ""
    plt.suptitle(suptitle, y=0.95, fontsize=16)

    if save:
        if save_path is None:
            print("Save path not provided, saving to current directory.")
            plt.savefig(f"{field.name}.png", dpi=300)
        else:
            plt.savefig(os.path.join(save_path, f"{field.name}.png"), dpi=300)

    if show is False:
        plt.close()

    return p


def visualizeRegionalDomain(
    static_data: xr.Dataset,
    show: bool = True,
    save: bool = False,
    save_path: str = None,
):
    # Grab useful variables
    central_longitude = float(
        (static_data["geolon"].max().values + static_data["geolon"].min().values) / 2,
    )
    lon = static_data["geolon_c"].values
    lat = static_data["geolat_c"].values

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

    # Final plot with land-sea mask #
    ax2 = fig.add_subplot(
        1,
        3,
        3,
        projection=ccrs.PlateCarree(central_longitude=central_longitude),
    )
    static_data["wet"].plot(
        ax=ax2,
        cmap="Blues",
        add_colorbar=False,
        transform=ccrs.PlateCarree(),
        facecolor="lightgray",
    )
    pm = ax2.set_title("Land/Ocean Mask", fontsize=10)
    pm.sticky_edges.x[:] = []
    pm.sticky_edges.y[:] = []
    ax2.margins(x=0.05, y=0.05)
    ax2.coastlines(linewidth=0.3, resolution="50m")
    # ax2.legend([color = '')

    fig.subplots_adjust(wspace=0.2)

    if save:
        if save_path is None:
            print("Save path not provided, saving to current directory.")
            plt.savefig("visualize_regional_domain.png.png", dpi=300)
        else:
            plt.savefig(
                os.path.join(save_path, "visualize_regional_domain.png"),
                dpi=300,
            )

    if show is False:
        plt.close()
    else:
        plt.show()


def create2DFieldAnimation(
    field: xr.DataArray,
    latitude: xr.DataArray,
    longitude: xr.DataArray,
    iter_dim: str = "time",
    interval: int = 200,
    verbose: bool = False,
    save: bool = False,
    save_path: str = None,
):
    """
    Create an animation of a 2D field over a specified dimension (e.g., time or depth).
    Uses plotLatLonField for plotting.
    """
    # Initial field for plotting
    field0 = field.isel({iter_dim: 0})

    levels = np.linspace(field.min().compute().item(), field.max().compute().item(), 35)

    # Create initial plot using plotLatLonField
    plt.ioff()  # Turn off interactive mode for animation
    fig = plt.figure()
    p = plotLatLonField(
        field0,
        latitude=latitude,
        longitude=longitude,
        stats=False,
        levels=levels,
        ax=None,
        show=False,
        save=False,
    )
    im = p
    ax = p.axes

    plt.close(fig)  # Prevent duplicate display in notebooks

    def update(i):
        field_i = field.isel({iter_dim: i})
        im.set_array(field_i.values.flatten())
        try:
            import pandas as pd

            label_val = field[iter_dim].isel({iter_dim: i}).values
            if np.issubdtype(type(label_val), np.datetime64):
                time_str = pd.to_datetime(str(label_val)).strftime("%Y-%m-%d")
            else:
                time_str = str(label_val)
        except Exception:
            time_str = f"{iter_dim}={i}"
        ax.set_title(f"{field.name} [{iter_dim}: {time_str}]", fontsize=14)
        if verbose:
            print(f"Frame {i+1}/{field.sizes[iter_dim]}", end="\r")
        return (im,)

    n_frames = field.sizes[iter_dim]
    anim = FuncAnimation(
        fig,
        update,
        frames=n_frames,
        interval=interval,
        blit=False,
    )

    if verbose:
        print("\nAnimation object created successfully.")

    # Save the animation if requested
    if save:
        if save_path is None:
            print("Save path not provided, saving to current directory.")
            anim.save(f"{field.name}_animation.gif", writer="pillow")
        else:
            anim.save(
                os.path.join(save_path, f"{field.name}_animation.gif"),
                writer="pillow",
            )
        if verbose:
            print(f"Animation saved to {save_path if save_path else os.getcwd()}")

    return anim


def plotAvgTimeseries(
    field: xr.DataArray,
    weights: xr.DataArray,
    save: bool = False,
    save_path: str = None,
    show: bool = True,
):
    """
    Plot a time series of the area-weighted average of a 2D field.

    Args:
        field (xr.DataArray): 2D field with time dimension.
        weights (xr.DataArray): Area weights for the field.
        save (bool, optional): Whether to save the plot. Defaults to False.
        save_path (str, optional): Path to save the plot. Defaults to None.
    """
    if "time" not in field.dims:
        raise ValueError("Field must have a time dimension.")

    avg_dims = [dim for dim in field.dims if dim != "time"]

    # Compute area-weighted average over all spatial dimensions
    weighted_field = field.weighted(weights)
    ts_avg = weighted_field.mean(dim=avg_dims)

    # Create the plot
    ts_avg.plot(subplot_kws={"title": f"Area-Weighted Mean {field.name}"})

    if save:
        if save_path is None:
            print("Save path not provided, saving to current directory.")
            plt.savefig(f"{field.name}_{len(ts_avg)}D_timeseries.png", dpi=300)
        else:
            plt.savefig(
                os.path.join(save_path, f"{field.name}_{len(ts_avg)}D_timeseries.png"),
                dpi=300,
            )
    if not show:
        plt.close()
    else:
        plt.show()
