"""
This module provides functions for reading YAML files and working with intake catalogs.

Functions:
    - read_yaml(path_to_yaml): Read a YAML file and return its content as a dictionary.
    - get_collection(path_to_catalog, **kwargs): Get a collection of datasets from an
                     intake catalog based on specified criteria.
"""

import intake
import yaml


def read_yaml(path_to_yaml):
    """Read yaml file and return data from loaded yaml file"""
    with open(path_to_yaml) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    return data


def get_collection(path_to_catalog, **kwargs):
    """Get collection of datasets from intake catalog"""
    cat = intake.open_esm_datastore(path_to_catalog)
    # note that the json file points to the csv, so the path that the
    # yaml file contains does not actually get used. this can cause issues

    cat_subset = cat.search(**kwargs)

    if "variable" in kwargs.keys():
        # pylint: disable=invalid-name
        def preprocess(ds):
            # the double brackets return a Dataset rather than a DataArray
            # this is fragile and could cause issues, not sure what subsetting on time_bound does
            return ds[[kwargs["variable"], "time_bound"]]

        # not sure what the chunking kwarg is doing here either
        dsets = cat_subset.to_dataset_dict(
            xarray_open_kwargs={"chunks": {"time": -1}},
            preprocess=preprocess,
        )

    else:
        dsets = cat_subset.to_dataset_dict()

    return dsets
