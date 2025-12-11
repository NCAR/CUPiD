from __future__ import annotations

import xarray as xr

dpseas = {"DJF": 90, "MAM": 92, "JJA": 92, "SON": 91}


def seasonal_climatology_weighted(dat):
    """Calculate seasonal and annual average climatologies"""

    # avoid rolling mean crashing if using dask
    # dat = dat.chunk({'time':-1})

    days_in_month = dat.time.dt.days_in_month

    num = (dat * days_in_month).rolling(time=3, center=True, min_periods=3).sum()
    den = days_in_month.rolling(time=3, center=True, min_periods=3).sum()
    dat_seas = (num / den).dropna("time", how="all")

    dat_djf = dat_seas.where(dat_seas.time.dt.month == 1, drop=True).mean("time")
    dat_mam = dat_seas.where(dat_seas.time.dt.month == 4, drop=True).mean("time")
    dat_jja = dat_seas.where(dat_seas.time.dt.month == 7, drop=True).mean("time")
    dat_son = dat_seas.where(dat_seas.time.dt.month == 10, drop=True).mean("time")

    # annual mean
    num_am = (dat * days_in_month).groupby("time.year").sum("time")
    den_am = days_in_month.groupby("time.year").sum("time")
    dat_am = (num_am / den_am).mean("year")

    dat_djf = dat_djf.rename("DJF")
    dat_mam = dat_mam.rename("MAM")
    dat_jja = dat_jja.rename("JJA")
    dat_son = dat_son.rename("SON")
    dat_am = dat_am.rename("AM")

    alldat = xr.merge([dat_djf, dat_mam, dat_jja, dat_son, dat_am])
    return alldat
