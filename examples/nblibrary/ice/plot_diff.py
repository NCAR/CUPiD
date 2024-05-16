from __future__ import annotations

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec


def plot_diff(field1, field2, levels, case1, case2, title, proj, TLAT, TLON):
    # make circular boundary for polar stereographic circular plots
    theta = np.linspace(0, 2 * np.pi, 100)
    center, radius = [0.5, 0.5], 0.5
    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
    circle = mpath.Path(verts * radius + center)

    if np.size(levels) > 2:
        cmap = mpl.colormaps["tab20"]
        norm = mpl.colors.BoundaryNorm(levels, ncolors=cmap.N)

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

    field_diff = field2.values - field1.values
    field_std = field_diff.std()

    this = ax.pcolormesh(
        TLON,
        TLAT,
        field1,
        norm=norm,
        cmap="tab20",
        transform=ccrs.PlateCarree(),
    )
    plt.colorbar(this, orientation="vertical", fraction=0.04, pad=0.01)
    plt.title(case1, fontsize=10)

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
        field2,
        norm=norm,
        cmap="tab20",
        transform=ccrs.PlateCarree(),
    )
    plt.colorbar(this, orientation="vertical", fraction=0.04, pad=0.01)
    plt.title(case2, fontsize=10)

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
        field_diff,
        cmap="seismic",
        vmax=field_std * 2.0,
        vmin=-field_std * 2.0,
        transform=ccrs.PlateCarree(),
    )
    plt.colorbar(this, orientation="vertical", fraction=0.04, pad=0.01)
    plt.title(case2 + "-" + case1, fontsize=10)

    plt.suptitle(title)
