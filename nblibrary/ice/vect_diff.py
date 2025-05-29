from __future__ import annotations

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec


def vect_diff(uvel1, vvel1, uvel2, vvel2, angle, proj, case1, case2, TLAT, TLON):
    uvel_rot1 = uvel1 * np.cos(angle) - vvel1 * np.sin(angle)
    vvel_rot1 = uvel1 * np.sin(angle) + vvel1 * np.cos(angle)
    uvel_rot2 = uvel2 * np.cos(angle) - vvel2 * np.sin(angle)
    vvel_rot2 = uvel2 * np.sin(angle) + vvel2 * np.cos(angle)

    speed1 = np.sqrt(uvel1 * uvel1 + vvel1 * vvel1)
    speed2 = np.sqrt(uvel2 * uvel2 + vvel2 * vvel2)

    uvel_diff = uvel_rot2 - uvel_rot1
    vvel_diff = vvel_rot2 - vvel_rot1
    speed_diff = speed2 - speed1

    # make circular boundary for polar stereographic circular plots
    theta = np.linspace(0, 2 * np.pi, 100)
    center, radius = [0.5, 0.5], 0.5
    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
    circle = mpath.Path(verts * radius + center)

    # set up the figure with a North Polar Stereographic projection
    fig = plt.figure(tight_layout=True)
    gs = GridSpec(2, 4)

    if proj == "N":
        ax = fig.add_subplot(gs[0, :2], projection=ccrs.NorthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
    if proj == "S":
        ax = fig.add_subplot(gs[0, :2], projection=ccrs.SouthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

    ax.set_boundary(circle, transform=ax.transAxes)
    ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

    this = ax.pcolormesh(
        TLON,
        TLAT,
        speed1,
        vmin=0.0,
        vmax=0.5,
        cmap="ocean",
        transform=ccrs.PlateCarree(),
    )
    plt.colorbar(this, orientation="vertical", fraction=0.04, pad=0.01)
    plt.title(case1, fontsize=10)

    intv = 5
    # add vectors
    Q = ax.quiver(
        TLON.values[::intv, ::intv],
        TLAT.values[::intv, ::intv],
        uvel_rot1.values[::intv, ::intv],
        vvel_rot1.values[::intv, ::intv],
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

    if proj == "N":
        ax = fig.add_subplot(gs[0, 2:], projection=ccrs.NorthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
    if proj == "S":
        ax = fig.add_subplot(gs[0, 2:], projection=ccrs.SouthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

    ax.set_boundary(circle, transform=ax.transAxes)
    ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

    this = ax.pcolormesh(
        TLON,
        TLAT,
        speed2,
        vmin=0.0,
        vmax=0.5,
        cmap="ocean",
        transform=ccrs.PlateCarree(),
    )
    plt.colorbar(this, orientation="vertical", fraction=0.04, pad=0.01)
    plt.title(case1, fontsize=10)

    intv = 5
    # add vectors
    Q = ax.quiver(
        TLON.values[::intv, ::intv],
        TLAT.values[::intv, ::intv],
        uvel_rot2.values[::intv, ::intv],
        vvel_rot2.values[::intv, ::intv],
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

    if proj == "N":
        ax = fig.add_subplot(gs[1, 1:3], projection=ccrs.NorthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
    if proj == "S":
        ax = fig.add_subplot(gs[1, 1:3], projection=ccrs.SouthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

    ax.set_boundary(circle, transform=ax.transAxes)
    ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

    this = ax.pcolormesh(
        TLON,
        TLAT,
        speed_diff,
        vmin=-0.2,
        vmax=0.2,
        cmap="seismic",
        transform=ccrs.PlateCarree(),
    )
    plt.colorbar(this, orientation="vertical", fraction=0.04, pad=0.01)
    plt.title(case2 + "-" + case1, fontsize=10)

    intv = 5
    # add vectors
    Q = ax.quiver(
        TLON.values[::intv, ::intv],
        TLAT.values[::intv, ::intv],
        uvel_diff.values[::intv, ::intv],
        vvel_diff.values[::intv, ::intv],
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

    plt.suptitle("Velocity m/s")
