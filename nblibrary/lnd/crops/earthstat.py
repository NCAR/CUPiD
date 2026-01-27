"""
Classes to handle importing and working with EarthStat data
"""

from __future__ import annotations

import os
import warnings

import numpy as np
import xarray as xr

from .earthstat_regrid import regrid_to_clm

# The resolution which will be used as the basis for regridding, if available
REFERENCE_EARTHSTAT_RES = "f09"

# The variables we actually use anywhere
NEEDED_VARS = ["HarvestArea", "Production", "Yield", "LandMask"]


def align_time(da_to_align: xr.DataArray, target_time: xr.DataArray) -> xr.DataArray:
    """
    Align EarthStat time axis with CLM time axis.

    EarthStat and CLM time axes don't match. This function gives the EarthStat data the time axis
    of the CLM outputs. If you don't do this, you will get all NaNs when you try to assign
    something from EarthStat to the CLM Dataset.

    Parameters
    ----------
    da_to_align : xarray.DataArray
        EarthStat DataArray to align.
    target_time : xarray.DataArray
        CLM time coordinate DataArray to align to.

    Returns
    -------
    xarray.DataArray
        DataArray with time axis aligned to target_time.
    """

    # We may want to use this with target_time DataArrays that are a DateTime type. Otherwise we'll
    # assume that the values are just numeric years.
    target_time_is_dt_type = hasattr(target_time.values[0], "year")

    # Align EarthStat with CLM axis
    orig_time = da_to_align["time"]
    first_year = min(orig_time.values).year
    last_year = max(orig_time.values).year
    if target_time_is_dt_type:
        this_slice = slice(f"{first_year}-01-01", f"{last_year}-12-31")
    else:
        this_slice = slice(first_year, last_year)
    new_time_coord = target_time.sel(time=this_slice)

    # Slice EarthStat to match CLM time span
    first_year_target = min(target_time.values)
    last_year_target = max(target_time.values)
    if target_time_is_dt_type:
        first_year_target = first_year_target.year
        last_year_target = last_year_target.year
    this_slice = slice(f"{first_year_target}-01-01", f"{last_year_target}-12-31")
    da_to_align = da_to_align.sel(time=this_slice)

    return da_to_align.assign_coords({"time": new_time_coord})


def check_dim_alignment(earthstat_ds: xr.Dataset, clm_ds: xr.Dataset) -> xr.Dataset:
    """
    Ensure that EarthStat and CLM datasets are aligned on all dimensions.

    Parameters
    ----------
    earthstat_ds : xarray.Dataset
        EarthStat dataset to align.
    clm_ds : xarray.Dataset
        CLM dataset to align to.

    Returns
    -------
    xarray.Dataset
        EarthStat dataset with dimensions aligned to CLM dataset.

    Raises
    ------
    RuntimeError
        If dimensions cannot be aligned (except for time, where CLM can have more timesteps).
    """
    # Align crop coordinates
    if "crop" not in earthstat_ds.coords:
        earthstat_ds = earthstat_ds.assign_coords({"crop": clm_ds["crop"]})

    # Align time coordinates
    earthstat_ds = align_time(earthstat_ds, clm_ds["time"])

    for dim in earthstat_ds.dims:
        if not earthstat_ds[dim].equals(clm_ds[dim]):
            # Special handling for time: It's okay for CLM to have more timesteps than EarthStat,
            # but every timestep in EarthStat needs to be in CLM.
            if dim == "time":
                if all(x in clm_ds[dim].values for x in earthstat_ds[dim].values):
                    continue

            raise RuntimeError(f"Misalignment in {dim}")

    return earthstat_ds


def get_clm_landarea(ds: xr.Dataset) -> xr.DataArray:
    """
    Calculate CLM land area from gridcell area and land fraction.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing 'area' and 'landfrac' variables.

    Returns
    -------
    xarray.DataArray
        Land area calculated as gridcell area * landfrac.
    """
    return ds["area"] * ds["landfrac"]


