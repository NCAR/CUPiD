"""
A class for holding a list of cases and information about them
"""
from __future__ import annotations

import os
from time import time

import numpy as np


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
    ):
        # Initialize as a normal list...
        super().__init__(*args)
        # ...And then add all the extra stuff

        # Define extra variables
        self.names = opts["case_name_list"]

        # Get map figure layout info
        self.mapfig_layout = {}
        self._get_mapfig_layout()

        # Import cases
        self._import_cases(
            CropCase,
            identify_resolution,
            opts,
        )
        self.resolutions = {case.cft_ds.attrs["resolution"] for case in self}

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
                    opts["cfts_to_include"],
                    opts["crops_to_include"],
                    opts["start_year"],
                    opts["end_year"],
                    verbose=opts["verbose"],
                    force_new_cft_ds_file=opts["force_new_cft_ds_file"],
                ),
            )

            # Get resolution
            self[-1].cft_ds.attrs["resolution"] = identify_resolution(
                self[-1].cft_ds,
            ).name

        print("Done.")
        if opts["verbose"]:
            end = time()
            print(f"Importing took {int(end - start)} s")

    def _get_mapfig_layout(self):
        """
        Get map figure layout info
        """
        n_cases = len(self.names)

        self.mapfig_layout["nrows"] = int(np.ceil(n_cases / 2))
        self.mapfig_layout["subplots_adjust_colorbar_top"] = 0.95
        self.mapfig_layout["subplots_adjust_colorbar_bottom"] = 0.2
        self.mapfig_layout["cbar_ax_rect"] = (0.2, 0.15, 0.6, 0.03)

        height = 3.75 * self.mapfig_layout["nrows"]
        width = 15
        self.mapfig_layout["figsize"] = (width, height)
        self.mapfig_layout["ncols"] = 2
        self.mapfig_layout["hspace"] = 0
        self.mapfig_layout["wspace"] = 0
