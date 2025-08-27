"""
A module for plotting utilties shared amongst the lnd/ Python
"""
from __future__ import annotations


def cut_off_antarctica(da, antarctica_border=-60):
    """
    Cut off the bottom of the map, from latitude antarctica_border south
    """
    da = da.sel(lat=slice(antarctica_border, 90))
    return da
