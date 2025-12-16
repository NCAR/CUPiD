from __future__ import annotations

import xarray as xr
import numpy as np


def global_mean(variable):
    """
    Description: compute the global mean (weigthed) of a variable
    Argument:
       ds: variable
    Return:
       ds_ann: annual mean
    """
    weights = np.cos(np.deg2rad(variable.lat))
    variable_weighted = variable.weighted(weights)
    variable_mean = variable_weighted.mean(("lon", "lat"))
    return variable_mean


def compute_ann_mean(filepath, case, var, lat1=None, lat2=None, lon1=None, lon2=None):
    """
    Description: Compute the annual mean within a specified latitude (lat1-lat2)
    and longitude (lon1-lon2) range of the variable "var".

    Arguments:
        filepath = filepath
        case = casename
        var = variable name
        lat1 = starting latitude
        lat2 = ending latitude
        lon1 = starting longitude
        lon2 = ending longitude
    """
    filename = filepath + case + "/" + case + "." + var + ".nc"
    ds = xr.open_dataset(filename)

    # Select the subset of data within the specified latitude and longitude ranges before calculating the annual mean
    ds_subset = ds.sel(lat=slice(lat1, lat2), lon=slice(lon1, lon2))

    var_ann = ds_subset[var].groupby("time.year").mean()
    var_lat_lon_ann = lat_lon_mean(var_ann, lat1, lat2, lon1, lon2)

    return var_lat_lon_ann


def compute_var_g_ann(filepath, case, var):
    """
    Compute the weighted annual global mean of
    a given variable.
    Argument:
       case = casename
       var = variable name
    """
    filename = filepath + case + "/" + case + "." + var + ".nc"
    ds = xr.open_dataset(filename)
    return global_mean(ds[var].groupby("time.year").mean())


def lat_lon_mean(variable, lat1, lat2, lon1, lon2):
    """
    Description: Compute the mean (weighted by cosine of latitude) of a variable
    within a specified latitude (lat1-lat2) and longitude (lon1-lon2) range.

    Arguments:
        variable: xarray DataArray representing the variable to be averaged.
        lat1: Starting latitude for the range.
        lat2: Ending latitude for the range.
        lon1: Starting longitude for the range.
        lon2: Ending longitude for the range.

    Return:
        variable_mean: The mean value of the variable within the specified lat/lon range.
    """
    # Select the subset of data within the specified latitude and longitude ranges
    variable_subset = variable.sel(lat=slice(lat1, lat2), lon=slice(lon1, lon2))

    # Compute weights as the cosine of the latitude, adjusted for the selected range
    weights = np.cos(np.deg2rad(variable_subset.lat))

    # Apply weighted mean over the subset
    variable_weighted = variable_subset.weighted(weights)
    variable_mean = variable_weighted.mean(("lon", "lat"))

    return variable_mean


def lat_lon_mean_norm(variable, lat1, lat2, lon1, lon2):
    # TODO: This could be combined with lat_lon_mean by adding a normalize_weights argument
    """
    Description: Compute the mean (weighted by cosine of latitude) of a variable
    within a specified latitude (lat1-lat2) and longitude (lon1-lon2) range.

    Arguments:
        variable: xarray DataArray representing the variable to be averaged.
        lat1: Starting latitude for the range.
        lat2: Ending latitude for the range.
        lon1: Starting longitude for the range.
        lon2: Ending longitude for the range.

    Return:
        variable_mean: The mean value of the variable within the specified lat/lon range.
    """
    # Select the data subset within the specified latitude and longitude ranges
    variable_subset = variable.sel(lat=slice(lat1, lat2), lon=slice(lon1, lon2))

    # Compute weights as the cosine of the latitude, adjusted for the selected range
    # Ensure weights are normalized (sum to 1) over the selected latitude range for accurate weighting
    latitudes = variable_subset.lat
    weights = np.cos(np.deg2rad(latitudes))
    weights /= weights.sum(dim="lat")

    # Apply weighted mean over the subset
    variable_weighted = variable_subset.weighted(weights)
    variable_mean = variable_weighted.mean(("lon", "lat"))

    return variable_mean


def compute_var_zonal_ann(filepath, case, var):
    """
    Description: compute the annual global mean (weighted) of
    a variable var
    Argument:
       case = casename
       var = variable name
    """
    filename = filepath + case + "/" + case + "." + var + ".nc"
    ds = xr.open_dataset(filename)
    ds.mean(["lon"])
    var_zonal_ann = ds[var].groupby("time.year").mean().mean(["lon"])
    return var_zonal_ann
