from __future__ import annotations

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec


def vect_diff(
    case_names,
    case_info,
    angle,
    proj,
    TLAT,
    TLON,
):

    # Use first case as reference/base case
    ref_case_name = case_names[0]
    ref_case_nickname = case_info[ref_case_name]["case_nickname"]
    ref_case_data = case_info[ref_case_name]
    ref_ds = ref_case_data["ds"]
    ref_climo_nyears = ref_case_data["climo_nyears"]

    uvel1 = (
        ref_ds["uvel"]
        .isel(time=slice(-ref_climo_nyears * 12, None))
        .mean("time")
        .values
    )
    vvel1 = (
        ref_ds["vvel"]
        .isel(time=slice(-ref_climo_nyears * 12, None))
        .mean("time")
        .values
    )
    mask1 = (
        ref_ds["aice"]
        .isel(time=slice(-ref_climo_nyears * 12, None))
        .mean("time")
        .values
    )

    # make circular boundary for polar stereographic circular plots
    theta = np.linspace(0, 2 * np.pi, 100)
    center, radius = [0.5, 0.5], 0.5
    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
    circle = mpath.Path(verts * radius + center)

    # set up the figure with a North Polar Stereographic projection
    fig = plt.figure()
    ncases = len(case_names)
    gs = GridSpec(2, ncases * 2 + 1)

    if proj == "N":
        ax = fig.add_subplot(gs[0, :2], projection=ccrs.NorthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
        title = "NH Velocity m/s"
    if proj == "S":
        ax = fig.add_subplot(gs[0, :2], projection=ccrs.SouthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())
        title = "SH Velocity m/s"

    ax.set_boundary(circle, transform=ax.transAxes)
    ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

    # plot ref case first

    uvel_rot1 = uvel1 * np.cos(angle) - vvel1 * np.sin(angle)
    vvel_rot1 = uvel1 * np.sin(angle) + vvel1 * np.cos(angle)
    speed1_tmp = np.sqrt(uvel1 * uvel1 + vvel1 * vvel1)
    speed1 = np.where(mask1 > 0.01, speed1_tmp, np.nan)

    cmap = mpl.colormaps["ocean"]
    levels = mpl.ticker.MaxNLocator(nbins=10).tick_values(0.0, 0.2)
    norm = mpl.colors.BoundaryNorm(levels, ncolors=cmap.N)

    this = ax.pcolormesh(
        TLON,
        TLAT,
        speed1,
        norm=norm,
        cmap="ocean",
        transform=ccrs.PlateCarree(),
    )
    plt.title(ref_case_nickname, fontsize=10)

    intv = 10
    # add vectors
    Q = ax.quiver(
        TLON[::intv, ::intv],
        TLAT[::intv, ::intv],
        uvel_rot1[::intv, ::intv],
        vvel_rot1[::intv, ::intv],
        color="black",
        scale=1.0,
        transform=ccrs.PlateCarree(),
    )

    n = 0
    for case_name, case_data in list(case_info.items())[1:]:
        ds = case_data["ds"]
        case_nickname = case_data["case_nickname"]
        climo_nyears = case_data["climo_nyears"]

        n = n + 2
        if proj == "N":
            ax = fig.add_subplot(gs[0, n : n + 2], projection=ccrs.NorthPolarStereo())
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
        if proj == "S":
            ax = fig.add_subplot(gs[0, n : n + 2], projection=ccrs.SouthPolarStereo())
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

        ax.set_boundary(circle, transform=ax.transAxes)
        ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

        uvel2 = (
            ds["uvel"]
            .isel(time=slice(-ref_climo_nyears * 12, None))
            .mean("time")
            .values
        )
        vvel2 = (
            ds["vvel"]
            .isel(time=slice(-ref_climo_nyears * 12, None))
            .mean("time")
            .values
        )
        mask2 = (
            ds["aice"]
            .isel(time=slice(-ref_climo_nyears * 12, None))
            .mean("time")
            .values
        )

        uvel_rot2 = uvel2 * np.cos(angle) - vvel2 * np.sin(angle)
        vvel_rot2 = uvel2 * np.sin(angle) + vvel2 * np.cos(angle)

        speed2_tmp = np.sqrt(uvel2 * uvel2 + vvel2 * vvel2)
        speed2 = np.where(mask2 > 0.01, speed2_tmp, np.nan)

        this = ax.pcolormesh(
            TLON,
            TLAT,
            speed2,
            norm=norm,
            cmap="ocean",
            transform=ccrs.PlateCarree(),
        )
        plt.title(case_nickname, fontsize=10)

        # add vectors
        Q = ax.quiver(
            TLON[::intv, ::intv],
            TLAT[::intv, ::intv],
            uvel_rot2[::intv, ::intv],
            vvel_rot2[::intv, ::intv],
            color="black",
            scale=1.0,
            transform=ccrs.PlateCarree(),
        )

    units = "cm/s"
    ax.quiverkey(
        Q,
        0.85,
        0.025,
        0.10,
        r"10 " + units,
        labelpos="S",
        coordinates="axes",
        color="black",
        zorder=2,
    )

    pos = gs[0, n + 2].get_position(fig)
    shrink_h, shrink_w = 0.8, 0.4
    new_height = pos.height * shrink_h
    new_width = pos.width * shrink_w
    cbar_ax = fig.add_axes(
        [
            pos.x0,
            pos.y0 + new_height / 4,
            new_width,
            new_height,
        ],
    )
    plt.colorbar(this, orientation="vertical", cax=cbar_ax)

    n = 0
    for case_name, case_data in list(case_info.items())[1:]:
        ds = case_data["ds"]
        case_nickname = case_data["case_nickname"]
        climo_nyears = case_data["climo_nyears"]

        n = n + 2

        if proj == "N":
            ax = fig.add_subplot(
                gs[1, n - 1 : n + 1],
                projection=ccrs.NorthPolarStereo(),
            )
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
        if proj == "S":
            ax = fig.add_subplot(
                gs[1, n - 1 : n + 1],
                projection=ccrs.SouthPolarStereo(),
            )
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

        ax.set_boundary(circle, transform=ax.transAxes)
        ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

        uvel2 = (
            ds["uvel"]
            .isel(time=slice(-ref_climo_nyears * 12, None))
            .mean("time")
            .values
        )
        vvel2 = (
            ds["vvel"]
            .isel(time=slice(-ref_climo_nyears * 12, None))
            .mean("time")
            .values
        )
        mask2 = (
            ds["aice"]
            .isel(time=slice(-ref_climo_nyears * 12, None))
            .mean("time")
            .values
        )

        uvel_rot2 = uvel2 * np.cos(angle) - vvel2 * np.sin(angle)
        vvel_rot2 = uvel2 * np.sin(angle) + vvel2 * np.cos(angle)

        speed2_tmp = np.sqrt(uvel2 * uvel2 + vvel2 * vvel2)
        speed2 = np.where(mask2 > 0.01, speed2_tmp, np.nan)

        uvel_diff = uvel_rot1 - uvel_rot2
        vvel_diff = vvel_rot1 - vvel_rot2
        speed_diff = speed1 - speed2

        cmap = mpl.colormaps["coolwarm"]
        diff_levels = mpl.ticker.MaxNLocator(nbins=10).tick_values(-0.2, 0.2)
        norm = mpl.colors.BoundaryNorm(diff_levels, ncolors=cmap.N)

        this = ax.pcolormesh(
            TLON,
            TLAT,
            speed_diff,
            norm=norm,
            cmap="coolwarm",
            transform=ccrs.PlateCarree(),
        )
        plt.title(ref_case_nickname + "-" + case_nickname, fontsize=10)

        # add vectors
        Q = ax.quiver(
            TLON[::intv, ::intv],
            TLAT[::intv, ::intv],
            uvel_diff[::intv, ::intv],
            vvel_diff[::intv, ::intv],
            color="black",
            scale=0.2,
            transform=ccrs.PlateCarree(),
        )

    units = "cm/s"
    ax.quiverkey(
        Q,
        0.85,
        0.025,
        0.05,
        r"5 " + units,
        labelpos="S",
        coordinates="axes",
        color="black",
        zorder=2,
    )

    pos = gs[1, n + 1].get_position(fig)
    shrink_h, shrink_w = 0.8, 0.4
    new_height = pos.height * shrink_h
    new_width = pos.width * shrink_w
    cbar_ax = fig.add_axes(
        [
            pos.x0,
            pos.y0 + new_height / 4,
            new_width,
            new_height,
        ],
    )
    plt.colorbar(this, orientation="vertical", cax=cbar_ax)

    plt.suptitle(title)
