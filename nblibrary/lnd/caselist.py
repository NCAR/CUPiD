"""
A class for holding a list of cases and information about them
"""
from __future__ import annotations

import os
from time import time

import numpy as np
import xarray as xr


class CaseList(list):
    """
    A class for holding a list of cases and information about them
    """

    def __init__(
        self,
        *args,
        CropCase,
        identify_resolution,
        opts,
        **kwargs,
    ):
        # Initialize as a normal list...
        super().__init__(*args, **kwargs)
        # ...And then add all the extra stuff

        # Define extra variables
        self.names = opts["case_name_list"]

        # Import cases
        self._import_cases(
            CropCase,
            identify_resolution,
            opts,
        )
        self.resolutions = {case.cft_ds.attrs["resolution"].name for case in self}

        # Get map figure layout info
        self.mapfig_layout = {}
        self._get_mapfig_layout()

    def _import_cases(
        self,
        CropCase,  # pylint: disable=invalid-name
        identify_resolution,
        opts,
    ):
        start = time()
        for case_name in self.names:
            print(f"Importing {case_name}...")
            case_output_dir = os.path.join(
                opts["CESM_output_dir"],
                case_name,
                "lnd",
                "hist",
            )
            self.append(
                CropCase(
                    case_name,
                    case_output_dir,
                    opts["clm_file_h"],
                    opts["cfts_to_include"],
                    opts["crops_to_include"],
                    opts["start_year"],
                    opts["end_year"],
                    verbose=opts["verbose"],
                ),
            )

            if opts["dev_mode"]:
                start_load = time()
                print("Loading...")
                self[-1].cft_ds.load()
                end_load = time()
                print(f"Loading took {int(end_load - start_load)} s")

            # Get gridcell area
            ds = self[-1].cft_ds
            area_p = self._get_area_p(ds)
            ds["pfts1d_gridcellarea"] = xr.DataArray(
                data=area_p,
                coords={"pft": ds["pft"].values},
                dims=["pft"],
            )

            # Get resolution
            ds.attrs["resolution"] = identify_resolution(ds)

        print("Done.")
        if opts["verbose"]:
            end = time()
            print(f"Importing took {int(end - start)} s")

    def _get_area_p(self, ds):
        """
        Get area of gridcell that is parent of each pft (patch)
        """
        area_g = []
        for i, lon in enumerate(ds["grid1d_lon"].values):
            lat = ds["grid1d_lat"].values[i]
            area_g.append(ds["area"].sel(lat=lat, lon=lon))
        area_g = np.array(area_g)
        area_p = []
        for i in ds["pfts1d_gi"].isel(cft=0).values:
            area_p.append(area_g[int(i) - 1])
        area_p = np.array(area_p)
        return area_p

    def _get_mapfig_layout(self):
        """
        Get map figure layout info
        """
        n_cases = len(self.names)
        if 3 <= n_cases <= 4:
            self.mapfig_layout["nrows"] = 2
            self.mapfig_layout["subplots_adjust_colorbar_top"] = 0.95
            self.mapfig_layout["subplots_adjust_colorbar_bottom"] = 0.2
            self.mapfig_layout["cbar_ax_rect"] = (0.2, 0.15, 0.6, 0.03)
        else:
            raise RuntimeError(f"Specify figure layout for N_cases=={n_cases}")
        height = 3.75 * self.mapfig_layout["nrows"]
        width = 15
        self.mapfig_layout["figsize"] = (width, height)
        self.mapfig_layout["ncols"] = 2
        self.mapfig_layout["hspace"] = 0
        self.mapfig_layout["wspace"] = 0
