# From https://github.com/NCAR/ctsm_python_gallery/blob/02ae0f079bb53b8619408f32b1fb9248ed0a260c/notebooks/sparse-PFT-gridding.ipynb  # noqa:  disable=E501
from __future__ import annotations

import itertools

import numpy as np
import sparse
import xarray as xr


def to_sparse(data, vegtype, jxy, ixy, shape):
    """Takes an input numpy array and converts it to a sparse array."""

    codes = zip(vegtype, jxy - 1, ixy - 1)

    # some magic from https://github.com/pydata/xarray/pull/5577
    # This constructs a list of coordinate locations at which data exists
    # it works for arbitrary number of dimensions but assumes that the last
    # dimension is the "stacked" dimension i.e. "pft"
    if data.ndim == 1:
        indexes = codes
    else:
        sizes = list(itertools.product(*[range(s) for s in data.shape[:-1]]))
        tuple_indexes = itertools.product(sizes, codes)
        indexes = map(lambda x: list(itertools.chain(*x)), tuple_indexes)

    return sparse.COO(
        coords=np.array(list(indexes)).T,
        data=data.ravel(),
        shape=data.shape[:-1] + shape,
    )


def convert_pft1d_to_sparse(dataset):

    # extract PFT variables
    pfts = xr.Dataset({k: v for k, v in dataset.items() if "pft" in v.dims})

    ixy = dataset.pfts1d_ixy.astype(int)
    jxy = dataset.pfts1d_jxy.astype(int)
    vegtype = dataset.pfts1d_itype_veg.astype(int)
    npft = vegtype.max().load().item()
    # expected shape of sparse arrays (excludes time)
    output_sizes = {
        "pft": npft + 1,
        "lat": dataset.sizes["lat"],
        "lon": dataset.sizes["lon"],
    }

    result = xr.Dataset()
    for var in pfts:
        result[var] = xr.apply_ufunc(
            to_sparse,
            pfts[var],
            vegtype,
            jxy,
            ixy,
            input_core_dims=[["pft"]] * 4,
            output_core_dims=[["pft", "lat", "lon"]],
            exclude_dims={"pft"},  # changes size
            dask="parallelized",
            kwargs=dict(shape=tuple(output_sizes.values())),
            dask_gufunc_kwargs=dict(
                meta=sparse.COO([]),
                output_sizes=output_sizes,
            ),  # lets dask know that we are changing from numpy to sparse
            output_dtypes=[pfts[var].dtype],
        )

    # copy over coordinate variables lat, lon
    result = result.update(dataset[["lat", "lon"]])
    result["pft"] = np.arange(result.sizes["pft"])
    return result
