from __future__ import annotations

import numpy as np
import xarray as xr
from itertools import groupby

# time series error 
# flow metrics

def remove_nan(qsim, qobs):
    sim_obs = np.stack((qsim, qobs), axis=1)
    sim_obs = sim_obs[~np.isnan(sim_obs).any(axis=1), :]
    return sim_obs[:, 0], sim_obs[:, 1]


def nse(qsim, qobs):
    """
    Calculates The Nash–Sutcliffe efficiency (NSE) between two time series arrays.

    Arguments
    ---------
    sim: array-like
        Simulated time series array.
    obs: array-like
        Observed time series array.

    Returns
    -------
    nse: float
        nse calculated between the two arrays.
    """
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return 1 - np.sum((qsim1 - qobs1) ** 2) / np.sum((qobs1 - np.mean(qobs1)) ** 2)


def corr(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.corrcoef(qsim1, qobs1)[0, 1]


def alpha(qsim, qobs):
    """
    Calculates ratio of variabilities of two time series arrays.

    Arguments
    ---------
    sim: array-like
        Simulated time series array.
    obs: array-like
        Observed time series array.

    Returns
    -------
    alpha: float
        variability ratio calculated between the two arrays.
    """
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.sqrt(np.sum((qsim1 - np.mean(qsim1)) ** 2) / len(qsim1)) / np.sqrt(
        np.sum((qobs1 - np.mean(qobs1)) ** 2) / len(qobs1),
    )


def beta(qsim, qobs):
    """
    Calculates ratio of means of two time series arrays.

    Arguments
    ---------
    sim: array-like
        Simulated time series array.
    obs: array-like
        Observed time series array.

    Returns
    -------
    beta: float
        mean ratio calculated between the two arrays.
    """
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.mean(qsim1) / np.mean(qobs1)


def kge(qsim, qobs):
    """
    Calculates the Kling-Gupta Efficiency (KGE) between two time series arrays.
    Arguments
    ---------
    sim: array-like
        Simulated time series array.
    obs: array-like
        Observed time series array.

    Returns
    -------
    kge: float
        Kling-Gupta Efficiency calculated between the two arrays.
    """
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return 1 - np.sqrt(
        (1 - corr(qsim1, qobs1)) ** 2
        + (alpha(qsim1, qobs1) - 1) ** 2
        + (beta(qsim1, qobs1) - 1) ** 2,
    )


def pbias(qsim, qobs):
    """
    Calculates percentage bias between two flow arrays.
    Arguments
    ---------
    sim: array-like
        Simulated time series array.
    obs: array-like
        Observed time series array.

    Returns
    -------
    pbial: float
        percentage bias calculated between the two arrays.
    """
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.sum(qsim1 - qobs1) / np.sum(qobs1)


def mae(qsim, qobs):
    """
    Calculates mean absolute error (mae) two flow arrays.
    Arguments
    ---------
    sim: array-like
        Simulated time series array.
    obs: array-like
        Observed time series array.

    Returns
    -------
    mae: float
        mean absolute error calculated between the two arrays.
    """
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.sum(abs(qsim1 - qobs1)) / np.sum(qobs1)


def rmse(qsim, qobs):
    """
    Calculates root mean squared of error (rmse) between two time series arrays.
    Arguments
    ---------
    sim: array-like
        Simulated time series array.
    obs: array-like
        Observed time series array.

    Returns
    -------
    rmse: float
        rmse calculated between the two arrays.
    """
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.sqrt(np.mean((qsim1 - qobs1) ** 2))

# flow metrics

def FHV(dr: xr.DataArray, percent=0.9):
    """
    Calculates Flow duration curve high segment volume.
    Arguments
    ---------
    dr: xr.DataArray
        2D DataArray containing daily time series with coordinates of 'site', and 'time'
    Returns
    -------
    ds_FLV: xr.Dataset
        Dataset containing two 2D DataArrays 'ann_max_flow' and 'ann_max_day' with coordinate of 'year', and 'site'
    Notes
    -------
    None
    """
    prob=np.arange(1,float(len(dr['time']+1)))/(1+len(dr['time'])) #probability
    for d in range(len(prob)):
        idx=d
        if prob[d] > percent: break

    t_axis = dr.dims.index('time')
    flow_array_sort = np.sort(dr.values, axis=t_axis)
    if t_axis==0:
        FHV = np.mean(flow_array_sort[idx:,:], axis=t_axis)
    elif t_axis==1:
        FHV = np.mean(flow_array_sort[:,idx:], axis=t_axis)

    ds_FHV = xr.Dataset(data_vars=dict(FHV=(["site"], FHV)), coords=dict(site=dr['site']))

    return ds_FHV


def FLV(dr: xr.DataArray, percent=0.1):

    #Calculates Flow duration curve low segment volume. default is < 0.1
    # Yilmaz, K. K., et al. (2008), A process-based diagnostic approach to model evaluation: Applicationto the NWS distributed hydrologic model, Water Resour. Res., 44, W09417, doi:10.1029/2007WR006716

    prob=np.arange(1,float(len(dr['time']+1)))/(1+len(dr['time'])) #probability
    for d in range(len(prob)):
        idx=d
        if prob[d] > percent: break

    t_axis = dr.dims.index('time')
    flow_array_sort = np.sort(dr.values, axis=t_axis)
    if t_axis==0:
        FLV = np.sum(flow_array_sort[:idx,:], axis=t_axis)
    elif t_axis==1:
        FLV = np.sum(flow_array_sort[:,:idx], axis=t_axis)

    ds_FLV = xr.Dataset(data_vars=dict(FLV=(["site"], FLV)), coords=dict(site=dr['site']))

    return ds_FLV


def FMS(dr: xr.DataArray, percent_low=0.3, percent_high=0.7):

    #Calculate Flow duration curve midsegment slope (default between 30 and 70 percentile)

    prob=np.arange(1,float(len(dr['time']+1)))/(1+len(dr['time'])) #probability
    for d in range(len(prob)):
        idx_l=d
        if prob[d] > percent_low: break
    for d in range(len(prob)):
        idx_h=d
        if prob[d] > percent_high: break

    t_axis = dr.dims.index('time')
    flow_array_sort = np.sort(dr.values, axis=t_axis)
    
    if t_axis==0:
        high = flow_array_sort[idx_h,:]
        low  = flow_array_sort[idx_l,:]
    elif t_axis==1:
        high = flow_array_sort[:,idx_h]
        low  = flow_array_sort[:,idx_l]

    high_log = np.log10(high, where=0<high, out=np.nan*high)
    low_log  = np.log10(low,  where=0<low,  out=np.nan*low)

    FMS = (high_log-low_log)/(percent_high-percent_low)

    ds_FMS = xr.Dataset(data_vars=dict(FMS=(["site"], FMS)), coords=dict(site=dr['site']))

    return ds_FMS


def BFI(dr: xr.DataArray, alpha=0.925, npass=3, skip_time=30):

    #Calculate digital filter based Baseflow Index
    # Ladson, A. R., et al. (2013). A Standard Approach to Baseflow Separation Using The Lyne and Hollick Filter. Australasian Journal of Water Resources, 17(1), 25–34.
    # https://doi.org/10.7158/13241583.2013.11465417

    t_axis = dr.dims.index('time')
    tlen = len(dr['time'])

    q_total = dr.values
    if t_axis==1:
        q_total = q_total.T

    q_total_diff = q_total - np.roll(q_total, 1, axis=t_axis) # q(i)-q(i-1)
    q_fast = np.tile(q_total[skip_time+1,:], (tlen,1))

    count=1
    while count <= npass:
        for tix in np.arange(1, tlen):
            q_fast[tix,:] = alpha*q_fast[tix-1,:]+(1.0+alpha)/2.0*q_total_diff[tix,:]
            q_fast[tix,:] = np.where(q_fast[tix,:]>=0, q_fast[tix,:], 0)
        count+=1

    q_base = q_total-q_fast

    q_total_sum = np.nansum(q_total[skip_time:,:], axis=t_axis)
    BFI = np.nansum(q_base[skip_time:,:], axis=t_axis)/np.where(q_total_sum>0, q_total_sum, np.nan)

    ds_BFI = xr.Dataset(data_vars=dict(BFI=(["site"], BFI)), coords=dict(site=dr['site']))

    return BFI


def high_q_freq_dur(dr: xr.DataArray, percent=0.7, dayofyear='wateryear'):
    
    # freq_high_q: frequency of high-flow days (> 9 times the median daily flow) day/yr
    # mean_high_q_dur: average duration of high-flow events over yr (number of consecutive days > 9 times the median daily flow) day
    
    dayofyear='wateryear'
    if dayofyear=='wateryear':
        smon=10; sday=1; emon=9; eday=30; yr_adj=1
    elif dayofyear=='calendar':
        smon=1; sday=1; emon=12; eday=31; yr_adj=0
    else:
        raise ValueError('Invalid argument for "dayofyear"')

    years = np.unique(dr.time.dt.year.values)[:-1]

    ds_high_q = xr.Dataset(data_vars=dict(
                    mean_high_q_dur =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    freq_high_q     =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    ),
                    coords=dict(year=years,
                                site=dr['site'],),
                    )

    t_axis = dr.dims.index('time')
    q_thresh=np.median(dr.values, axis=t_axis)*5

    for yr in years:
        time_slice=slice(f'{yr}-{smon}-{sday}',f'{yr+yr_adj}-{emon}-{eday}')

        q_array = dr.sel(time=time_slice).values # find annual max flow
        for sidx, site in enumerate(dr['site'].values):
            binary_array = np.where(q_array[:,sidx]>q_thresh[sidx], 1, 0)
            count_dups = myCount(binary_array)
            if not count_dups:
                ds_high_q['mean_high_q_dur'].loc[yr, site] = 0
                ds_high_q['freq_high_q'].loc[yr, site]     = 0
            else:
                ds_high_q['mean_high_q_dur'].loc[yr, site] = np.mean(count_dups)
                ds_high_q['freq_high_q'].loc[yr, site]     = len(count_dups) # used to np.sum
   
    return ds_high_q


def low_q_freq_dur(dr: xr.DataArray, percent=0.7, dayofyear='wateryear'):
    # : frequency of low-flow days (< 0.2 times the mean daily flow) day/yr
    # : average duration of low-flow events (number of consecutive days < 0.2 times the mean daily flow) day
    
    dayofyear='wateryear'
    if dayofyear=='wateryear':
        smon=10; sday=1; emon=9; eday=30; yr_adj=1
    elif dayofyear=='calendar':
        smon=1; sday=1; emon=12; eday=31; yr_adj=0
    else:
        raise ValueError('Invalid argument for "dayofyear"')

    years = np.unique(dr.time.dt.year.values)[:-1]

    ds_low_q = xr.Dataset(data_vars=dict(
                    mean_low_q_dur =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    freq_low_q     =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    ),
                    coords=dict(year=years,
                                site=dr['site'],),
                    )

    t_axis = dr.dims.index('time')
    q_thresh=np.median(dr.values, axis=t_axis)*0.2

    for yr in years:
        time_slice=slice(f'{yr}-{smon}-{sday}',f'{yr+yr_adj}-{emon}-{eday}')

        q_array = dr.sel(time=time_slice).values # find annual max flow
        for sidx, site in enumerate(dr['site'].values):
            binary_array = np.where(q_array[:,sidx]<q_thresh[sidx], 1, 0)
            count_dups = myCount(binary_array)
            if not count_dups:
                ds_low_q['mean_low_q_dur'].loc[yr, site] = 0
                ds_low_q['freq_low_q'].loc[yr, site]     = 0
            else:
                ds_low_q['mean_low_q_dur'].loc[yr, site] = np.mean(count_dups)
                ds_low_q['freq_low_q'].loc[yr, site]     = len(count_dups) # used to np.sum
   
    return ds_low_q


def annual_max(dr: xr.DataArray, dayofyear='wateryear'):
    """
    Calculates annual maximum value and dayofyear.
    Arguments
    ---------
    dr: xr.DataArray
        2D DataArray containing daily time series with coordinates of 'site', and 'time'
    Returns
    -------
    ds_ann_max: xr.Dataset
        Dataset containing two 2D DataArrays 'ann_max_flow' and 'ann_max_day' with coordinate of 'year', and 'site'
    Notes
    -------
    dayofyear start with October 1st with dayofyear="wateryear" or January 1st with dayofyear="calendar".
    """
    if dayofyear=='wateryear':
        smon=10; sday=1; emon=9; eday=30; yr_adj=1
    elif dayofyear=='calendar':
        smon=1; sday=1; emon=12; eday=31; yr_adj=0
    else:
        raise ValueError('Invalid argument for "dayofyear"')

    years = np.unique(dr.time.dt.year.values)[:-1]

    ds_ann_max = xr.Dataset(data_vars=dict(
                    ann_max_flow =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    ann_max_day  =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    ),
                    coords=dict(year=years,
                                site=dr['site'],),
                    )

    for yr in years:
        time_slice=slice(f'{yr}-{smon}-{sday}',f'{yr+yr_adj}-{emon}-{eday}')

        max_flow_array = dr.sel(time=time_slice).max(dim='time').values # find annual max flow
        ix = np.argwhere(np.isnan(max_flow_array)) # if whole year data is missing, it is nan, so find that site
        max_day_array = dr.sel(time=time_slice).argmax(dim='time', skipna=False).values.astype('float') # find annual max flow day
        max_day_array[ix]=np.nan

        ds_ann_max['ann_max_flow'].loc[dict(year=yr)] = max_flow_array
        ds_ann_max['ann_max_day'].loc[dict(year=yr)]  = max_day_array

    return ds_ann_max


def annual_min(dr: xr.DataArray, dayofyear='wateryear'):
    """
    Calculates annual minimum value and dayofyear.
    Arguments
    ---------
    dr: xr.DataArray
        2D DataArray containing daily time series with coordinates of 'site', and 'time'
    Returns
    -------
    ds_ann_max: xr.Dataset
        Dataset containing two 2D DataArrays 'ann_min_flow' and 'ann_min_day' with coordinate of 'year', and 'site'
    """
    if dayofyear=='wateryear':
        smon=10; sday=1; emon=9; eday=30; yr_adj=1
    elif dayofyear=='calendar':
        smon=1; sday=1; emon=12; eday=31; yr_adj=0
    else:
        raise ValueError('Invalid argument for "dayofyear"')

    years = np.unique(dr.time.dt.year.values)[:-1]

    ds_ann_min = xr.Dataset(data_vars=dict(
                    ann_min_flow =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    ann_min_day  =(["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                    ),
                    coords=dict(year=years,
                                site=dr['site'],)
                    )

    for yr in years:
        time_slice=slice(f'{yr}-{smon}-{sday}',f'{yr+yr_adj}-{emon}-{eday}')
        min_flow_array = dr.sel(time=time_slice).min(dim='time').values
        ix = np.argwhere(np.isnan(min_flow_array)) # if whole year data is missing, it is nan, so find that site
        min_day_array = dr.sel(time=time_slice).argmin(dim='time', skipna=False).values.astype('float') # find annual max flow day
        min_day_array[ix]=np.nan
        ds_ann_min['ann_min_flow'].loc[dict(year=yr)] = min_flow_array
        ds_ann_min['ann_min_day'].loc[dict(year=yr)] = min_day_array

    return ds_ann_min


def annual_centroid(dr: xr.DataArray, dayofyear='wateryear'):
    """
    Calculates annual time series centroid (in dayofyear).
    Arguments
    ---------
    dr: xr.DataArray
        2D DataArray containing daily time series with coordinates of 'site', and 'time'
    Returns
    -------
    ds_ann_max: xr.Dataset
        Dataset containing one 2D DataArrays 'ann_centroid_day' with coordinate of 'year', and 'site'
    """
    if dayofyear=='wateryear':
        smon=10; sday=1; emon=9; eday=30; yr_adj=1
    elif dayofyear=='calendar':
        smon=1; sday=1; emon=12; eday=31; yr_adj=0
    else:
        raise ValueError('Invalid argument for "dayofyear"')

    years = np.unique(dr.time.dt.year.values)[:-1]

    ds_ann_centroid = xr.Dataset(data_vars=dict(
                                ann_centroid_day = (["year", "site"], np.full((len(years),len(dr['site'])), np.nan, dtype='float32')),
                                ),
                                coords=dict(year=years, site=dr['site'],)
                                )

    for ix, yr in enumerate(years):
        time_slice=slice(f'{yr}-{smon}-{sday}',f'{yr+yr_adj}-{emon}-{eday}')
        for site in dr['site'].values:
            q_array = dr.sel(time=time_slice, site=site).values
            centroid_day = (q_array*np.arange(len(q_array))).sum()/q_array.sum()
            ds_ann_centroid['ann_centroid_day'].loc[dict(year=yr, site=site)] = centroid_day

    return ds_ann_centroid


def season_mean(ds: xr.Dataset, calendar="standard"):
    # Make a DataArray with the number of days in each month, size = len(time)
    month_length = ds.time.dt.days_in_month

    # Calculate the weights by grouping by 'time.season'
    weights = (month_length.groupby("time.season") / month_length.groupby("time.season").sum())

    # Test that the sum of the weights for each season is 1.0
    np.testing.assert_allclose(weights.groupby("time.season").sum().values, np.ones(4))

    # Calculate the weighted average
    return (ds * weights).groupby("time.season").sum(dim="time")