"""
Classes to handle importing and working with EarthStat data
"""
from __future__ import annotations

import os
import warnings
from copy import deepcopy

import numpy as np
import xarray as xr
import xesmf as xe

# The resolution which will be used as the basis for regridding, if available
REFERENCE_EARTHSTAT_RES = "f09"

# The variables we actually use anywhere
NEEDED_VARS = ["HarvestArea", "Production", "Yield", "LandMask"]

# One level's worth of indentation for messages
INDENT = "    "


def align_time(da_to_align, target_time):
    """
    EarthStat and CLM time axes don't match. This function gives the EarthStat data the time axis of
    the CLM outputs. If you don't do this, you will get all NaNs when you try to assign something
    from EarthStat to the CLM Dataset.
    """

    # Align EarthStat with CLM axis
    orig_time = da_to_align["time"]
    first_year = min(orig_time.values).year
    last_year = max(orig_time.values).year
    this_slice = slice(f"{first_year}-01-01", f"{last_year}-12-31")
    new_time_coord = target_time.sel(time=this_slice)

    # Slice EarthStat to match CLM time span
    first_year_target = min(target_time.values).year
    last_year_target = max(target_time.values).year
    this_slice = slice(f"{first_year_target}-01-01", f"{last_year_target}-12-31")
    da_to_align = da_to_align.sel(time=this_slice)

    return da_to_align.assign_coords({"time": new_time_coord})


