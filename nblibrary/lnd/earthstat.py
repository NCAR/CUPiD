"""
Classes to handle importing and working with EarthStat data
"""
from __future__ import annotations

import os

import xarray as xr

# TODO:
# 1. Eliminate EarthStatDataset class. Move its methods into EarthStat class.
# 2. Allows: Delete __slots__ thing and warning suppression about that
# 3. EarthStat.get_data(): Add required "target units" attribute and fail if not handled
# 4. Add custom EarthStat.__repr__ method to just show (xr.Dataset(resolution, time range))
# 5. "First, check whether this crop is even in EarthStat. Return early if not." does not do this??
# CHECK B4B RESULTS
# 6. EarthStat.get_map() and get_data() need to include time_slice option instead of getting mean of all time
# 7. EarthStat.get_map() needs to area-weight mean yield


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
        self._import_data(earthstat_dir, sim_resolutions, opts)

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

    def _import_data(self, earthstat_dir, sim_resolutions, opts):
        """
        Import EarthStat maps corresponding to simulated CLM resolutions
        """
        for res in sim_resolutions:
            # For now, can only import f09 EarthStat. Will skip maps comparing EarthStat to output
            # from other resolutions.
            if res != "f09":
                continue
            print(f"Importing EarthStat yield maps for resolution {res}...")

            # Open file
            ds = xr.open_dataset(os.path.join(earthstat_dir, res + ".nc"))
            start_year = opts["start_year"]
            end_year = opts["end_year"]
            ds = ds.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))

            self[res] = ds
        print("Done.")

    def get_data(self, res, stat_input, crop):
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
        data_obs *= conversion_factor
        data_obs.attrs["units"] = converting[1]
        return data_obs

    def get_map(self, res, stat_input, crop):
        """
        Get map from EarthStat for comparing with CLM output
        """
        # Actually get the map
        data_obs = self.get_data(res, stat_input, crop)
        map_obs = data_obs.mean(dim="time")

        return map_obs
