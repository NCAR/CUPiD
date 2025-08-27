"""
A class to handle importing and working with EarthStat data
"""
from __future__ import annotations

import os

import xarray as xr
from plotting_utils import cut_off_antarctica


class EarthStat:
    """
    A class to handle importing and working with EarthStat data
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

    def get_map(self, which, case_res, crop, case_name):
        """
        Get map from EarthStat for comparing with CLM output
        """

        # First, check whether this crop is even in EarthStat. Return early if not.
        map_obs = None
        try:
            earthstat_crop_idx = self.crops.index(crop)
        except ValueError:
            print(f"{crop} not in EarthStat res {case_res}; skipping")
            return map_obs
        try:
            earthstat_ds = self[case_res]
        except KeyError:
            print(f"{case_res} not in EarthStat; skipping {case_name}")
            return map_obs

        # Define some things based on what map we want
        if which == "yield":
            which_var = "Yield"
            conversion_factor = 1  # Already tons/ha
        elif which == "prod":
            which_var = "Production"
            conversion_factor = 1e-6  # Convert tons to Mt
        elif which == "area":
            which_var = "HarvestArea"
            conversion_factor = 1e-6  # Convert ha to Mha
        else:
            raise NotImplementedError(
                f"_get_earthstat_map() doesn't work for which='{which}'",
            )

        # Actually get the map
        map_obs = earthstat_ds[which_var].isel(crop=earthstat_crop_idx).mean(dim="time")
        map_obs = cut_off_antarctica(map_obs)
        map_obs *= conversion_factor

        return map_obs