def check_dim_alignment(earthstat_ds, clm_ds):
    """
    Ensure that EarthStat and CLM datasets are aligned on all dimensions
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


def _get_regridder_and_mask(da_in, mask_in, ds_target, method):
    """Get regridder and mask"""
    # Create mask
    mask = xr.where(~mask_in.notnull() | (mask_in == 0), 0.0, 1.0)

    # Not sure how much of a difference specifying this makes, but anyway
    if "conservative" in method:
        # Extrapolation not available for conservative regridding methods
        extrap_method = None
    else:
        extrap_method = "inverse_dist"

    # Create and apply regridder
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Latitude is outside of")
        regridder = xe.Regridder(
            da_in,
            ds_target,
            method=method,
            ignore_degenerate=True,
            extrap_method=extrap_method,
        )
    mask_regridded = regridder(mask)

    return regridder, mask_regridded


def _regrid_to_clm(
    *,
    ds_in,
    var,
    ds_target,
    method="conservative",
    area_in=None,
    area_out=None,
    mask_var=None,
):
    """Regrid an observational dataset to a CLM target grid using conservative regridding"""

    # Sense checks
    assert (area_in is None) == (area_out is None)
    if area_in is not None:
        area_out = area_out * area_in.sum() / area_out.sum()

    # Get mask of input data
    if mask_var is None:
        mask_var = var
    mask_in = ds_in[mask_var]

    # Extract data
    da_in = ds_in[var]
    if area_in is not None:
        # da_in /= area_in
        da_in = da_in / area_in
        da_in = da_in.where(area_in > 0)
    data_filled = da_in.fillna(0.0)

    # xesmf might look for a "mask" variable:
    # https://coecms-training.github.io/parallel/case-studies/regridding.html
    if "landmask" in ds_target:
        ds_target["mask"] = ds_target["landmask"].fillna(0)

    # Create and apply regridder
    regridder, _ = _get_regridder_and_mask(
        da_in,
        mask_in,
        ds_target,
        method,
    )
    da_out = regridder(data_filled)

    # NO; this adds an 8-9 percentage point overestimate in test variables HarvestArea and
    # Production. Which makes sense: These are not per-m2-of-gridcell numbers; these are gridcell
    # TOTALS.
    # # Normalize to account for partial coverage
    # da_out = da_out / mask_regridded

    # apply landmask from CLM target grid
    da_out = da_out * ds_target["landmask"]

    if area_out is not None:
        da_out *= area_out

    # If we chose a conservative method, assume we want the global sums to match before and after.
    if "conservative" in method:

        # Print error in global sum introduced by regridding
        before = ds_in[var].sum().values
        after = da_out.sum().values
        pct_diff = (after - before) / before * 100
        if "units" in ds_in[var].attrs:
            units = ds_in[var].attrs["units"]
        else:
            units = "unknown units"
        print(f"{INDENT}{var} ({units}):")
        print(f"{2*INDENT}Global sum before: {before:.2e}")
        print(f"{2*INDENT}Global sum  after: {after:.2e} ({pct_diff:.1f}% diff)")

        # Adjust so global sum matches what we had before regridding
        print(f"{2*INDENT}Adjusting to match.")
        da_out = da_out * ds_in[var].sum() / da_out.sum()
        after = da_out.sum().values
        diff = after - before
        pct_diff = diff / before * 100
        print(f"{2*INDENT}Global diff final: {diff:.2e} ({pct_diff:.1f}%)")

    # Recover attributes
    da_out.attrs = ds_in[var].attrs

    # Destroy regridder to avoid memory leak?
    # https://github.com/JiaweiZhuang/xESMF/issues/53#issuecomment-2114209348
    # Doesn't seem to help much, if at all. Maybe a couple hundred MB.
    regridder.grid_in.destroy()
    regridder.grid_out.destroy()
    del regridder

    return da_out


def get_clm_landarea(ds):
    return ds["area"] * ds["landfrac"]


class EarthStat:
    """
    A class to handle importing EarthStat data
    """

    def __init__(
        self,
        earthstat_dir,
        sim_resolutions,
        opts,
    ):
        # Define variables
        self.crops = []
        self._data = {}

        # Import EarthStat crop list
        self._get_crop_list(earthstat_dir, opts["crops_to_include"])

        # Import EarthStat maps
        self._import_all_resolutions(earthstat_dir, sim_resolutions, opts)

    def __getitem__(self, key):
        """instance[key] syntax should return corresponding value in data dict"""
        return self._data[key]

    def __setitem__(self, key: str, value: xr.Dataset):
        """instance[key]=value syntax should set corresponding key=value in data dict"""
        self._data[key] = value

    def __print__(self):
        print(
            f"Dict with Datasets for the following resolutions: {','.join(self._data.keys())}",
        )

    def keys(self):
        """
        Return keys of the _data dict
        """
        return self._data.keys()

    def items(self):
        """
        Return items (key-value pairs) of the _data dict
        """
        return self._data.items()

    def _get_crop_list(self, earthstat_dir, crops_to_include):
        """
        Get the list of crops in EarthStat
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
        for crop in crops_to_include:
            if crop not in self.crops:
                print(f"WARNING: {crop} not found in self.crops")

    def _import_all_resolutions(self, earthstat_dir, sim_resolutions, opts):
        """
        Import EarthStat maps corresponding to simulated CLM resolutions
        """
        for res in sim_resolutions.keys():
            self._import_one_resolution(earthstat_dir, opts, res)

        # If any resolutions weren't read, we'll need to interpolate to get them
        missing_res = [k for k in sim_resolutions.keys() if k not in self.keys()]
        if missing_res:
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
                clm_in_ds = xr.open_dataset(clm_in_file)
            clm_in_landarea = get_clm_landarea(clm_in_ds)

            for res in missing_res:
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
                        earthstat_out_da = _regrid_to_clm(
                            ds_in=deepcopy(earthstat_in_ds),
                            var=var,
                            ds_target=deepcopy(clm_out_ds),
                            method=method,
                            area_in=deepcopy(clm_in_landarea),
                            area_out=deepcopy(clm_out_landarea),
                            mask_var="LandMask",
                        )
                    if i == 0:
                        self[res] = xr.Dataset(data_vars={var: earthstat_out_da})
                    else:
                        self[res][var] = earthstat_out_da

                # Calculate yield
                self[res]["Yield"] = self[res]["Production"] / self[res]["HarvestArea"]
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*large graph.*")
                    self[res]["Yield"].load()
                self[res]["Yield"].attrs["long_name"] = "crop yield"
                prod_units = self[res]["Production"].attrs["units"]
                area_units = self[res]["HarvestArea"].attrs["units"]
                self[res]["Yield"].attrs["units"] = f"{prod_units}/{area_units}"

        print("Done.")

    def _import_one_resolution(self, earthstat_dir, opts, res):
        earthstat_file = os.path.join(earthstat_dir, res + ".nc")
        # Skip (but warn) if EarthStat file not found.
        if not os.path.exists(earthstat_file):
            print(f"No EarthStat maps available for resolution {res}; will interpolate")
            return

        # Open file
        print(f"Importing EarthStat yield maps for resolution {res}...")
        print(earthstat_file)
        ds = xr.open_dataset(earthstat_file)

        # Drop variables we don't need
        vars_to_drop = [v for v in ds if v not in NEEDED_VARS]
        ds = ds.drop_vars(vars_to_drop)

        # Drop years we don't need
        start_year = opts["start_year"]
        end_year = opts["end_year"]
        ds = ds.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))

        self[res] = ds

    def get_data(self, res, stat_input, crop, target_unit):
        """
        Get data from EarthStat
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

    def get_map(self, res, stat_input, crop, target_unit):
        """
        Get map from EarthStat for comparing with CLM output
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
    def _create_empty(cls):
        """
        Create an empty EarthStat object without going through the normal initialization (i.e.,
        import). Used internally by sel() and isel() for creating copies.
        """
        # Create instance without calling __init__
        instance = cls.__new__(cls)
        # Initialize _data as empty dict
        instance._data = {}
        return instance

    def _copy_other_attributes(self, dest_earthstat):
        """
        Copy all CropCaseList attributes from self to destination EarthStat object, except
        for _data dict.
        """
        for attr in [a for a in dir(self) if not a.startswith("__")]:
            if attr == "_data":
                continue
            # Skip callable attributes (methods) - they should be inherited from the class
            if callable(getattr(self, attr)):
                continue
            setattr(dest_earthstat, attr, getattr(self, attr))
        return dest_earthstat

    def sel(self, *args, **kwargs):
        """
        Makes a copy of this EarthStat object, applying Dataset.sel() with the given arguments.
        """
        new_earthstat = self._create_empty()

        # .sel() each Dataset in dict
        for res in list(self.keys()):
            new_earthstat[res] = self[res].sel(*args, **kwargs)

        # Copy over other attributes
        new_earthstat = self._copy_other_attributes(new_earthstat)

        return new_earthstat

    def isel(self, *args, **kwargs):
        """
        Makes a copy of this EarthStat object, applying Dataset.isel() with the given arguments.
        """
        new_earthstat = self._create_empty()

        # .sel() each Dataset in dict
        for res in list(self.keys()):
            new_earthstat[res] = self[res].isel(*args, **kwargs)

        # Copy over other attributes
        new_earthstat = self._copy_other_attributes(new_earthstat)

        return new_earthstat
