from __future__ import annotations

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.gridspec import GridSpec


def add_cyclic(ds):

    ni = ds.tlon.shape[1]

    xL = int(ni / 2 - 1)
    xR = int(xL + ni)

    tlon = ds.tlon.data
    tlat = ds.tlat.data

    tlon = np.where(np.greater_equal(tlon, min(tlon[:, 0])), tlon - 360.0, tlon)
    lon = np.concatenate((tlon, tlon + 360.0), 1)
    lon = lon[:, xL:xR]

    if ni == 320:
        lon[367:-3, 0] = lon[367:-3, 0] + 360.0
    lon = lon - 360.0

    lon = np.hstack((lon, lon[:, 0:1] + 360.0))
    if ni == 320:
        lon[367:, -1] = lon[367:, -1] - 360.0

    # -- trick cartopy into doing the right thing:
    #   it gets confused when the cyclic coords are identical
    lon[:, 0] = lon[:, 0] - 1e-8

    # -- periodicity
    lat = np.concatenate((tlat, tlat), 1)
    lat = lat[:, xL:xR]
    lat = np.hstack((lat, lat[:, 0:1]))

    TLAT = xr.DataArray(lat, dims=("nlat", "nlon"))
    TLONG = xr.DataArray(lon, dims=("nlat", "nlon"))

    dso = xr.Dataset({"TLAT": TLAT, "TLONG": TLONG})
    # copy vars
    varlist = [v for v in ds.data_vars if v not in ["TLAT", "TLONG"]]
    for v in varlist:
        v_dims = ds[v].dims
        if not ("nlat" in v_dims and "nlon" in v_dims):
            dso[v] = ds[v]
        else:
            # determine and sort other dimensions
            other_dims = set(v_dims) - {"nlat", "nlon"}
            other_dims = tuple([d for d in v_dims if d in other_dims])
            lon_dim = ds[v].dims.index("nlon")
            field = ds[v].data
            field = np.concatenate((field, field), lon_dim)
            field = field[..., :, xL:xR]
            field = np.concatenate((field, field[..., :, 0:1]), lon_dim)
            dso[v] = xr.DataArray(
                field,
                dims=other_dims + ("nlat", "nlon"),
                attrs=ds[v].attrs,
            )
    # copy coords
    for v, da in ds.coords.items():
        if not ("nlat" in da.dims and "nlon" in da.dims):
            dso = dso.assign_coords(**{v: da})

    return dso


def plot_diff(field1, field2, levels, case1, case2, title, proj, TLAT, TLON):
    # make circular boundary for polar stereographic circular plots
    theta = np.linspace(0, 2 * np.pi, 100)
    center, radius = [0.5, 0.5], 0.5
    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
    circle = mpath.Path(verts * radius + center)

    # Read in observed sea ice concentration

    path_nsidc = "/glade/campaign/cesm/development/cross-wg/diagnostic_framework/CUPiD_obs_data/ice/"

    ds_obs = xr.open_dataset(path_nsidc + "SSMI.ifrac.1981-2005monthlymean.gx1v5.nc")

    ds_pop = add_cyclic(ds_obs)

    ifrac_obs = ds_pop.monthly_ifrac.mean(dim="month")

    aice = title.find("Concentration")

    if np.size(levels) > 2:
        cmap = mpl.colormaps["ocean"]
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
        cmap="ocean",
        transform=ccrs.PlateCarree(),
    )
    if aice > 0:
        plt.contour(
            ds_pop.tlon,
            ds_pop.tlat,
            ifrac_obs,
            levels=[0.15],
            colors="magenta",
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
        cmap="ocean",
        transform=ccrs.PlateCarree(),
    )
    if aice > 0:
        plt.contour(
            ds_pop.tlon,
            ds_pop.tlat,
            ifrac_obs,
            levels=[0.15],
            colors="magenta",
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