class EarthStat:
    """
    A class to handle importing EarthStat data.

    Attributes
    ----------
    crops : list[str]
        List of crop names available in EarthStat.
    _data : dict[str, xarray.Dataset]
        Dictionary mapping resolution names to EarthStat datasets.
    """

    def __init__(
        self,
        earthstat_dir: str,
        sim_resolutions: dict[str, xr.Dataset],
        opts: dict,
    ) -> None:
        """
        Initialize EarthStat instance.

        Parameters
        ----------
        earthstat_dir : str
            Directory containing EarthStat data files.
        sim_resolutions : dict[str, xarray.Dataset]
            Dictionary mapping resolution names to CLM datasets for regridding.
        opts : dict
            Options dictionary containing 'crops_to_plot', 'start_year', and 'end_year'.
        """
        # Define variables
        self.crops: list[str] = []
        self._data: dict[str, xr.Dataset] = {}

        # Import EarthStat crop list
        self._get_crop_list(earthstat_dir, opts["crops_to_plot"])

        # Import EarthStat maps
        self._import_all_resolutions(earthstat_dir, sim_resolutions, opts)

    def __getitem__(self, key: str) -> xr.Dataset:
        """
        Get dataset for a resolution using instance[key] syntax.

        Parameters
        ----------
        key : str
            Resolution name.

        Returns
        -------
        xarray.Dataset
            Dataset for the specified resolution.
        """
        return self._data[key]

    def __setitem__(self, key: str, value: xr.Dataset) -> None:
        """
        Set dataset for a resolution using instance[key]=value syntax.

        Parameters
        ----------
        key : str
            Resolution name.
        value : xarray.Dataset
            Dataset to store for this resolution.
        """
        self._data[key] = value

    def __print__(self) -> None:
        """
        Print information about available resolutions.
        """
        print(
            f"Dict with Datasets for the following resolutions: {','.join(self._data.keys())}",
        )

    def keys(self):
        """
        Return keys of the _data dict.

        Returns
        -------
        dict_keys
            Keys (resolution names) of the internal data dictionary.
        """
        return self._data.keys()

    def items(self):
        """
        Return items (key-value pairs) of the _data dict.

        Returns
        -------
        dict_items
            Items (resolution name, dataset pairs) of the internal data dictionary.
        """
        return self._data.items()

    def _get_crop_list(self, earthstat_dir: str, clm_crops_to_plot: list[str]) -> None:
        """
        Get the list of crops in EarthStat.

        Reads the crop list from EARTHSTATMIRCAUNFAO_croplist.txt and renames some crops to
        match CLM conventions.

        Parameters
        ----------
        earthstat_dir : str
            Directory containing EarthStat data files.
        clm_crops_to_plot : list[str]
            List of CLM crop names to check against EarthStat crops.
        """
        earthstat_crop_list_file = os.path.join(
            earthstat_dir,
            "EARTHSTATMIRCAUNFAO_croplist.txt",
        )
        with open(earthstat_crop_list_file, encoding="utf-8") as f:
            for line in f:
                # Strip leading/trailing whitespace
                line = line.strip()
                if not line:
                    continue  # skip blank lines
                # Split into number and name(s)
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    raise RuntimeError(
                        "Failed to parse this line in earthstat_crop_list_file: "
                        + line,
                    )
                self.crops.append(parts[1].lower())
        # Replace some names to match those in CLM
        for i, crop in enumerate(self.crops):
            if crop == "maize":
                self.crops[i] = "corn"
            elif crop == "soybeans":
                self.crops[i] = "soybean"
            elif crop == "sugar cane":
                self.crops[i] = "sugarcane"
        # Check that all CLM crops are in self.crops
        for crop in clm_crops_to_plot:
            if crop not in self.crops:
                print(f"WARNING: {crop} not found in self.crops")

    def _import_all_resolutions(
        self,
        earthstat_dir: str,
        sim_resolutions: dict[str, xr.Dataset],
        opts: dict,
    ) -> None:
        """
        Import EarthStat maps corresponding to simulated CLM resolutions.

        Parameters
        ----------
        earthstat_dir : str
            Directory containing EarthStat data files.
        sim_resolutions : dict[str, xarray.Dataset]
            Dictionary mapping resolution names to CLM datasets.
        opts : dict
            Options dictionary containing configuration settings.
        """
        for res in sim_resolutions.keys():
            self._import_one_resolution(earthstat_dir, opts, res)

        # If any resolutions weren't read, we'll need to interpolate to get them
        missing_res = [k for k in sim_resolutions.keys() if k not in self.keys()]
        if missing_res:
            self._get_all_missing(earthstat_dir, sim_resolutions, opts, missing_res)

        print("Done.")

    def _get_all_missing(
        self,
        earthstat_dir: str,
        sim_resolutions: dict[str, xr.Dataset],
        opts: dict,
        missing_res: list[str],
    ) -> None:
        """
        Interpolate EarthStat data to all missing resolutions.

        Parameters
        ----------
        earthstat_dir : str
            Directory containing EarthStat data files.
        sim_resolutions : dict[str, xarray.Dataset]
            Dictionary mapping resolution names to CLM datasets.
        opts : dict
            Options dictionary containing configuration settings.
        missing_res : list[str]
            List of resolution names that need to be interpolated.

        Raises
        ------
        FileNotFoundError
            If no EarthStat files were successfully read.
        """
        # Get base resolution to do regridding from
        if REFERENCE_EARTHSTAT_RES not in self.keys():
            self._import_one_resolution(
                earthstat_dir,
                opts,
                REFERENCE_EARTHSTAT_RES,
            )
        # If no resolutions were read, we have a problem
        if not self.keys():
            raise FileNotFoundError("No EarthStat files read")
        # If REFERENCE_EARTHSTAT_RES not available, fall back to the finest resolution we have.
        if REFERENCE_EARTHSTAT_RES in self.keys():
            earthstat_in_ds = self[REFERENCE_EARTHSTAT_RES]
            earthstat_in_res = REFERENCE_EARTHSTAT_RES
        else:
            n_finest = -np.inf
            for res, ds in self.items():
                n = ds["lat"].size
                if n > n_finest:
                    earthstat_in_ds = ds
                    earthstat_in_res = res
                    n_finest = n

        if earthstat_in_res in sim_resolutions:
            clm_in_ds = sim_resolutions[earthstat_in_res]
        else:
            clm_in_file = os.path.join(
                earthstat_dir,
                f"{earthstat_in_res}_clm_regrid_ds.nc",
            )
            clm_in_ds = xr.open_dataset(clm_in_file, decode_timedelta=False)
        clm_in_landarea = get_clm_landarea(clm_in_ds)

        for res in missing_res:
            self._get_one_missing(
                sim_resolutions=sim_resolutions,
                earthstat_in_ds=earthstat_in_ds,
                earthstat_in_res=earthstat_in_res,
                res=res,
                clm_in_landarea=clm_in_landarea,
            )

    def _get_one_missing(
        self,
        *,
        sim_resolutions: dict[str, xr.Dataset],
        earthstat_in_ds: xr.Dataset,
        earthstat_in_res: str,
        res: str,
        clm_in_landarea: xr.DataArray,
    ) -> None:
        """
        Interpolate EarthStat data to one missing resolution.

        Parameters
        ----------
        sim_resolutions : dict[str, xarray.Dataset]
            Dictionary mapping resolution names to CLM datasets.
        earthstat_in_ds : xarray.Dataset
            Source EarthStat dataset to interpolate from.
        earthstat_in_res : str
            Source resolution name.
        res : str
            Target resolution name.
        clm_in_landarea : xarray.DataArray
            CLM land area at source resolution.

        Raises
        ------
        ValueError
            If interpolation method is not defined for a variable.
        """
        print(f"Interpolating EarthStat data from {earthstat_in_res} to {res}")
        clm_out_ds = sim_resolutions[res]
        clm_out_landarea = get_clm_landarea(clm_out_ds)

        # Interpolate
        for i, var in enumerate(NEEDED_VARS):
            match var:
                case "HarvestArea" | "Production":
                    method = "conservative"
                case "Yield" | "LandMask":
                    # Yield: Calculated later, as Production/HarvestArea.
                    # LandMask: Used only as a source for interpolation.
                    continue
                case _:
                    raise ValueError(f"Undefined interp method for var {var}")
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*large graph.*")
                earthstat_out_da = regrid_to_clm(
                    ds_in=earthstat_in_ds,
                    var=var,
                    ds_target=clm_out_ds,
                    method=method,
                    area_in=clm_in_landarea,
                    area_out=clm_out_landarea,
                    mask_var="LandMask",
                )
            if i == 0:
                self[res] = xr.Dataset(data_vars={var: earthstat_out_da})
            else:
                self[res][var] = earthstat_out_da

            # Clean up the output DataArray reference
            del earthstat_out_da

        # Calculate yield
        assert (
            np.nanmax(
                self[res]["Production"].where(self[res]["HarvestArea"] == 0).values,
            )
            == 0
        )
        self[res]["Yield"] = (
            self[res]["Production"] / self[res]["HarvestArea"]
        ).fillna(0)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*large graph.*")
            self[res]["Yield"].load()
        self[res]["Yield"].attrs["long_name"] = "crop yield"
        prod_units = self[res]["Production"].attrs["units"]
        area_units = self[res]["HarvestArea"].attrs["units"]
        self[res]["Yield"].attrs["units"] = f"{prod_units}/{area_units}"

    def _import_one_resolution(self, earthstat_dir: str, opts: dict, res: str) -> None:
        """
        Import EarthStat maps for one resolution.

        Parameters
        ----------
        earthstat_dir : str
            Directory containing EarthStat data files.
        opts : dict
            Options dictionary containing 'start_year' and 'end_year'.
        res : str
            Resolution name to import.
        """
        earthstat_file = os.path.join(earthstat_dir, res + ".nc")
        # Skip (but warn) if EarthStat file not found.
        if not os.path.exists(earthstat_file):
            print(f"No EarthStat maps available for resolution {res}; will interpolate")
            return

        # Open file
        print(f"Importing EarthStat yield maps for resolution {res}...")
        print(earthstat_file)
        ds = xr.open_dataset(earthstat_file, decode_timedelta=False)

        # Drop variables we don't need
        vars_to_drop = [v for v in ds if v not in NEEDED_VARS]
        ds = ds.drop_vars(vars_to_drop)

        # Drop years we don't need
        start_date = None if (y := opts["start_year"]) is None else f"{y}-01-01"
        end_date = None if (y := opts["end_year"]) is None else f"{y}-12-31"
        ds = ds.sel(time=slice(start_date, end_date))

        self[res] = ds

    def get_data(
        self,
        res: str,
        stat_input: str,
        crop: str,
        target_unit: str,
    ) -> xr.DataArray:
        """
        Get data from EarthStat for a specific resolution, statistic, and crop.

        Parameters
        ----------
        res : str
            Resolution name (e.g., 'f09', 'f19').
        stat_input : str
            Statistic to retrieve ('yield', 'prod', or 'area').
        crop : str
            Crop name.
        target_unit : str
            Target unit for the data ('tonnes/ha' for yield, 'Mt' for prod, 'Mha' for area).

        Returns
        -------
        xarray.DataArray
            DataArray with the requested data in the target units.

        Raises
        ------
        NotImplementedError
            If stat_input is not 'yield', 'prod', or 'area', or if target_unit is not supported.
        RuntimeError
            If the units in the data don't match expected units.
        """
        # First, check whether this crop is even in EarthStat. Return early if not.
        earthstat_crop_idx = self.crops.index(crop)

        # Define some things based on what map we want
        if stat_input == "yield":
            which_var = "Yield"
            converting = ["tonnes/ha", "tonnes/ha"]
            conversion_factor = 1  # Already tons/ha
        elif stat_input == "prod":
            which_var = "Production"
            converting = ["tonnes", "Mt"]
            conversion_factor = 1e-6  # Convert tons to Mt
        elif stat_input == "area":
            which_var = "HarvestArea"
            converting = ["ha", "Mha"]
            conversion_factor = 1e-6  # Convert ha to Mha
        else:
            raise NotImplementedError(
                f"_get_earthstat_map() doesn't work for stat_input='{stat_input}'",
            )

        data_obs = self[res][which_var].isel(crop=earthstat_crop_idx)
        units_in = data_obs.attrs["units"]
        if units_in != converting[0]:
            raise RuntimeError(f"Expected {converting[0]}, got {units_in}")
        if target_unit != converting[1]:
            raise NotImplementedError(
                f"EarthStat.get_data() can't handle target_unit '{target_unit}'",
            )
        data_obs *= conversion_factor
        data_obs.attrs["units"] = converting[1]
        return data_obs

    def get_map(
        self,
        res: str,
        stat_input: str,
        crop: str,
        target_unit: str,
    ) -> xr.DataArray:
        """
        Get time-averaged map from EarthStat for comparing with CLM output.

        Parameters
        ----------
        res : str
            Resolution name (e.g., 'f09', 'f19').
        stat_input : str
            Statistic to retrieve ('yield', 'prod', or 'area').
        crop : str
            Crop name.
        target_unit : str
            Target unit for the data.

        Returns
        -------
        xarray.DataArray
            Time-averaged map of the requested statistic. For yield, this is area-weighted.
        """
        # Actually get the map
        data_obs = self.get_data(res, stat_input, crop, target_unit)

        # Area-weight mean yield
        if stat_input == "yield":
            # Target unit of weight doesn't actually matter but is needed for get_data() call
            data_obs = data_obs.weighted(self.get_data(res, "area", crop, "Mha"))

        map_obs = data_obs.mean(dim="time")

        return map_obs

    @classmethod
    def _create_empty(cls) -> EarthStat:
        """
        Create an empty EarthStat object without going through normal initialization.

        Used internally by sel() and isel() for creating copies.

        Returns
        -------
        EarthStat
            Empty EarthStat instance with initialized _data dict.
        """
        # Create instance without calling __init__
        instance = cls.__new__(cls)
        # Initialize _data as empty dict
        instance._data = {}
        return instance

    def _copy_other_attributes(self, dest_earthstat: EarthStat) -> EarthStat:
        """
        Copy all EarthStat attributes from self to destination, except for _data dict.

        Parameters
        ----------
        dest_earthstat : EarthStat
            Destination EarthStat object to copy attributes to.

        Returns
        -------
        EarthStat
            The destination EarthStat object with copied attributes.
        """
        for attr in [a for a in dir(self) if not a.startswith("__")]:
            if attr == "_data":
                continue
            # Skip callable attributes (methods) - they should be inherited from the class
            if callable(getattr(self, attr)):
                continue
            setattr(dest_earthstat, attr, getattr(self, attr))
        return dest_earthstat

    def sel(self, *args, **kwargs) -> EarthStat:
        """
        Make a copy of this EarthStat object, applying Dataset.sel() with the given arguments.

        Parameters
        ----------
        *args
            Positional arguments passed to Dataset.sel().
        **kwargs
            Keyword arguments passed to Dataset.sel().

        Returns
        -------
        EarthStat
            New EarthStat object with sel() applied to each resolution's dataset.
        """
        new_earthstat = self._create_empty()

        # .sel() each Dataset in dict
        for res in list(self.keys()):
            new_earthstat[res] = self[res].sel(*args, **kwargs)

        # Copy over other attributes
        new_earthstat = self._copy_other_attributes(new_earthstat)

        return new_earthstat

    def isel(self, *args, **kwargs) -> EarthStat:
        """
        Make a copy of this EarthStat object, applying Dataset.isel() with the given arguments.

        Parameters
        ----------
        *args
            Positional arguments passed to Dataset.isel().
        **kwargs
            Keyword arguments passed to Dataset.isel().

        Returns
        -------
        EarthStat
            New EarthStat object with isel() applied to each resolution's dataset.
        """
        new_earthstat = self._create_empty()

        # .sel() each Dataset in dict
        for res in list(self.keys()):
            new_earthstat[res] = self[res].isel(*args, **kwargs)

        # Copy over other attributes
        new_earthstat = self._copy_other_attributes(new_earthstat)

        return new_earthstat
