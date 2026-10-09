from __future__ import annotations

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.gridspec import GridSpec


def plot_diff(
    case_names,
    case_info,
    var,
    levels,
    title,
    hem,
    month,
    TLAT,
    TLON,
    path_HadleyOI,
):

    # Use first case as reference/base case
    ref_case_name = case_names[0]
    ref_case_nickname = case_info[ref_case_name]["case_nickname"]
    ref_case_data = case_info[ref_case_name]
    ref_ds = ref_case_data["ds"]
    ref_climo_nyears = ref_case_data["climo_nyears"]

    # Base/reference field
    if var in ref_ds:
        field1 = ref_ds[var].isel(time=slice(-ref_climo_nyears * 12, None))
    else:
        field1 = ref_ds["aice"].isel(time=slice(-ref_climo_nyears * 12, None)) * 0.0

    mask1 = ref_ds["aice"].isel(time=slice(-ref_climo_nyears * 12, None))

    # make circular boundary for polar stereographic circular plots
    theta = np.linspace(0, 2 * np.pi, 100)
    center, radius = [0.5, 0.5], 0.5
    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
    circle = mpath.Path(verts * radius + center)

    # Read in observed sea ice concentration

    ds_obs = xr.open_dataset(path_HadleyOI + "sst_HadOIBl_bc_1x1_climo_1980_2019.nc")

    aice = title.find("Concentration")

    if np.size(levels) > 2:
        cmap = mpl.colormaps["ocean"]
        norm = mpl.colors.BoundaryNorm(levels, ncolors=cmap.N)

    # set up the figure with a Polar Stereographic projection
    fig = plt.figure()
    ncases = len(case_names)
    gs = GridSpec(2, ncases * 2 + 1)

    if hem == "N":
        ax = fig.add_subplot(gs[0, 0:2], projection=ccrs.NorthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
    if hem == "S":
        ax = fig.add_subplot(gs[0, 0:2], projection=ccrs.SouthPolarStereo())
        # sets the latitude / longitude boundaries of the plot
        ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

    ifrac_obs = ds_obs.ice_cov_prediddle.isel(month=month)
    field1_tmp2 = field1.sel(time=(field1.time.dt.month == month)).mean(dim="time")
    mask1_tmp = mask1.sel(time=(field1.time.dt.month == month)).mean(dim="time")

    field1_tmp = np.where(mask1_tmp > 0.01, field1_tmp2, np.nan)

    del mask1_tmp

    ax.set_boundary(circle, transform=ax.transAxes)
    ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

    this = ax.pcolormesh(
        TLON.values,
        TLAT.values,
        field1_tmp,
        norm=norm,
        cmap="ocean",
        transform=ccrs.PlateCarree(),
    )
    if aice > 0:
        plt.contour(
            ds_obs.lon.values,
            ds_obs.lat.values,
            ifrac_obs.values,
            levels=[0.15],
            colors="magenta",
            transform=ccrs.PlateCarree(),
        )
    plt.title(ref_case_nickname, fontsize=10)

    n = 0
    for case_name, case_data in list(case_info.items())[1:]:
        ds = case_data["ds"]
        case_nickname = case_data["case_nickname"]
        climo_nyears = case_data["climo_nyears"]

        # Comparison field
        if var in ds:
            field2 = ds[var].isel(time=slice(-climo_nyears * 12, None))
        else:
            field2 = ds["aice"].isel(time=slice(-climo_nyears * 12, None)) * 0.0

        mask2 = ds["aice"].isel(time=slice(-climo_nyears * 12, None))

        n = n + 2

        if hem == "N":
            ax = fig.add_subplot(gs[0, n : n + 2], projection=ccrs.NorthPolarStereo())
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
        if hem == "S":
            ax = fig.add_subplot(gs[0, n : n + 2], projection=ccrs.SouthPolarStereo())
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

        field2_tmp2 = field2.sel(time=(field2.time.dt.month == month)).mean(dim="time")
        mask2_tmp = mask2.sel(time=(field2.time.dt.month == month)).mean(dim="time")

        field2_tmp = np.where(mask2_tmp > 0.01, field2_tmp2, np.nan)

        del mask2_tmp

        ax.set_boundary(circle, transform=ax.transAxes)
        ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

        this = ax.pcolormesh(
            TLON.values,
            TLAT.values,
            field2_tmp,
            norm=norm,
            cmap="ocean",
            transform=ccrs.PlateCarree(),
        )
        if aice > 0:
            plt.contour(
                ds_obs.lon.values,
                ds_obs.lat.values,
                ifrac_obs.values,
                levels=[0.15],
                colors="magenta",
                transform=ccrs.PlateCarree(),
            )
        plt.title(case_nickname, fontsize=10)

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

        # Comparison field
        if var in ds:
            field2 = ds[var].isel(time=slice(-climo_nyears * 12, None))
        else:
            field2 = ds["aice"].isel(time=slice(-climo_nyears * 12, None)) * 0.0

        mask2 = ds["aice"].isel(time=slice(-climo_nyears * 12, None))

        n = n + 2

        if hem == "N":
            ax = fig.add_subplot(
                gs[1, n - 1 : n + 1],
                projection=ccrs.NorthPolarStereo(),
            )
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, 90, 45], crs=ccrs.PlateCarree())
        if hem == "S":
            ax = fig.add_subplot(
                gs[1, n - 1 : n + 1],
                projection=ccrs.SouthPolarStereo(),
            )
            # sets the latitude / longitude boundaries of the plot
            ax.set_extent([0.005, 360, -90, -45], crs=ccrs.PlateCarree())

        field2_tmp2 = field2.sel(time=(field2.time.dt.month == month)).mean(dim="time")

        ax.set_boundary(circle, transform=ax.transAxes)
        ax.add_feature(cfeature.LAND, zorder=100, edgecolor="k")

        field_diff = field1_tmp2.values - field2_tmp2.values
        field_std = np.nanstd(field_diff)

        cmap = mpl.colormaps["coolwarm"]
        diff_levels = mpl.ticker.MaxNLocator(nbins=10).tick_values(
            -3.0 * field_std,
            3.0 * field_std,
        )
        norm = mpl.colors.BoundaryNorm(diff_levels, ncolors=cmap.N)

        this = ax.pcolormesh(
            TLON.values,
            TLAT.values,
            field_diff,
            norm=norm,
            cmap="coolwarm",
            transform=ccrs.PlateCarree(),
        )

        plt.title(ref_case_nickname + "-" + case_nickname, fontsize=10)

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
