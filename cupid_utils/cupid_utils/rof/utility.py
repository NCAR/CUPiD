from __future__ import annotations

import numpy as np
import pandas as pd
import yaml
from pyogrio import read_dataframe


# in case toml module may not be available
try:
    import tomli

    def load_toml(toml_file) -> dict:
        """Load TOML data from file"""
        with open(toml_file, "rb") as f:
            return tomli.load(f)

except ImportError:
    pass  # or anything to log


def load_yaml(yaml_file) -> dict:
    """Load yaml data from file"""
    with open(yaml_file) as ymlfile:
        return yaml.load(ymlfile, Loader=yaml.FullLoader)


class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


def read_shps(shp_list, usecols, **kwargs):
    """Faster load shapefiles with selected attributes in dataframe"""
    gdf_frame = []
    for shp in shp_list:
        gdf_frame.append(read_dataframe(shp, columns=usecols))
        print("Finished reading %s" % shp.strip("\n"))
    return pd.concat(gdf_frame)


def get_index_array(a_array, b_array):
    """
    Get index array where each index points to locataion in a_array. The order of index array corresponds to b_array

      e.g.,
      a_array = [2, 4, 1, 8, 3, 10, 5, 9, 7, 6]
      b_array = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
      result  = [2, 0, 4, 1, 6, 9, 8, 3, 7, 5]

    https://stackoverflow.com/questions/8251541/numpy-for-every-element-in-one-array-find-the-index-in-another-array
    """
    index = np.argsort(a_array)
    sorted_a_array = a_array[index]
    sorted_index = np.searchsorted(sorted_a_array, b_array)

    yindex = np.take(index, sorted_index, mode="clip")
    mask = a_array[yindex] != b_array

    result = np.ma.array(yindex, mask=mask)

    return result


def reorder_index(ID_array_orig, ID_array_target):
    x = ID_array_orig
    # Find the indices of the reordered array. See link for more details:
    # https://stackoverflow.com/questions/8251541/numpy-for-every-element-in-one-array-find-the-index-in-another-array
    index = np.argsort(x)
    sorted_x = x[index]
    sorted_index = np.searchsorted(sorted_x, ID_array_target)

    return np.take(index, sorted_index, mode="clip")


def no_time_variable(ds):
    vars_without_time = []
    for var in ds.variables:
        if "time" not in ds[var].dims:
            if var not in list(ds.coords):
                vars_without_time.append(var)
    return vars_without_time
