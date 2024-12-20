from __future__ import annotations

import xarray as xr

dpseas = {"DJF": 90, "MAM": 92, "JJA": 92, "SON": 91}


def seasonal_climatology_weighted(dat):
    """Calculate seasonal and annual average climatologies"""
    days_in_month = dat.time.dt.days_in_month
    mons = dat.time.dt.month
    wgts = mons.copy(deep=True)
    wgts = xr.where(
        (mons == 1) | (mons == 2) | (mons == 12),
        days_in_month / dpseas["DJF"],
        wgts,
    )
    wgts = xr.where(
        (mons == 3) | (mons == 4) | (mons == 5),
        days_in_month / dpseas["MAM"],
        wgts,
    )
    wgts = xr.where(
        (mons == 6) | (mons == 7) | (mons == 8),
        days_in_month / dpseas["JJA"],
        wgts,
    )
    wgts = xr.where(
        (mons == 9) | (mons == 10) | (mons == 11),
        days_in_month / dpseas["SON"],
        wgts,
    )
    datw = dat * wgts

    wgts_am = days_in_month / 365.0
    datw_am = dat * wgts_am

    ds_season = (
        datw.load()
        .rolling(min_periods=3, center=True, time=3)
        .sum()
        .dropna("time", how="all")
    )
    dat_djf = ds_season.where(ds_season.time.dt.month == 1, drop=True).mean("time")
    dat_mam = ds_season.where(ds_season.time.dt.month == 4, drop=True).mean("time")
    dat_jja = ds_season.where(ds_season.time.dt.month == 7, drop=True).mean("time")
    dat_son = ds_season.where(ds_season.time.dt.month == 10, drop=True).mean("time")
    dat_am = datw_am.groupby("time.year").sum("time")
    dat_am = dat_am.mean("year")

    dat_djf = dat_djf.rename("DJF")
    dat_mam = dat_mam.rename("MAM")
    dat_jja = dat_jja.rename("JJA")
    dat_son = dat_son.rename("SON")
    dat_am = dat_am.rename("AM")

    return xr.merge([dat_djf, dat_mam, dat_jja, dat_son, dat_am])
